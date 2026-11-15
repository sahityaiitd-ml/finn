from datetime import UTC, datetime
from pathlib import Path

from extract.pdfs import demo_docs, extract_pages, sha256_file
from extract.screener import Announcement
from jobs.fetch_filings import filing_id, to_row

DEMO = Path(__file__).resolve().parents[3] / "data" / "demo"


def test_demo_docs_parse_names():
    docs = demo_docs(DEMO)
    tcs = [d for d in docs if d.symbol == "TCS" and d.kind == "transcript"]
    assert {d.period for d in tcs} == {"2025-12", "2026-03", "2026-06", "2026-09"}
    assert any(d.kind == "results" and d.symbol == "TCS" for d in docs)


def test_sha256_stable_and_pages_have_text():
    p = DEMO / "results" / "TCS_2026-09.pdf"
    assert sha256_file(p) == sha256_file(p) and len(sha256_file(p)) == 64
    pages = extract_pages(p)
    assert len(pages) == 22 and "TCS" in pages[0]


def test_filing_id_is_stable_and_unique_per_symbol():
    a = Announcement("t", datetime(2026, 11, 13, tzinfo=UTC), "d", "https://x/y.pdf")
    assert filing_id("TCS", a) == filing_id("TCS", a)
    assert filing_id("TCS", a) != filing_id("INFY", a)
    assert to_row("TCS", a)["url"] == "https://x/y.pdf"
