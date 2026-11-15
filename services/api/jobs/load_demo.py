"""Load the committed/local demo snapshot into Supabase: companies, portfolio, PDFs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.db import get_client
from app.storage import ingest_pdf
from extract.pdfs import demo_docs

DEMO = Path(__file__).resolve().parents[3] / "data" / "demo"
PORTFOLIO_NAME = "Demo portfolio"


def main() -> None:
    db = get_client()
    companies = json.loads((DEMO / "companies.json").read_text())
    db.table("companies").upsert(
        [
            {"symbol": c["symbol"], "name": c["name"], "bse_code": c["bse_code"], "grp": c["group"]}
            for c in companies
        ]
    ).execute()

    existing = db.table("portfolios").select("id").eq("name", PORTFOLIO_NAME).execute().data
    pid = (
        existing[0]["id"]
        if existing
        else (db.table("portfolios").insert({"name": PORTFOLIO_NAME}).execute().data[0]["id"])
    )
    db.table("portfolio_holdings").upsert(
        [
            {"portfolio_id": pid, "symbol": c["symbol"]}
            for c in companies
            if c["group"] == "portfolio"
        ]
    ).execute()
    print(f"portfolio {pid}: {sum(c['group'] == 'portfolio' for c in companies)} holdings")

    for d in demo_docs(DEMO):
        sha, created = ingest_pdf(db, d.path, symbol=d.symbol, kind=d.kind, period=d.period)
        print(
            ("stored " if created else "have   ")
            + f"{d.kind:10} {d.symbol:10} {d.period} {sha[:10]}"
        )


if __name__ == "__main__":
    sys.exit(main())
