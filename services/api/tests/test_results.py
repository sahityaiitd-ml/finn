import json
from pathlib import Path

from extract.pdfs import extract_pages
from extract.results import (
    change_pct,
    detect_basis,
    parse_number,
    parse_results,
    restatement_flags,
    split_line,
    to_dict,
)

DEMO = Path(__file__).resolve().parents[3] / "data" / "demo" / "results"
FIXTURES = Path(__file__).parent / "fixtures" / "results"


def parsed(sym: str):
    """Statement pages are saved as small fixtures so every filing is tested in CI."""
    fx = json.loads((FIXTURES / f"{sym}_2026-09.json").read_text())
    pages = [""] * fx["n_pages"]
    for no, text in fx["pages"].items():
        pages[int(no) - 1] = text
    return parse_results(pages)


def test_fixtures_match_the_real_pdf():
    pdf = DEMO / "TCS_2026-09.pdf"
    fx = json.loads((FIXTURES / "TCS_2026-09.json").read_text())
    assert extract_pages(pdf)[7] == fx["pages"]["8"]


# ---------- units ----------
def test_parse_number_variants():
    assert parse_number("1,45,463") == 145463
    assert parse_number("(1,326)") == -1326
    assert parse_number("-") == 0
    assert parse_number("42,535.28") == 42535.28
    assert parse_number("13.792.34") is None  # OCR damage is rejected, never guessed
    assert parse_number("Total") is None


def test_split_line_ignores_label_numbers_and_trailing_damage():
    label, vals = split_line("Total income ( 1 + 2] 43,103.55 37,387.56 35,290.03 80,491.11 x 9")
    assert label.startswith("Total income") and vals[:3] == [43103.55, 37387.56, 35290.03]
    _, vals = split_line("Total income 3,734.96 3,936.95 3,331.45 7.671.91 6,880.00 13.792.34")
    assert vals == [3734.96, 3936.95, 3331.45]
    assert split_line("Profit before tax 12 34")[1] == []  # fewer than 3 numbers


def test_detect_basis_prefers_whichever_appears_first():
    assert detect_basis("Audited Consolidated Interim Statement ...") == "consolidated"
    assert detect_basis("Standalone Statement of Profit and Loss") == "standalone"
    assert detect_basis("Statement of results") is None


def test_change_pct():
    assert change_pct(110, 100) == 10.0
    assert change_pct(5, 0) is None
    assert change_pct(5, -2) is None
    assert change_pct(None, 5) is None


def test_bank_format_unsupported():
    page = "Interest Earned 100 90 80\nTotal Income 120 100 90\nTotal expenses 90 80 70"
    # banks have no finance cost line, so the statement finder skips them -> not "ok"
    assert parse_results([page]).status in ("see_pdf", "unsupported")


# ---------- five real filings ----------
def test_tcs_consolidated():
    r = parsed("TCS")
    d = to_dict(r)
    assert r.status == "ok" and r.basis == "consolidated" and r.column_ok[:3] == [True] * 3
    assert d["metrics"]["revenue"]["values"][:3] == [73188, 72275, 65799]
    assert d["metrics"]["pbt"]["values"][:3] == [18638, 17944, 16068]
    assert d["metrics"]["pat"]["values"][:3] == [13934, 13420, 12131]
    # EBITDA = PBT(pre-exceptional) + finance cost + D&A - other income, done in Python
    assert r.derived["ebitda"][0] == 18638 + 252 + 1262 - 1337
    assert r.derived["exceptional"][:3] == [0, -668, -1135]  # shown separately, signed
    assert r.flags == []
    assert d["metrics"]["revenue"]["page"] == 8  # every figure carries its page


def test_reliance_consolidated_prefers_consolidated_over_standalone():
    r = parsed("RELIANCE")
    assert r.status == "ok" and r.basis == "consolidated" and r.page == 10
    assert r.metrics["revenue"].values[0] == 332861
    assert r.derived["ebitda"][0] == 38613 + 8481 + 15315 - 5793


def test_tata_steel_handles_jv_line_and_flags_exceptional():
    r = parsed("TATASTEEL")
    assert r.status == "ok" and r.basis == "consolidated"
    assert r.metrics["pat"].values[0] == 3699.59
    assert r.derived["exceptional"][0] == 348.68
    assert "exceptional_item" in r.flags


def test_dabur_ocr_damage_fails_only_the_damaged_column():
    r = parsed("DABUR")
    assert r.status == "ok" and r.column_ok[:3] == [True, True, False]
    assert r.derived["ebitda"][2] is None  # year-ago column shows "see PDF", not a guess
    assert "other_income_gt_20pct_pbt" in r.flags


def test_maruti_scanned_page_never_shows_a_guess():
    r = parsed("MARUTI")
    assert r.status == "see_pdf"
    assert r.column_ok[:3] == [False, False, False]
    assert r.derived == {}


# ---------- restatement / basis switch ----------
def test_restatement_and_basis_switch_flags():
    cur = {
        "status": "ok",
        "basis": "consolidated",
        "metrics": {
            "revenue": {"values": [200, 150, 100]},
            "pbt": {"values": [1, 2, 3]},
            "pat": {"values": [1, 2, 3]},
        },
    }
    prior = {
        "status": "ok",
        "basis": "standalone",
        "metrics": {
            "revenue": {"values": [140, 0, 0]},
            "pbt": {"values": [2, 0, 0]},
            "pat": {"values": [2, 0, 0]},
        },
    }
    assert restatement_flags(cur, prior) == ["basis_switch", "restated_periods"]
    assert restatement_flags(cur, None) == []
