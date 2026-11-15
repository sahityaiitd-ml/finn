# CLAUDE.md — FINN

## Product rules (never break)
- Evidence, not verdicts. No credibility score, no buy/sell language.
- Every number and quote links to its source document + page.
- The model extracts; Python computes arithmetic and sets every status.
- Vague guidance is marked "Vague" and never scored.
- Alert cause label is only "No related filing found" or "Related filing found, cause unconfirmed".
- Never collapse: results, board outcomes, M&A, auditor/KMP change, credit rating, pledge, litigation, fund-raise.
- Pull research uses only annual reports and transcripts. No news, no outside knowledge.
- Price moves are never coloured. Colour = severity only.

## Stack
- `apps/web`: Next.js App Router, TypeScript strict, Tailwind; tokens in `styles/tokens.css`.
- `services/api`: FastAPI, Python 3.11, uv, ruff, pytest; Docker for HF Spaces.
- Supabase Postgres + Storage; GitHub Actions cron.
- Models: rules first → Groq 8B (classify/summarise) → Groq 70B (guidance) → Gemini Flash (vision, odd mappings).
- Cache every model call by sha256(model + prompt_version + input).

## Commands
- Web: `cd apps/web && pnpm dev` · `pnpm lint` · `pnpm test`
- API: `cd services/api && uv run fastapi dev app/main.py` · `uv run ruff check .` · `uv run pytest`

## Git
- Branch per milestone: `feat/m<n>-<slug>`. Conventional Commits. Squash-merge PRs.
- Never commit `.env`, PDFs over 5 MB, or API keys.
- After each milestone, append to `docs/build-log.md`: date, what changed, key decisions, notable prompts.

## Design
- Figma `jXb5rzeDSJaDvsqMi1KApc`, page "v3 · Calm ledger".
- Inter only, tabular numerals. Cards 16 px radius, no border. Pill buttons at least 44 px. Proof links 13/500 sage-text.
- Mobile first at 390 px; two-column layout at 1024 px and wider.
