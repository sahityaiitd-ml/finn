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


def test_results_pdf_links():
    from extract.screener import parse_results_pdf_links

    html = (
        '<section id="quarters"><a href="/company/source/quarter/3365/9/2026/"></a>'
        '<a href="/company/source/quarter/3365/12/2025/"></a></section>'
    )
    links = parse_results_pdf_links(html)
    assert set(links) == {"2026-09", "2025-12"}
    assert links["2026-09"].startswith("https://www.screener.in/company/source/quarter/")
