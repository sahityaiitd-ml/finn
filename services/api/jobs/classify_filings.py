"""Classify unclassified filings: rules first, small model for leftovers and summaries."""

from __future__ import annotations

from supabase import Client

from extract.llm import Completer, GroqCompleter, analyse
from rules.classify import FLOOR_CATEGORIES, Verdict, classify, is_generic_headline
from rules.materiality import materiality


def decide(llm: Completer, headline: str, description: str) -> dict:
    """Pure decision for one filing. Returns the columns to store."""
    verdict = classify(headline, description)
    summary = None
    by = "rule"
    if verdict is None:
        cat, summary = analyse(llm, headline, description)
        by = "llm8b"
        if cat == "unsure":
            # unsure: show it, never hide it
            verdict = Verdict("press_release", "llm_unsure", True, "unsure")
        else:
            floored = cat in FLOOR_CATEGORIES
            verdict = Verdict(cat, "llm", floored, f"floor:{cat}" if floored else None)
    elif is_generic_headline(headline) and description:
        _, summary = analyse(llm, headline, description)
    score = materiality(verdict.category, headline, description, verdict.never_collapse)
    if verdict.rule == "repay":
        score = 20  # repaying a commercial paper is routine; it is not a fund-raise
    return {
        "category": verdict.category,
        "classified_by": by,
        "materiality": score,
        "never_collapse": verdict.never_collapse,
        "summary": summary,
    }


def run(db: Client, llm: Completer | None = None, reclassify: bool = False) -> dict:
    llm = llm or GroqCompleter(db)
    q = db.table("filings").select("*")
    todo = (q if reclassify else q.is_("category", "null")).execute().data
    out = {"classified": 0, "by_rule": 0, "by_llm": 0, "floored": 0}
    batch = []
    for r in todo:
        d = decide(llm, r["headline"], r.get("description") or "")
        out["classified"] += 1
        out["by_rule" if d["classified_by"] == "rule" else "by_llm"] += 1
        out["floored"] += int(d["never_collapse"])
        batch.append({**r, **d})
    for i in range(0, len(batch), 50):
        db.table("filings").upsert(batch[i : i + 50]).execute()
    return out
