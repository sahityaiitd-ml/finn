import json
from datetime import UTC, datetime

import pytest

from app.digest import build_digest, display_headline
from extract.llm import analyse, clean_summary
from jobs.classify_filings import decide
from rules.classify import CATEGORIES, FLOOR_CATEGORIES, classify, is_generic_headline
from rules.materiality import ROUTINE_BELOW, is_routine, materiality


class FakeLLM:
    def __init__(self, reply):
        self.reply, self.calls = reply, 0

    def complete(self, model, version, system, user):
        self.calls += 1
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply if isinstance(self.reply, str) else json.dumps(self.reply)


# real BSE headlines (+ descriptions) from the live run -> expected category, floored?
REAL = [
    ("Announcement under Regulation 30 (LODR)-Analyst / Investor Meet - Intimation", "", "investor_meetings", False),
    ("Announcement under Regulation 30 (LODR)-Earnings Call Transcript", "", "earnings_call", False),
    ("Announcement under Regulation 30 (LODR)-Newspaper Publication", "", "unclassified", False),
    ("Announcement under Regulation 30 (LODR) - Bagging/receiving of order(s) or contract(s)", "", "press_release", False),
    ("Corporate Insolvency Resolution Process (CIRP)-Updates", "", "litigation", True),
    ("Intimation of Repayment of Commercial Paper (CP)", "", "fund_raise", False),
    ("Shareholder Meeting / Postal Ballot-Outcome of Postal_Ballot 6 Nov", "", "postal_ballot", False),
    ("Announcement under Regulation 30 (LODR)-Change in Directorate", "", "management_change", True),
    ("Announcement under Regulation 30 (LODR)-Change in Management", "", "management_change", True),
    ("Announcement under Regulation 30 (LODR)-Credit Rating", "", "credit_rating", True),
    ("Announcement under Regulation 30 (LODR)-Scheme of Arrangement", "", "M&A", True),
    ("Announcement under Regulation 30 (LODR)-Acquisition", "", "M&A", True),
    ("Unaudited Financial Results Of The Company For The Quarter And Six Months Ended 30Th September, 2026", "", "results", True),
    ("Announcement under Regulation 30 (LODR)-Allotment of ESOP / ESPS", "", "unclassified", False),
    ("Change In Corporate Office Address Of Registrar And Share Transfer Agent For Correspondence", "", "unclassified", False),
    ("Rumour verification - Regulation 30(11)", "", "press_release", False),
    ("Investor Conference", "Attending the Morgan Stanley investor conference", "investor_meetings", False),
    ("Intimation Under Regulation 30 Of SEBI(LODR)Regulations, 2015", "Dabur Pars LLC, Iranian subsidiary, dissolved on November 9", "M&A", True),
    ("Submission Of Information Under Regulation 30(5)", "Dabur appoints Ashok Kumar Jain as compliance officer", "management_change", True),
]  # fmt: skip


@pytest.mark.parametrize("headline,desc,cat,floored", REAL)
def test_real_headlines(headline, desc, cat, floored):
    v = classify(headline, desc)
    assert v is not None and v.category == cat and v.never_collapse is floored


def test_auditor_change_is_floored_even_though_category_is_unclassified():
    v = classify("Announcement under Regulation 30 (LODR)-Resignation of Statutory Auditor", "")
    assert v.never_collapse and v.floor_reason == "auditor_change"


@pytest.mark.parametrize(
    "text,cat",
    [
        ("Pledge of shares by promoter", "pledging"),
        ("Rights issue of equity shares", "fund_raise"),
        ("Litigation: show cause notice from SEBI", "litigation"),
        ("Intimation of merger with subsidiary", "M&A"),
        ("Resignation of Chief Financial Officer", "management_change"),
    ],
)
def test_every_floor_category_is_never_collapsed(text, cat):
    v = classify(text, "")
    assert v.category == cat and v.category in FLOOR_CATEGORIES and v.never_collapse


def test_board_outcome_is_never_collapsed():
    v = classify("Outcome of Board Meeting", "Board approved appointment of auditors")
    assert v.never_collapse and v.floor_reason == "board_outcome"


def test_unmatched_returns_none_for_the_model():
    assert classify("Intimation Under Regulation 30", "Something unrelated happened") is None


def test_generic_headline_detection():
    assert is_generic_headline("Intimation Under Regulation 30 Of SEBI(LODR)Regulations, 2015")
    assert is_generic_headline("Disclosure Under Regulation 30 Of SEBI (LODR), Regulations, 2015")
    assert not is_generic_headline("Announcement under Regulation 30 (LODR)-Credit Rating")


# ---------- materiality ----------
def test_materiality_order_and_floor():
    assert materiality("results", "x", "", True) > materiality("investor_meetings", "x", "", False)
    assert materiality("unclassified", "x", "", True) >= 50  # floor lifts the score
    assert materiality("press_release", "CEO resigns", "", False) == 45  # keyword boost
    assert materiality("results", "x", "", False) <= 100


def test_routine_only_when_low_and_not_floored():
    assert is_routine(ROUTINE_BELOW - 1, False)
    assert not is_routine(ROUTINE_BELOW - 1, True)
    assert not is_routine(ROUTINE_BELOW, False)


# ---------- model guards ----------
def test_model_unsure_or_garbage_is_shown_never_hidden():
    for reply in ({"category": "unsure", "summary": "x"}, "not json", RuntimeError("down"),
                  {"category": "made_up", "summary": "x"}):  # fmt: skip
        d = decide(FakeLLM(reply), "Odd headline nobody matches", "No keyword here")
        assert d["never_collapse"] is True and d["classified_by"] == "llm8b"


def test_model_floor_category_is_floored_and_calm_one_is_not():
    d = decide(FakeLLM({"category": "litigation", "summary": "s"}), "Odd zzz", "none")
    assert d["never_collapse"] and d["category"] == "litigation"
    d = decide(FakeLLM({"category": "investor_meetings", "summary": "s"}), "Odd zzz", "none")
    assert not d["never_collapse"] and d["materiality"] < ROUTINE_BELOW


def test_rules_do_not_call_the_model_unless_headline_is_generic():
    llm = FakeLLM({"category": "unsure", "summary": "x"})
    decide(llm, "Announcement under Regulation 30 (LODR)-Credit Rating", "reaffirmed")
    assert llm.calls == 0
    decide(llm, "Intimation Under Regulation 30 Of SEBI(LODR)Regulations, 2015", "Acquired Foo Ltd")
    assert llm.calls == 1


def test_summary_is_at_most_25_words_and_numbers_must_come_from_source():
    src = "Penalties of Rs.1.60 lakh were levied"
    assert len(clean_summary(" ".join(["word"] * 40), src).split()) <= 26  # 25 + ellipsis mark
    assert clean_summary("Penalty of Rs.1.60 lakh", src) is not None
    assert clean_summary("Penalty of Rs.9.99 lakh", src) is None  # invented number is dropped
    assert analyse(FakeLLM({"category": "dividend", "summary": "Pays 5"}), "h", "d")[1] is None


def test_all_categories_are_the_17_in_the_reference_doc():
    assert len(CATEGORIES) == 17 and len(set(CATEGORIES)) == 17


# ---------- digest ----------
NOW = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)


def f(i, hours_ago, cat, score, floor=False, reviewed=False):
    ts = datetime.fromtimestamp(NOW.timestamp() - hours_ago * 3600, UTC).isoformat()
    return {"id": i, "symbol": "TCS", "category": cat, "headline": f"Announcement under Regulation 30 (LODR)-{cat}",
            "published_at": ts, "materiality": score, "never_collapse": floor, "reviewed": reviewed,
            "url": "https://x"}  # fmt: skip


def test_digest_window_ranking_and_routine_drawer():
    rows = [
        f("a", 2, "investor_meetings", 15),
        f("b", 3, "results", 90, True),
        f("c", 5, "litigation", 80, True),
        f("old", 30, "results", 90, True),  # outside 24h
        f("d", 1, "unclassified", 5),
    ]
    d = build_digest(rows, {"TCS": "TCS Ltd"}, NOW, "24h")
    assert [i["id"] for i in d["main"]] == ["b", "c"]  # ranked by materiality
    assert {i["id"] for i in d["routine"]} == {"a", "d"}
    assert d["counts"] == {"main": 2, "routine": 2, "to_review": 2}
    assert build_digest(rows, {}, NOW, "7d")["counts"]["main"] == 3


def test_digest_caught_up_and_unclassified_never_hidden():
    rows = [f("b", 3, "results", 90, True, reviewed=True)]
    assert build_digest(rows, {}, NOW, "24h")["caught_up"] is True
    unclassified = f("u", 1, None, 0)
    d = build_digest([unclassified], {}, NOW, "24h")
    assert d["counts"]["main"] == 1 and d["caught_up"] is False


def test_display_headline_strips_boilerplate():
    assert (
        display_headline("Announcement under Regulation 30 (LODR)-Credit Rating") == "Credit Rating"
    )
    assert display_headline("Newspaper Publication 7 Nov") == "Newspaper Publication"


def test_commercial_paper_repayment_is_routine_not_a_raise():
    d = decide(FakeLLM({}), "Intimation of Repayment of Commercial Paper (CP)", "")
    assert d["category"] == "fund_raise" and not d["never_collapse"]
    assert d["materiality"] < ROUTINE_BELOW
    assert decide(FakeLLM({}), "Issue of Commercial Paper", "")["never_collapse"]
