"""Parse every stored results PDF and upsert into `results`. Rules only, no model calls."""

from __future__ import annotations

from supabase import Client

from extract.results import parse_results, restatement_flags, to_dict


def run(db: Client) -> dict:
    docs = db.table("documents").select("sha256,symbol,period").eq("kind", "results").execute().data
    docs.sort(key=lambda d: d["period"] or "")
    done: dict[str, dict] = {}  # symbol -> latest parsed dict so far (for restatement flags)
    counts = {"ok": 0, "see_pdf": 0, "unsupported": 0}
    for d in docs:
        pages = [
            r["text"]
            for r in db.table("doc_pages").select("page,text").eq("sha256", d["sha256"])
            .order("page").execute().data
        ]  # fmt: skip
        parsed = to_dict(parse_results(pages))
        parsed["flags"] = parsed["flags"] + restatement_flags(parsed, done.get(d["symbol"]))
        done[d["symbol"]] = parsed
        counts[parsed["status"]] += 1
        db.table("results").upsert(
            {
                "symbol": d["symbol"],
                "period": d["period"],
                "doc_sha256": d["sha256"],
                "basis": parsed["basis"],
                "parsed": parsed,
                "checks": parsed["checks"],
                "status": parsed["status"],
                "flags": parsed["flags"],
            },
            on_conflict="symbol,period,doc_sha256",
        ).execute()
    return {"documents": len(docs), **counts}
