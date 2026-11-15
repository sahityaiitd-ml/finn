# Build log

## 2026-11-15 — M0 scaffold
- Scaffolded repo, CLAUDE.md, docs, CI and cron workflows, FastAPI service, Next.js PWA with Calm-ledger tokens, schema migration.
- Installed uv, Node, pnpm, gh into the user's home dir (no Homebrew on the machine).
- Prompt that mattered: the kickoff brief (docs/PRD.md holds its scope).

## 2026-11-15 — M1 ingestion
- **Finding:** BSE and NSE return 403 to scripted requests (announcements API, RSS, PDFs). We did not work around bot protection (ADR 0004). Listings now come from screener.in (robots.txt allows company pages); PDF bytes come from a hand-downloaded demo set.
- Built: screener parser (announcements, concalls, annual reports, results links), company seed with BSE codes (22 names), SHA-256 PDF storage + per-page text, demo loader, filings job, batched yfinance EOD with .BO fallback.
- Live run: 90 filings from 18 holdings, 21 PDFs (458 pages) stored, 0 errors.
- Decisions: Groq model mapping to gpt-oss-20b/120b (ADR 0003); PDFs over 5 MB stay out of git and live in Supabase Storage; migration 0002 applied by hand in the SQL Editor.
- Prompt that mattered: "try to find better methods for getting the filings, else use demo snapshot" — led to screener.in as the sanctioned source.

## 2026-11-15 — M2 results first cut
- **Parser** (`services/api/extract/results.py`): rules only, no model. Reads the first three numeric columns after each label (this quarter, preceding, year-ago), ignores trailing OCR damage, prefers consolidated, handles JV/associate lines and wrapped labels.
- **Identity checks per column:** revenue + other income = total income; total income − expenses (+ JV share) = PBT before exceptional; PBT − tax = PAT. A failing column shows "See PDF". Nothing is guessed.
- **Python derives** EBITDA = PBT (pre-exceptional) + finance cost + D&A − other income; exceptional shown separately (signed: + gain, − charge); QoQ/YoY and margin bp.
- **Real-filing results (Sep 2026 quarter):** TCS, Reliance, Tata Steel parse with all checks; Dabur parses with year-ago column failing on OCR damage; Maruti (scanned, "31.658" for 31,658) is blocked as "See PDF". Gating matters: the Maruti PBT would have been off by 1000x.
- Flags built: other income > 20% of PBT, exceptional item, basis switch and restated periods (need a prior stored filing; unit-tested), standalone fallback.
- UI: Results tab from Figma node 23:487, bottom nav, hub tabs, minimal source page with the cited line highlighted.
- Decision: statement pages saved as small fixtures so all five filings are tested in CI even though four PDFs are over 5 MB.
