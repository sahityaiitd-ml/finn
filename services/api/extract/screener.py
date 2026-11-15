"""Parse the Documents section of a screener.in company page.

screener.in's robots.txt allows /company/ pages. We read link metadata only
(announcement title/time/description, concall and annual-report links). The PDFs
themselves live on BSE; see docs/decisions/0004-filings-source.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from bs4 import BeautifulSoup

BSE_CODE_RE = re.compile(r"bseindia\.com/stock-share-price/[^/]+/[^/]+/(\d{5,6})/")


@dataclass(frozen=True)
class Announcement:
    title: str
    published_at: datetime
    description: str
    url: str


@dataclass(frozen=True)
class DocLink:
    label: str  # e.g. "Nov 2026" or "Annual Report 2026"
    kind: str  # transcript | ppt | annual_report
    url: str


def parse_bse_code(html: str) -> str | None:
    m = BSE_CODE_RE.search(html)
    return m.group(1) if m else None


def parse_announcements(html: str) -> list[Announcement]:
    soup = BeautifulSoup(html, "lxml")
    out: list[Announcement] = []
    box = soup.select_one("#company-announcements-tab")
    if box is None:
        return out
    for a in box.select("ul.list-links li a[href]"):
        t = a.select_one("time[datetime]")
        if t is None:
            continue
        desc_div = a.select_one("div")
        detail = desc_div.get_text(" ", strip=True) if desc_div else ""
        # detail looks like "13 Nov - <description>"
        detail = re.sub(r"^\S+\s+\S+\s+-\s+", "", detail)
        title = a.get_text(" ", strip=True)
        if desc_div:
            title = title.replace(desc_div.get_text(" ", strip=True), "").strip()
        out.append(
            Announcement(
                title=title,
                published_at=datetime.fromisoformat(t["datetime"]),
                description=detail,
                url=a["href"],
            )
        )
    return out


def parse_concalls(html: str) -> list[DocLink]:
    soup = BeautifulSoup(html, "lxml")
    out: list[DocLink] = []
    for li in soup.select("li.flex"):
        label_el = li.select_one("div.ink-600")
        if label_el is None:
            continue
        label = label_el.get_text(strip=True)
        for a in li.select("a.button-chip[href]"):
            text = a.get_text(strip=True).lower()
            if text == "transcript":
                out.append(DocLink(label, "transcript", a["href"]))
            elif text == "ppt":
                out.append(DocLink(label, "ppt", a["href"]))
    return out


def parse_annual_reports(html: str) -> list[DocLink]:
    soup = BeautifulSoup(html, "lxml")
    out: list[DocLink] = []
    for a in soup.select("a[href]"):
        text = a.get_text(strip=True)
        if re.fullmatch(r"Annual Report \d{4}", text):
            out.append(DocLink(text, "annual_report", a["href"]))
    return out
