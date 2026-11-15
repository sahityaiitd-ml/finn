# 0004 — Filings source
**Status:** accepted (2026-11-15).

**Finding.** BSE (announcements API, RSS, and PDF links) returns 403 "Access Denied" (Akamai) to scripted requests, even with an honest user agent; NSE does not respond. We do not work around bot protection.

**Decision.**
1. **Listings** come from screener.in company pages (robots.txt allows `/company/`; the brief names screener.in as a source). Each page lists recent announcements (time, title, description, BSE link), concall transcript links and annual-report links. This is enough for the digest (B), the alert cause label, and transcript/annual-report discovery (A).
2. **PDF bytes** are on BSE and cannot be fetched by script. Results (C) and transcript text (A) therefore run from a committed demo set: PDFs a person downloaded by hand into `data/demo/`, keyed by SHA-256. Tickers outside the demo set show the link and "document not available here" rather than a guess.
3. If a company serves the same PDF on its own IR site, the fetcher may use it (to add per ticker).
4. Be polite: one request per company per run, honest user agent, cached.
