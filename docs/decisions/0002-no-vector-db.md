# 0002 — No vector DB
**Status:** accepted. Transcript retrieval uses Postgres full-text search over page rows. Pages are the citation unit, so page-level FTS keeps provenance exact and avoids another service.
