# FINN — Product requirements

FINN is a mobile-first AI investor agent. An investor drowns in filings, prices and results. FINN filters: it surfaces the few things that matter and buries the rest.

## 1. What FINN is
- **Push:** a windowed digest of portfolio filings (default 24 h), ranked, routine filings collapsed. Alerts for material filing types and end-of-day moves (volume > N × 20-day average, price beyond ±X%), user-set thresholds.
- **Pull:** on-demand research grounded only in annual reports and concall transcripts. Works for any NSE ticker.
- **Data:** yfinance end-of-day (.NS, fallback .BO); BSE/NSE announcements; transcripts and annual reports from screener.in or company IR.

## 2. MVP scope
- **A. Promised vs. delivered (pull):** last 4 quarters of guidance, each matched to what was reported. Status: Delivered / Missed / Partly / Vague / Not yet due / No comparable actual. Verbatim quote + page link both sides. No credibility score.
- **B. Ranked filings digest (push):** 17 ENAM categories; rules first, model for leftovers. Python materiality score. Never-collapse floor: results, board outcomes, M&A, auditor/KMP change, credit rating, pledge, litigation, fund-raise. Routine drawer. Summary ≤ 25 words. "Caught up" end state.
- **C. Results first cut (push):** parse SEBI Schedule III PDF; Revenue, EBITDA, PBT, PAT with QoQ and YoY. Python derives EBITDA. Identity checks gate every parse; failure shows "see PDF". Flags: other income > 20% of PBT, exceptional items, basis switch, restated periods. Banks/NBFCs: "format not supported".
- **End-of-day alert:** volume > 2× 20-day avg, price beyond ±5%, per-stock overrides. Cause label: "No related filing found" or "Related filing found, cause unconfirmed". Price moves never coloured.

## 3. Screens
Today · Companies · Profile tabs. Company hub with Promises · Results · Filings. Source drawer (bottom sheet ~75%) at the cited page with the line highlighted, or "Line not located". Design: Figma `jXb5rzeDSJaDvsqMi1KApc`, page "v3 · Calm ledger".

## Out of scope
Event/governance timeline, new-executive bio, thesis tracking, annual-report YoY diff, notes-to-accounts red flags, real-time push, live call transcription, credibility scores.
