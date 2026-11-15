# 0007 — End-of-day alerts and cause labels
**Status:** accepted (2026-11-15).

- **One batched yfinance call after the close** (`POST /jobs/eod`, GitHub Actions at 16:30 IST, Mon–Fri), `.NS` first with a `.BO` fallback. Three months of closes and volumes are stored in `prices`, which the dry run reads.
- **Rules:** volume above N × the average of the 20 sessions *before* the day (default 2×), or close-to-close move beyond ±X% (default 5%). A threshold of 0 switches a rule off. Per-stock overrides sit on the holding; an empty override means "use the default".
- **Cause label is one of exactly two strings:** "No related filing found" or "Related filing found, cause unconfirmed". A filing is *related* only if it is for that stock, published between the previous close (15:30 IST) and this one, and not routine (floored or materiality ≥ 30). A routine ESOP allotment is never offered as a possible cause. FINN never states or ranks a cause.
- **A price move is never coloured.** The card shows the signed number in plain ink.
- **Alerts are never collapsed**: they join the Today feed as always-shown items, ranked below results, M&A and litigation.
- **Dry run** replays the last 21 sessions over stored prices at the chosen settings, with the same cause rule, so the number a user sees is what would have happened.
- **Lessons from testing:** the API caps a request at 1,000 rows, so reading the price history pages through results (a truncated read would have silently corrupted the dry run); browser saves of settings use PUT/DELETE, which CORS must allow; and a server-rendered page cannot carry a click handler, which a build does not catch.
- **Not built:** per-user alerts and push notifications (one shared demo portfolio; the "Evening digest" switch is shown as "coming soon").
