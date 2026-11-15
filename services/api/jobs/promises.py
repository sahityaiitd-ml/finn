"""Promised-vs-delivered ledger for one ticker. Idempotent and cached.

Cache key = sha256(symbol + transcript hashes + results hashes + prompt version + rules version),
so the ledger is rebuilt only when an input changes.
"""

from __future__ import annotations

import hashlib
import re
import tempfile
from pathlib import Path

import httpx
from supabase import Client

from app.storage import ingest_pdf
from extract.guidance import PROMPT_VERSION, extract
from extract.llm import Completer, big_completer
from extract.promises import (
    RULES_VERSION,
    build_actuals,
    decide_status,
    horizon_end,
    quarter_label,
)
from extract.screener import parse_concalls

UA = "FINN-research-bot/0.1 (educational project)"
MAX_CALLS = 4  # the last four quarters
METRIC_LABELS = {
    "revenue_growth": "Revenue growth", "ebitda_margin": "EBITDA margin",
    "ebitda_growth": "EBITDA growth", "ebit_margin": "EBIT margin (derived)",
    "pat_growth": "PAT growth", "revenue_level": "Revenue", "ebitda_level": "EBITDA",
    "pat_level": "PAT", "pbt_growth": "PBT growth", "capex": "Capex",
    "volume_growth": "Volume growth", "order_book": "Order book", "other": "Other",
}  # fmt: skip
ORDER = {"Missed": 0, "Partly": 1, "Delivered": 2, "Not yet due": 3, "No comparable actual": 4,
         "Vague": 5}  # fmt: skip
_M = "jan feb mar apr may jun jul aug sep oct nov dec".split()
MONTHS = {m: i + 1 for i, m in enumerate(_M)}


def quarter_end_for_call(label: str) -> str | None:
    """'Nov 2026' -> '2026-09': the last quarter end strictly before the call month."""
    m = re.match(r"([A-Za-z]{3})\w*\s+(\d{4})", label.strip())
    if not m or m.group(1).lower() not in MONTHS:
        return None
    month, year = MONTHS[m.group(1).lower()], int(m.group(2))
    for qm in (12, 9, 6, 3):
        if qm < month:
            return f"{year}-{qm:02d}"
    return f"{year - 1}-12"


def transcript_docs(db: Client, symbol: str) -> list[dict]:
    rows = (
        db.table("documents").select("sha256,period,n_pages")
        .eq("symbol", symbol).eq("kind", "transcript").order("period", desc=True)
        .limit(MAX_CALLS).execute().data
    )  # fmt: skip
    return rows


def results_rows(db: Client, symbol: str) -> list[dict]:
    return (
        db.table("results").select("period,doc_sha256,parsed").eq("symbol", symbol).execute().data
    )


def ledger_key(symbol: str, docs: list[dict], results: list[dict]) -> str:
    parts = [symbol, *sorted(d["sha256"] for d in docs), *sorted(r["doc_sha256"] for r in results)]
    parts += [PROMPT_VERSION, RULES_VERSION]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def discover(db: Client, symbol: str) -> dict:
    """Find transcripts for a ticker we have not stored. Fetches only what the source allows."""
    r = httpx.get(
        f"https://www.screener.in/company/{symbol}/consolidated/",
        headers={"User-Agent": UA}, follow_redirects=True, timeout=30,
    )  # fmt: skip
    if r.status_code != 200:
        return {"state": "unavailable", "reason": "company page not found", "links": []}
    links = [d for d in parse_concalls(r.text) if d.kind == "transcript"][:MAX_CALLS]
    fetched, blocked = 0, []
    for d in links:
        period = quarter_end_for_call(d.label)
        try:
            pdf = httpx.get(d.url, headers={"User-Agent": UA}, follow_redirects=True, timeout=45)
            if pdf.status_code == 200 and pdf.content[:4] == b"%PDF" and period:
                with tempfile.TemporaryDirectory() as tmp:
                    f = Path(tmp) / "t.pdf"
                    f.write_bytes(pdf.content)
                    ingest_pdf(
                        db, f, symbol=symbol, kind="transcript", period=period, source_url=d.url
                    )
                fetched += 1
                continue
        except Exception:
            pass
        blocked.append({"label": d.label, "url": d.url})
    return {"state": "ok" if fetched else "unavailable", "fetched": fetched, "links": blocked}


def run(db: Client, symbol: str, llm: Completer | None = None, on_progress=None) -> dict:
    llm = llm or big_completer(db)
    docs = transcript_docs(db, symbol)
    discovery = None
    if not docs:
        discovery = discover(db, symbol)
        docs = transcript_docs(db, symbol)
    if not docs:
        return {"state": "unavailable", "reason": "transcripts could not be fetched automatically",
                "links": (discovery or {}).get("links", [])}  # fmt: skip

    results = results_rows(db, symbol)
    actuals, horizon = build_actuals(results), horizon_end(results)
    counts: dict[str, int] = {}
    progress = [
        {"period": d["period"], "label": f"{quarter_label(d['period'])} call",
         "pages": d["n_pages"], "status": "queued", "promises": 0}
        for d in docs
    ]  # fmt: skip

    def report(i: int, status: str, promises: int = 0) -> None:
        progress[i].update(status=status, promises=promises)
        if on_progress:
            on_progress(progress)

    dropped = 0
    errors: list[dict] = []
    for i, d in enumerate(docs):
        report(i, "reading")
        pages = {r["page"]: r["text"] for r in db.table("doc_pages").select("page,text")
                 .eq("sha256", d["sha256"]).execute().data}  # fmt: skip
        ex = extract(llm, pages)
        dropped += ex.dropped_quote
        if ex.error:  # a failed read is not "no guidance": keep old rows and report it
            errors.append({"call": d["period"], "error": ex.error})
            report(i, "error")
            continue
        db.table("guidance").delete().eq("doc_sha256", d["sha256"]).execute()
        rows = [
            {
                "symbol": symbol, "doc_sha256": d["sha256"], "page": it.page,
                "quarter": d["period"], "metric": it.metric, "quote": it.quote,
                "prompt_version": PROMPT_VERSION,
                "target": {
                    "direction": it.direction, "low": it.low, "high": it.high, "unit": it.unit,
                    "basis": it.basis, "qualifier": it.qualifier, "period": it.period,
                    "match_score": it.match_score, "start": it.start, "end": it.end,
                },
            }
            for it in ex.items
        ]  # fmt: skip
        if not rows:
            report(i, "done", 0)
            continue
        saved = db.table("guidance").insert(rows).execute().data
        matches = []
        for g in saved:
            t = g["target"]
            item = {"metric": g["metric"], "basis": t["basis"], "qualifier": t["qualifier"],
                    "period": t["period"], "direction": t["direction"], "low": t["low"],
                    "high": t["high"], "unit": t["unit"]}  # fmt: skip
            status, detail = decide_status(item, d["period"], actuals, horizon)
            counts[status] = counts.get(status, 0) + 1
            matches.append({"guidance_id": g["id"], "status": status, "detail": detail})
        db.table("promise_matches").upsert(matches).execute()
        report(i, "done", len(matches))
    return {"state": "partial" if errors else "done", "calls": len(docs),
            "promises": sum(counts.values()), "counts": counts, "progress": progress,
            "dropped_unverified_quotes": dropped, "errors": errors}  # fmt: skip


def ledger(db: Client, symbol: str) -> list[dict]:
    g = db.table("guidance").select("*").eq("symbol", symbol).execute().data
    ids = [x["id"] for x in g]
    m = {}
    if ids:
        for i in range(0, len(ids), 100):
            for r in (
                db.table("promise_matches")
                .select("*")
                .in_("guidance_id", ids[i : i + 100])
                .execute()
                .data
            ):
                m[r["guidance_id"]] = r
    out = []
    for x in g:
        pm = m.get(x["id"])
        if pm is None:
            continue
        t, d = x["target"], pm["detail"]
        out.append(
            {
                "id": x["id"], "quote": x["quote"], "page": x["page"], "sha256": x["doc_sha256"],
                "call_period": x["quarter"], "call": f"{quarter_label(x['quarter'])} call",
                "metric": x["metric"], "metric_label": METRIC_LABELS.get(x["metric"], "Other"),
                "status": pm["status"], "target": d.get("target", ""), "period": d.get("period"),
                "reported": d.get("reported"), "reason": d.get("reason"), "source": d.get("source"),
                "start": t.get("start"), "end": t.get("end"),
            }
        )  # fmt: skip
    out.sort(key=lambda r: (-int(r["call_period"].replace("-", "")), ORDER[r["status"]]))
    return out
