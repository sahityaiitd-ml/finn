# 0005 — Classification, floor and routine rules
**Status:** accepted (2026-11-15).

- **Rules first.** An ordered regex table maps headline + description to the 17 ENAM categories. On the 90 live filings it classified all 90 (the 80% target was a floor). The small model (`openai/gpt-oss-20b`, cached) handles only what the rules miss, and writes the ≤25-word summary only where the headline says little. Python rejects summaries over 25 words or with a number not present in the source text.
- **Never-collapse floor:** results, board outcomes, M&A, auditor or KMP change, credit rating, pledge, litigation, fund-raise. Auditor change is "unclassified" in the reference doc, so it has its own rule and floor reason.
- **When unsure, show.** A model "unsure", bad JSON, an error or an unknown category all become never-collapse. A model-labelled floor category is floored too.
- **Judgement calls.** (1) Repaying a commercial paper is `fund_raise` but routine, not a raise, so it scores 20 and may be collapsed. (2) A subsidiary dissolved, liquidated or a branch closed is shown as M&A: the reference doc counts selling a stake in a subsidiary, and hiding a closure is the costlier mistake. (3) A compliance-officer appointment is a KMP change.
- **Materiality** is a Python table by category plus keyword boosts (resign, downgrade, default…), lifted to at least 50 for floored items. Routine = score below 30 and not floored.
