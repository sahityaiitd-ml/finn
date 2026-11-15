"""Export / restore the demo snapshot: filings and promise ledgers as small JSON files.

The snapshot is the last fallback when no live source can be reached, so the demo still runs
offline. PDFs are not included here (they are in data/demo or Supabase Storage).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from supabase import Client

SNAP = Path(__file__).resolve().parents[3] / "data" / "demo" / "snapshot"
TABLES = ["filings", "guidance", "promise_matches"]


def _all(db: Client, table: str) -> list[dict]:
    out, start = [], 0
    while True:
        rows = db.table(table).select("*").range(start, start + 999).execute().data
        out += rows
        if len(rows) < 1000:
            return out
        start += 1000


def export(db: Client, root: Path = SNAP) -> dict[str, int]:
    root.mkdir(parents=True, exist_ok=True)
    counts = {}
    for t in TABLES:
        rows = _all(db, t)
        rows.sort(key=lambda r: str(r.get("id") or r.get("guidance_id")))
        (root / f"{t}.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n")
        counts[t] = len(rows)
    return counts


def restore(db: Client, root: Path = SNAP) -> dict[str, int]:
    """Load the snapshot into empty tables. Existing rows are never overwritten."""
    counts = {}
    for t in TABLES:
        f = root / f"{t}.json"
        rows = json.loads(f.read_text()) if f.exists() else []
        have = db.table(t).select("*", count="exact").limit(1).execute().count or 0
        if rows and have == 0:
            for i in range(0, len(rows), 200):
                db.table(t).upsert(rows[i : i + 200]).execute()
        counts[t] = len(rows) if have == 0 else 0
    return counts


if __name__ == "__main__":
    from app.db import get_client

    fn = {"export": export, "restore": restore}[sys.argv[1] if len(sys.argv) > 1 else "export"]
    print(fn(get_client()))
