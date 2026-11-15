# 0006 — Promised vs delivered: what the model may do, what Python decides
**Status:** accepted (2026-11-15).

**The model extracts; Python decides.** A model reads up to six forward-looking transcript pages per call and returns quotes with the page, metric, basis, qualifier, spoken period and any number. Python then:

1. **Verifies every quote** against its cited page (rapidfuzz ≥ 90) or drops it. A number the model returns must appear in the quote, otherwise the item becomes Vague.
2. **Checks the metric label** against the words around the quote. "Exit at 25% plus" is not a margin unless the page says margin. Unsupported labels become `other`, which is never compared.
3. **Resolves the period** ("FY27", "next quarter", "second half") from the call's quarter. Ambiguous phrases ("going forward", "this quarter") stay unresolved.
4. **Sets the status.** Vague (no number: never scored) → Not yet due (period after the latest reported results) → No comparable actual (period unresolved, not a percentage metric, constant-currency / organic / segment, or no matching figure in the results) → otherwise Delivered / Partly / Missed.

**Status thresholds.** Every guided metric is higher-is-better. Beating a target is Delivered. A miss within 0.5 pp (margins) or 2 pp (growth) of the threshold is Partly; anything worse is Missed. "Around X" is met within the same band below X. "Double-digit" is read as at least 10%. There is no score.

**Reported side** comes only from parsed results (identity-checked columns), never from the transcript. Margin and growth are computed in Python; "operating margin" is compared with a derived EBIT margin and labelled as such.

**Honesty rules.** A failed model call is an error, never "no guidance": the job becomes `partial` and is not cached. Tickers whose transcripts cannot be fetched show the links and nothing else.

**Providers.** Gemini (`gemini-3.5-flash`, several keys rotated on rate limits) is the default for extraction; Groq `openai/gpt-oss-120b` is the fallback. Groq's free tier allows 8,000 tokens per minute, which a six-page call nearly fills. 2.5-flash is closed to new users.
