import json
from pathlib import Path

import pytest

from extract.guidance import extract, pick_pages, refine_metric, score_page
from extract.pdfs import extract_pages
from extract.promises import (
    build_actuals,
    column_periods,
    compare,
    decide_status,
    horizon_end,
    lookup_actual,
    quarter_label,
    resolve_period,
    target_text,
)
from extract.quotes import locate

DEMO = Path(__file__).resolve().parents[3] / "data" / "demo"


# ---------- periods ----------
@pytest.mark.parametrize(
    "text,call,label,key",
    [
        ("FY27", "2026-06", "FY27", "FY:2027-03"),
        ("fiscal 2027", "2026-06", "FY27", "FY:2027-03"),
        ("Q2 FY27", "2026-06", "Q2 FY27", "Q:2026-09"),
        ("Q4 FY26", "2025-12", "Q4 FY26", "Q:2026-03"),
        ("next quarter", "2026-06", "Q2 FY27", "Q:2026-09"),
        ("full year", "2026-06", "FY27", "FY:2027-03"),
        ("this year", "2026-03", "FY27", "FY:2027-03"),  # Q4 call is held in April
        ("next year", "2026-06", "FY28", "FY:2028-03"),
        ("second half", "2026-06", "H2 FY27", "H:2027-03"),
        ("H1 FY27", "2026-03", "H1 FY27", "H:2026-09"),
    ],
)
def test_resolve_period(text, call, label, key):
    p = resolve_period(text, call)
    assert p is not None and p.label == label and p.key == key


@pytest.mark.parametrize("text", ["", "going forward", "next few quarters", "this quarter", "soon"])
def test_ambiguous_period_is_none(text):
    assert resolve_period(text, "2026-06") is None


def test_quarter_label():
    assert quarter_label("2026-09") == "Q2 FY27" and quarter_label("2026-03") == "Q4 FY26"


# ---------- column layout ----------
def test_column_periods_for_each_quarter_layout():
    assert column_periods("2026-09", 6) == [
        "Q:2026-09", "Q:2026-06", "Q:2025-09", "H:2026-09", "H:2025-09", "FY:2026-03",
    ]  # fmt: skip
    assert column_periods("2026-06", 4)[3] == "FY:2026-03"
    assert column_periods("2026-03", 5)[3:] == ["FY:2026-03", "FY:2025-03"]
    assert column_periods("2025-12", 6)[3] == "N:2025-12"


def parsed_row(period="2026-09"):
    v = lambda *a: list(a)  # noqa: E731
    return {
        "period": period,
        "doc_sha256": "sha",
        "parsed": {
            "status": "ok", "basis": "consolidated",
            "column_ok": [True, True, True, True, True, False],
            "metrics": {
                "revenue": {"values": v(120, 100, 80, 220, 160, 0), "page": 8, "line": "rev"},
                "pbt": {"values": v(30, 20, 16, 50, 30, 0), "page": 8, "line": "pbt"},
                "pat": {"values": v(20, 15, 12, 35, 22, 0), "page": 8, "line": "pat"},
            },
            "derived": {
                "ebitda": v(36, 25, 20, 61, 35, None),
                "ebit": v(30, 20, 16, 50, 28, None),
            },
        },
    }  # fmt: skip


def test_build_actuals_uses_only_checked_columns():
    a = build_actuals([parsed_row()])
    assert set(a) == {"Q:2026-09", "Q:2026-06", "Q:2025-09", "H:2026-09", "H:2025-09"}
    assert "FY:2026-03" not in a  # that column failed its identity checks
    assert horizon_end([parsed_row()]) == "2026-09"


def test_lookup_actual_margin_and_growth():
    a = build_actuals([parsed_row()])
    q2 = resolve_period("Q2 FY27", "2026-06")
    v, text, _ = lookup_actual("ebitda_margin", "level", "none", q2, a)
    assert round(v, 1) == 30.0 and text == "30.0%"
    v, text, _ = lookup_actual("revenue_growth", "yoy", "none", q2, a)
    assert round(v, 1) == 50.0 and "YoY" in text
    v, text, _ = lookup_actual("revenue_growth", "qoq", "none", q2, a)
    assert round(v, 1) == 20.0
    h1 = resolve_period("H1 FY27", "2026-06")
    assert round(lookup_actual("revenue_growth", "yoy", "none", h1, a)[0], 1) == 37.5


def test_lookup_refuses_what_results_cannot_answer():
    a = build_actuals([parsed_row()])
    q2 = resolve_period("Q2 FY27", "2026-06")
    assert lookup_actual("revenue_growth", "yoy", "constant_currency", q2, a) is None
    assert lookup_actual("volume_growth", "yoy", "none", q2, a) is None
    assert lookup_actual("revenue_growth", "cagr", "none", q2, a) is None
    assert lookup_actual("ebitda_margin", "yoy", "none", q2, a) is None
    q1 = resolve_period("Q1 FY27", "2026-03")  # prior-year Q1 is not in our filings
    assert lookup_actual("revenue_growth", "yoy", "none", q1, a) is None


# ---------- compare / every status ----------
@pytest.mark.parametrize(
    "actual,direction,low,high,kind,want",
    [
        (14.5, "range", 14, 15, "margin", "Delivered"),
        (16.0, "range", 14, 15, "margin", "Delivered"),  # beating the range is delivered
        (13.7, "range", 14, 15, "margin", "Partly"),
        (13.4, "range", 14, 15, "margin", "Missed"),  # the Figma example
        (20.8, "point", 20, None, "growth", "Delivered"),
        (18.5, "point", 20, None, "growth", "Delivered"),  # within 2pp below "around 20"
        (16.0, "point", 20, None, "growth", "Partly"),
        (10.0, "point", 20, None, "growth", "Missed"),
        (25.0, "min", 25, None, "margin", "Delivered"),
        (24.7, "min", 25, None, "margin", "Partly"),
        (22.0, "min", 25, None, "margin", "Missed"),
        (9.0, "max", None, 10, "growth", "Delivered"),
    ],
)
def test_compare(actual, direction, low, high, kind, want):
    assert compare(actual, direction, low, high, kind) == want


def item(**kw):
    base = dict(metric="ebitda_margin", basis="level", qualifier="none", period="Q2 FY27",
                direction="range", low=14.0, high=15.0, unit="percent")  # fmt: skip
    return {**base, **kw}


def test_status_vague_is_never_scored():
    s, d = decide_status(item(direction="none", low=None, high=None), "2026-06", {}, "2026-09")
    assert s == "Vague" and "never scored" in d["reason"]


def test_status_not_yet_due_and_no_comparable():
    a = build_actuals([parsed_row()])
    s, _ = decide_status(item(period="FY27"), "2026-06", a, "2026-09")
    assert s == "Not yet due"
    s, d = decide_status(item(period="going forward"), "2026-06", a, "2026-09")
    assert s == "No comparable actual" and "period" in d["reason"]
    s, _ = decide_status(item(metric="volume_growth"), "2026-06", a, "2026-09")
    assert s == "No comparable actual"
    s, _ = decide_status(item(period="Q4 FY26"), "2026-03", a, "2026-09")  # due, not in results
    assert s == "No comparable actual"
    s, _ = decide_status(item(), "2026-06", {}, None)  # nothing reported at all
    assert s == "Not yet due"


def test_status_delivered_and_missed_cite_their_source():
    a = build_actuals([parsed_row()])
    s, d = decide_status(item(low=25, high=28), "2026-06", a, "2026-09")  # actual margin 30.0
    assert s == "Delivered" and d["reported"] == "30.0%" and d["source"]["page"] == 8
    s, d = decide_status(item(low=34, high=36), "2026-06", a, "2026-09")
    assert s == "Missed" and d["target"] == "34–36%"


def test_target_text():
    assert target_text("range", 14, 15, "percent") == "14–15%"
    assert target_text("min", 25, None, "percent") == "25% or more"
    assert target_text("point", 20, None, "percent") == "around 20%"
    assert target_text("none", None, None, "percent") == ""


# ---------- quotes ----------
def test_locate_finds_exact_and_near_quotes_and_rejects_invented_ones():
    page = "We expect margins\nto stay in the 14 to 15%\nrange for the full year."
    h = locate("we expect margins to stay in the 14 to 15% range", page)
    assert h is not None and h.score >= 90 and page[h.start : h.end].lower().startswith("we expect")
    assert locate("management promised a 40% jump next quarter", page) is None


# ---------- guidance extraction with a fake model ----------
class Fake:
    def __init__(self, items):
        self.items = items

    def complete(self, model, version, system, user):
        return json.dumps({"items": self.items})


@pytest.fixture(scope="module")
def tcs_pages():
    p = DEMO / "transcripts" / "TCS_2026-06.pdf"
    return {i + 1: t for i, t in enumerate(extract_pages(p))}


def test_pick_pages_prefers_forward_looking_pages(tcs_pages):
    picked = pick_pages(tcs_pages, 6)
    assert len(picked) <= 6 and picked == sorted(picked)
    best = max(tcs_pages, key=lambda p: score_page(tcs_pages[p]))
    assert best in picked
    assert score_page("Thank you, the call has ended.") == 0


def test_extract_drops_invented_quotes_and_unspoken_numbers(tcs_pages):
    pg = pick_pages(tcs_pages)[0]
    real = " ".join(tcs_pages[pg].split())[:90]
    out = extract(
        Fake(
            [
                {
                    "page": pg,
                    "quote": "TCS guarantees 30% growth in FY28 for sure",
                    "metric": "revenue_growth",
                },
                {
                    "page": pg,
                    "quote": real,
                    "metric": "revenue_growth",
                    "basis": "yoy",
                    "qualifier": "none",
                    "period": "FY27",
                    "direction": "min",
                    "low": 77,
                    "high": None,
                    "unit": "percent",
                },
                {"page": 999, "quote": real, "metric": "other"},
            ]
        ),
        tcs_pages,
    )
    assert out.dropped_quote == 1 and out.dropped_other == 1
    assert len(out.items) == 1
    it = out.items[0]
    assert it.low is None and it.direction == "none"  # 77 is not in the quote, so it is Vague
    assert it.match_score >= 90


def test_refine_metric_needs_support_from_the_page():
    page = "We want to exit at 25% plus and strive to achieve it sooner."
    assert refine_metric("ebitda_margin", "exit at 25% plus", page, 0, 20) == "other"
    page2 = "Our operating margin should be 26 to 28%."
    assert refine_metric("ebitda_margin", "26 to 28%", page2, 30, 40) == "ebit_margin"
    page3 = "EBITDA margin will be at least 15%."
    assert refine_metric("ebitda_margin", "at least 15%", page3, 25, 37) == "ebitda_margin"
    assert refine_metric("revenue_growth", "x", "We will do well.", 0, 5) == "other"


# ---------- job helpers ----------
def test_quarter_end_for_call_month():
    from jobs.promises import quarter_end_for_call as q

    assert q("Nov 2026") == "2026-09" and q("Oct 2026") == "2026-09"
    assert q("Aug 2026") == "2026-06" and q("Jul 2026") == "2026-06"
    assert q("May 2026") == "2026-03" and q("Apr 2026") == "2026-03"
    assert q("Feb 2026") == "2025-12" and q("Jan 2026") == "2025-12"
    assert q("garbage") is None


def test_ledger_key_changes_with_any_input():
    from jobs.promises import ledger_key

    base = ledger_key("TCS", [{"sha256": "a"}], [{"doc_sha256": "r"}])
    assert base == ledger_key("TCS", [{"sha256": "a"}], [{"doc_sha256": "r"}])
    assert base != ledger_key("TCS", [{"sha256": "a"}, {"sha256": "b"}], [{"doc_sha256": "r"}])
    assert base != ledger_key("TCS", [{"sha256": "a"}], [{"doc_sha256": "r2"}])
    assert base != ledger_key("INFY", [{"sha256": "a"}], [{"doc_sha256": "r"}])


def test_model_failure_is_an_error_not_empty_guidance(tcs_pages):
    class Boom:
        def complete(self, *a):
            raise RuntimeError("429 Too Many Requests")

    out = extract(Boom(), tcs_pages)
    assert out.items == [] and out.error and "429" in out.error

    class BadJson:
        def complete(self, *a):
            return "not json"

    assert extract(BadJson(), tcs_pages).error


def test_retry_wait_honours_retry_after():
    from extract.llm import retry_wait

    assert retry_wait("12", 1) == 13.0
    assert retry_wait("999", 1) == 66.0  # capped
    assert retry_wait(None, 3) == 30.0


def test_double_digit_is_a_number_management_gave(tcs_pages):
    pg = pick_pages(tcs_pages)[0]
    real = " ".join(tcs_pages[pg].split())[:80]
    q = real + " double-digit"
    pages = {pg: tcs_pages[pg] + "\n" + q}
    out = extract(
        Fake([{"page": pg, "quote": q, "metric": "revenue_growth", "direction": "none",
               "period": "FY27", "basis": "yoy", "qualifier": "none"}]),
        pages,
    )  # fmt: skip
    it = out.items[0]
    assert it.direction == "min" and it.low == 10.0 and it.unit == "percent"
