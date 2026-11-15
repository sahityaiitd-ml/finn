# FINN

A mobile-first AI investor agent that filters filings, prices and results down to the few things that matter. Evidence, not verdicts.

Live demo: _TBD (M0 deploy)_

See [docs/PRD.md](docs/PRD.md), [docs/architecture.md](docs/architecture.md) and [docs/build-log.md](docs/build-log.md). The full README is completed in M6.

## Run locally
```bash
cp .env.example .env
cd services/api && uv run fastapi dev app/main.py
cd apps/web && pnpm install && pnpm dev
```
