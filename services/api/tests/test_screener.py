from pathlib import Path

from extract.screener import (
    parse_announcements,
    parse_annual_reports,
    parse_bse_code,
    parse_concalls,
)

HTML = (Path(__file__).parent / "fixtures" / "screener_reliance_docs.html").read_text()


def test_bse_code():
    assert parse_bse_code(HTML) == "500325"


def test_announcements():
    items = parse_announcements(HTML)
    assert len(items) >= 5
    first = items[0]
    assert first.published_at.tzinfo is not None
    assert first.url.startswith("https://www.bseindia.com/")
    assert "Regulation 30" in first.title
    assert first.description and not first.description.startswith("13 Nov")


def test_concalls_have_transcripts():
    docs = parse_concalls(HTML)
    transcripts = [d for d in docs if d.kind == "transcript"]
    assert transcripts and transcripts[0].label == "Nov 2026"


def test_annual_reports():
    ars = parse_annual_reports(HTML)
    assert ars[0].label == "Annual Report 2026"
