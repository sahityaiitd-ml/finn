"""Shape end-of-day alerts as Today-feed items. Pure functions."""

from __future__ import annotations

from datetime import date, datetime

from extract.eod import CLOSE, IST

ALERT_MATERIALITY = 55  # ranks below results / M&A / litigation, above routine paperwork


def alert_item(a: dict, names: dict[str, str], filings: dict[str, dict]) -> dict:
    d = a["detail"]
    close = datetime.combine(date.fromisoformat(a["d"]), CLOSE, IST)
    related = [filings[i] for i in d.get("filing_ids", []) if i in filings]
    return {
        "id": a["id"],
        "symbol": a["symbol"],
        "name": names.get(a["symbol"], a["symbol"]),
        "category": "eod_alert",
        "headline": "End-of-day alert",
        "summary": None,
        "published_at": close.isoformat(),
        "source_url": related[0]["url"] if related else None,
        "never_collapse": True,  # an alert is never hidden
        "materiality": ALERT_MATERIALITY,
        "reviewed": bool(d.get("reviewed")),
        "alert": {
            "triggered": d["triggered"],
            "ratio": d["ratio"],
            "vol_mult": d["vol_mult"],
            "pct": d["pct"],  # shown plainly: a price move is never coloured
            "price_pct": d["price_pct"],
            "cause_label": a["cause_label"],
            "filings": [{"headline": f["headline"], "url": f["url"]} for f in related],
        },
    }
