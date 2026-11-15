# 0003 — Model routing (checked 2026-11-15)
**Status:** accepted. Groq no longer lists Llama 8B/70B. Mapping, via `/openai/v1/models`:
- small tasks (leftover classification, ≤25-word summaries): `openai/gpt-oss-20b`
- guidance extraction: `openai/gpt-oss-120b`
- scanned pages and odd-metric mapping: Gemini `gemini-2.5-flash` with `response_schema`

Rules/regex still handle ~80% of classification and all results lines. All calls cached by `sha256(model + prompt_version + input)`.
