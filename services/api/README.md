---
title: FINN API
emoji: 📈
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# FINN API

FastAPI service for FINN (filings digest, results first cut, promised-vs-delivered ledger,
end-of-day alerts). This folder is deployed as a Hugging Face Docker Space. See the repository
root `README.md` and `docs/deploy.md`.

Secrets (Space settings → Variables and secrets): `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`,
`GROQ_API_KEY`, `GEMINI_API_KEY` (and optionally `GEMINI_API_KEYS`), `JOB_SECRET`,
`CORS_ORIGINS` (your Vercel URL).
