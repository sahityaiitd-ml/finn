"""Fetch recent announcements per holding from screener.in and upsert into filings."""

from __future__ import annotations

import hashlib
import time

import httpx
from supabase import Client

from extract.screener import Announcement, parse_announcements

UA = "FINN-research-bot/0.1 (educational project)"
DELAY_S = 1.5  # one polite request per company


def filing_id(symbol: str, a: Announcement) -> str:
    return hashlib.sha1(f"{symbol}|{a.url}".encode()).hexdigest()[:20]


def to_row(symbol: str, a: Announcement) -> dict:
    return {
        "id": filing_id(symbol, a),
        "symbol": symbol,
        "headline": a.title,
        "description": a.description,
        "url": a.url,
        "published_at": a.published_at.isoformat(),
    }


def run(db: Client, delay: float = DELAY_S) -> dict:
    symbols = [r["symbol"] for r in db.table("portfolio_holdings").select("symbol").execute().data]
    symbols = sorted(set(symbols))
    fetched, errors = 0, []
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=30) as c:
        for s in symbols:
            try:
                r = c.get(f"https://www.screener.in/company/{s}/consolidated/")
                r.raise_for_status()
                rows = [to_row(s, a) for a in parse_announcements(r.text)]
                if rows:
                    db.table("filings").upsert(rows, ignore_duplicates=True).execute()
                fetched += len(rows)
            except Exception as e:  # keep going; report per-symbol failures
                errors.append({"symbol": s, "error": str(e)[:120]})
            time.sleep(delay)
    return {"companies": len(symbols), "filings_seen": fetched, "errors": errors}
