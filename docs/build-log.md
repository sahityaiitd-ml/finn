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
