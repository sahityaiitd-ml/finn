# 0001 — Stack
**Status:** accepted. Next.js PWA on Vercel; FastAPI on a Hugging Face Space; Supabase; GitHub Actions cron. All free tiers. The Space sleeps, so scheduling lives outside it and calls `POST /jobs/*` with a shared secret.

**Amendment (2026-11-15).** Hugging Face made Docker Spaces a paid feature, so the API runs on Render's free web service instead (`render.yaml`). The design is unchanged: the service sleeps when idle, so scheduling stays outside it (GitHub Actions) and the cron retries while it wakes.
