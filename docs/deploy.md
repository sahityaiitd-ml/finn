# Deploy

Everything runs on free tiers. Order matters: Supabase → Hugging Face Space → Vercel → GitHub secrets.

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

## 2. Hugging Face Space (the API)
1. New Space → SDK **Docker** → blank → CPU basic (free).
2. Settings → Variables and secrets, add secrets: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`,
   `GROQ_API_KEY`, `GEMINI_API_KEY` (and optionally `GEMINI_API_KEYS`), `JOB_SECRET`; and the
   variable `CORS_ORIGINS` = your Vercel URL (comma-separated if more than one).
3. Push the API. Either let the repo do it:
   - GitHub repo → Settings → Secrets and variables → Actions: secret `HF_TOKEN` (a *write* token),
     variable `HF_SPACE` = `your-name/finn-api`. Then run the **deploy-space** workflow.
   - or push by hand: copy `services/api` to a folder, `git init`, and push to
     `https://huggingface.co/spaces/your-name/finn-api`.
4. Open `https://your-name-finn-api.hf.space/health`. It should say `"status":"ok"` and
   `"db_configured":true`.

## 3. Vercel (the web app)
1. Import the GitHub repo. **Root Directory:** `apps/web`. Framework: Next.js.
2. Environment variables: `NEXT_PUBLIC_API_URL` = the Space URL (no trailing slash).
3. Deploy. Then put the Vercel URL in the Space's `CORS_ORIGINS` and restart the Space.
4. On a phone: open the Vercel URL, then "Add to Home Screen" (it is a PWA).

## 4. Cron (GitHub Actions)
Repo → Settings → Secrets and variables → Actions: secrets `API_URL` (the Space URL) and
`JOB_SECRET` (same value as in the Space). The `cron` workflow then calls
`POST /jobs/fetch-filings` every 30 minutes on market days and `POST /jobs/eod` at 16:30 IST. The
Space sleeps when idle, so the workflow retries while it wakes. Run it once by hand with
**Run workflow** to check.

## Checks
- `GET /health` → ok, `db_configured: true`.
- `curl -X POST $API_URL/jobs/eod -H "x-job-secret: $JOB_SECRET"` → `{"status":"done",...}`.
- Web: Today lists filings; Companies → TCS → Results shows figures with a source link.
