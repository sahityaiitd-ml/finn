# Deploy

Everything runs on free tiers. Order matters: Supabase → Render → Vercel → GitHub secrets.

## 1. Supabase (once)
1. New project. SQL Editor: run `supabase/migrations/0001_init.sql`, then `0002_ingestion.sql`.
2. Storage: create a private bucket named `documents`.
3. Copy the project URL, the `anon` key and the `service_role` key (secret).
4. Load the demo data from your machine (needs `.env` filled in):
   ```bash
   cd services/api && uv run python -m jobs.load_demo
   ```
   This stores companies, the 18-stock portfolio, the PDFs in `data/demo/` and the committed
   snapshot (filings and the precomputed promise ledgers). Large PDFs (> 5 MB) are not in git; put
   them in `data/demo/results/` first, or skip them and the Results tab shows "No results parsed".

## 2. Render (the API)
Hugging Face made Docker Spaces a paid feature, so the API runs on Render's free web service. It
sleeps when idle; the cron workflow retries while it wakes (about a minute).
1. render.com → sign in with GitHub → **New → Blueprint** → pick the `finn` repo. Render reads
   `render.yaml` and proposes a free web service `finn-api`.
2. Enter the secrets when asked (paste the values from your `.env`): `SUPABASE_URL`,
   `SUPABASE_SERVICE_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY` (several keys may be comma-separated),
   `JOB_SECRET`. Leave `CORS_ORIGINS` for now and set it after Vercel.
3. Deploy. The first Docker build takes a few minutes.
4. Open `https://finn-api.onrender.com/health` (the exact URL is on the service page). It should
   say `"status":"ok"` and `"db_configured":true`.

## 3. Vercel (the web app)
1. Import the GitHub repo. **Root Directory:** `apps/web`. Framework: Next.js.
2. Environment variables: `NEXT_PUBLIC_API_URL` = the Render URL (no trailing slash).
3. Deploy. Then set `CORS_ORIGINS` on the Render service to your Vercel URL (comma-separated if more than one) and let it redeploy.
4. On a phone: open the Vercel URL, then "Add to Home Screen" (it is a PWA).

## 4. Cron (GitHub Actions)
Repo → Settings → Secrets and variables → Actions: secrets `API_URL` (the Render URL) and
`JOB_SECRET` (same value as on Render). The `cron` workflow then calls
`POST /jobs/fetch-filings` every 30 minutes on market days and `POST /jobs/eod` at 16:30 IST. The
service sleeps when idle, so the workflow retries while it wakes. Run it once by hand with
**Run workflow** to check.

## Checks
- `GET /health` → ok, `db_configured: true`.
- `curl -X POST $API_URL/jobs/eod -H "x-job-secret: $JOB_SECRET"` → `{"status":"done",...}`.
- Web: Today lists filings; Companies → TCS → Results shows figures with a source link.
