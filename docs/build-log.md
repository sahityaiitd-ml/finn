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

## 2026-11-15 — M3 filings digest
- **Classifier:** rules-first, all 17 categories, never-collapse floor, Python materiality. 90/90 live filings classified by rules; the model path is exercised by tests (fake client) and was run live on 4 leftovers earlier, then cached.
- **A real catch:** the model labelled a compliance-officer (KMP) change as "unclassified", which would have hidden it. Fixed with rules, and any model "unsure" now defaults to shown. This is the "filter that labels a material filing routine" risk from the handoff brief.
- **Digest API:** `/digest?window=24h|3d|7d|30d` ranked by materiality; routine drawer; caught-up flag; `/filings/{id}/reviewed`.
- **Today screen** from Figma 01 / 01b: window switch, progress, cards, Mark reviewed (persisted), All caught up, routine drawer. Checked at 375px.
- Known gap: the header count ("N need you") is server-rendered, so it does not drop as items are reviewed.

## 2026-11-15 — M4 promised vs delivered
- **Pipeline:** page picking (6 most forward-looking pages) → model extraction → quote check (rapidfuzz ≥ 90 or dropped) → Python period/target/status rules → job + polling API → Promises tab with loading state. Cached by transcript + results + prompt + rules version.
- **Provider:** Groq's free tier (8,000 tokens/min) rate-limited the 120B model. A first run silently returned "0 promises" — the extractor swallowed a 429. Fixed: retry with the server's `retry-after`, and a failed read is now an error (job = partial, never cached as done). Then moved extraction to Gemini (`gemini-3.5-flash`, two keys rotated); 2.5-flash is closed to new users. Zero unverified quotes on all four tickers.
- **Guards that earned their keep:** a metric label must be supported by the words around the quote ("exit at 25% plus" is not a margin); a number must appear in the quote; "double-digit" is an explicit "≥ 10%" rule.
- **Honest outcome:** 76 → ~80 promises across TCS, Dabur, Tata Steel, Dixon; none scoreable as Delivered/Missed/Partly. Most guidance is segment, volume, per-tonne, capex or FY27 (not yet reported); TCS says it gives no guidance. The ledger shows this rather than forcing a score.
- **Results parser widened** to six columns (quarter, preceding, year-ago, half/nine-month, same last year, full year) with unit detection (crore/lakh/million; unclear → never compared), tolerance for squashed spaces ("Profitbefore tax"), and Dixon as a sixth filing. Dixon's scanned Mar/Jun 2026 statements fail the identity checks and show "See PDF" (Gemini vision on scanned pages is a next step).
- **Any ticker:** discovery works from screener.in; BSE blocks the PDF download (403), so tickers without stored transcripts show the links and "nothing is guessed" (tested with Titan).

## 2026-11-15 — M5 alerts, alert rules, profile
- **EOD job:** one batched yfinance call for the 18 holdings, 1,134 price rows stored; alert rules (volume vs the 20-session average, price move), per-stock overrides, 0 = rule off. At the defaults the latest session (13 Nov) had no alerts, and none were invented.
- **Cause label:** exactly two strings; a filing is related only if material, for that stock, and filed between the previous close and this one. Routine filings never count.
- **Screens from Figma 05/09:** Alert rules (default thresholds with switches, overrides, dry run, cause-label and never-collapsed explainers), Profile (coverage, preferences), a digest-window picker that Today now defaults to, and the alert card on Today (volume ×, price move in plain ink, cause label).
- **Cron:** `fetch-filings` now also classifies (chained), and `eod` runs at 16:30 IST on market days.
- **Bugs the browser caught, not the unit tests:** (1) the API's CORS allowed only GET/POST, so PUT/DELETE settings silently failed; (2) my digest edit had not applied (a formatter had reflowed the block), so alerts never reached Today; (3) a read-only switch carried a click handler, which a server-rendered page cannot do and `next build` does not detect. Each now has a regression test or an endpoint-level test.
- **Data pitfall:** the API returns at most 1,000 rows per request; price history is now read in pages. Before the fix the dry run silently dropped the newest 134 rows.
- **Demo check:** with temporary sensitive thresholds (1.3× / 1.5%) the real data produced four alerts, which rendered correctly on Today; they were deleted and the defaults restored.

## 2026-11-15 — M6 polish, docs, deploy kit
- **Source bottom sheet** from Figma 06/06b: opens at the cited page (≈75% height), highlights the cited line or the fuzzy-located quote span, shows "FINN read … Matches the page exactly" or "Line not located", previous/next page, Copy citation, and Open PDF (a signed link, since the bucket is private). Esc and the backdrop close it; it falls back to a normal page link without JavaScript.
- **Two-column layout at ≥ 1024 px** for Today, Promises and Results; settings pages stay one readable column.
- **Offline snapshot** (`data/demo/snapshot/`): filings and the precomputed promise ledgers, restored into empty tables by `jobs.load_demo`.
- **Deploy kit:** Hugging Face Space metadata, an optional `deploy-space` workflow (does nothing until `HF_TOKEN`/`HF_SPACE` are set), `docs/deploy.md`. The Docker image could not be built here (no Docker on this machine); its Python step was reproduced in a clean `uv sync --no-dev` environment and every module imports. Removed the unused Tesseract install from the Dockerfile.
- **Docs:** README in the requested order with real numbers (52 distinct model calls over the whole build; 90/90 filings classified by rules), architecture, six screenshots at 390 px, and the covering-email draft addressed per the brief.
- **Checked:** sheet opens on a results line and a transcript quote, closes with Esc, pages navigate; laptop layout at 1100 px. The amber "Line not located" state was also checked in the browser with a temporary test page (since deleted). Not checked: the deployed apps.

## 2026-11-15 — Deploy: Hugging Face → Render
- **Finding:** Hugging Face now makes Docker Spaces a paid plan; only Static Spaces are free. The kickoff's "FastAPI on a HF Space" is no longer possible on a free tier.
- **Change:** the API deploys to Render's free web service from `render.yaml` (Docker, health check `/health`, secrets entered in the dashboard). The Dockerfile now listens on the platform's `PORT`. The Hugging Face metadata and the `deploy-space` workflow are removed. The design is unchanged: the service sleeps, so scheduling stays in GitHub Actions and the cron retries while it wakes. ADR 0001 has an amendment.

## 2026-11-15 — Live
- Deployed: web on Vercel (https://finn-ruddy.vercel.app), API on Render (https://finn-api-d58i.onrender.com). The Render name `finn-api` was already taken, so the service has a random suffix; an early guess at the default URL answered 200 from *someone else's* service (different `/health` body), which is why nothing was sent there.
- Verified live: health with database connected; digest 11 to review / 21 routine; TCS results with the source sheet (page 8 of 22, line highlighted) and a working signed PDF link; mark-reviewed and an alert-threshold change persisted from the Vercel site; any-ticker path (Titan) returns "not available" with four links; CORS allows only the Vercel origin and localhost.
- Cron: `POST /jobs/eod` and `POST /jobs/fetch-filings` both ran successfully from GitHub Actions with the secret (18 of 18 symbols priced; 90 filings seen, 0 errors).
- Test data created during these checks (one reviewed flag, one threshold change) was reset.

## 2026-11-15 — Downloadable Android app, install-ready PWA
- **Android:** `apps/android` wraps the live web app in a Capacitor WebView (so the app and the website are always the same version). GitHub Actions builds the APK (no local Android SDK needed) and publishes it at a fixed link: `releases/download/android-latest/finn.apk`. It built on the first run; the artifact was downloaded and inspected: 4 MB, package `app.finn.investor`, live URL baked in, launcher icons at every density, offline fallback page, v2-signed (debug key, so Play Protect may ask to confirm). Not tested on a physical phone here.
- **iOS:** not possible without an Apple Developer account (signing / TestFlight); iPhone users use Add to Home Screen.
- **PWA:** PNG icons (192, 512, maskable 512, Apple touch 180) generated by `apps/web/scripts/make-icons.py`; manifest now has `id`, `scope`, `orientation`, categories and the PNG icons; Apple web-app metadata added.
