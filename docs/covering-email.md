# Covering email (draft)

**To:** assessment@enam.com
**Subject:** IIT Delhi – AI Engineer - 2027

---

Hello,

Please find my submission for the AI Engineer Build Challenge.

**Links**
- Prototype (open on a phone): https://finn-ruddy.vercel.app (the free API host sleeps when idle, so the first load after a quiet spell can take about a minute)
- Android app (APK, tap to install): https://github.com/sahityaiitd-ml/finn/releases/download/android-latest/finn.apk (allow "install unknown apps" once; on iPhone, open the prototype link and use Share → Add to Home Screen)
- Repository: https://github.com/sahityaiitd-ml/finn
- AI build history: https://github.com/sahityaiitd-ml/finn/blob/main/docs/ai-build-history/claude-code-session.md (the Claude Code conversation, readable and redacted; attached as a file too), plus `docs/build-log.md` for the decisions

**What I built.** FINN, a mobile-first investor agent with one rule: evidence, not verdicts.
- A **ranked filings digest** for an 18-stock demo portfolio: rules classify the filings, a hard floor keeps material types on screen, routine paperwork collapses into one drawer, and the screen ends in "All caught up".
- A **results first cut**: Revenue, EBITDA, PBT and PAT with QoQ and YoY, parsed from the SEBI results PDF. Python does the arithmetic, and three identity checks per column gate what is shown.
- **Promised vs delivered**: management guidance from the last four calls, each a verbatim quote verified against its page, with a status set in code. No credibility score.
- **End-of-day alerts** (volume and price rules, per-stock overrides, a dry run) whose cause label is only "No related filing found" or "Related filing found, cause unconfirmed".
Every number and quote opens a source sheet at the cited page with the line highlighted.

**Key decisions and trade-offs**
- The model extracts; Python decides. The real risk is a filter that hides a material filing, so the floor, the score and every status are code. In testing the model labelled a compliance-officer change "unclassified"; rules and a "when unsure, show it" default now catch that.
- A failed read is an error, never "no guidance". Groq's free tier rate-limited the large model and an early version silently reported zero promises. I fixed it and moved extraction to Gemini.
- Refuse rather than guess: a scanned page read `31.658` for 31,658. The identity checks blocked it, so it shows "See PDF".
- BSE and NSE return 403 to scripts and I did not work around that. Listings come from screener.in; PDFs come from a hand-downloaded demo set, so tickers outside it show source links instead of numbers.
- Model routing and caching: rules first (90 of 90 filings classified without a model), a small model only for short summaries and leftovers, Gemini for extraction, every call cached forever. The build made 52 distinct model calls.

**Honest limits.** On the four demo tickers no promise could be scored Delivered or Missed: most guidance is segment, volume or FY27 (not yet reported), and TCS says it gives none. The ledger says so instead of forcing a score. Dixon's scanned statements show "See PDF".

**Deliberately left out.** Event timeline, new-executive bio, thesis tracking, annual-report diff, notes-to-accounts red flags, real-time push, live call transcription, credibility scores, banks and NBFCs.

**Where I'd take it next.** Read scans with Gemini vision under the same identity checks; fetch PDFs through a sanctioned channel so any ticker works end to end; per-user portfolios and notifications; and demo tickers whose guidance is numeric so scored rows appear.

Thank you for the opportunity.

Regards,
`<Your name>`
