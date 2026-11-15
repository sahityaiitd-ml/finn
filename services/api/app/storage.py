"""Store PDFs by SHA-256 in Supabase Storage and page text in doc_pages. Idempotent."""

from __future__ import annotations

from pathlib import Path

from supabase import Client

from extract.pdfs import extract_pages, sha256_file

BUCKET = "documents"


def ingest_pdf(
    db: Client,
    path: Path,
    *,
    symbol: str,
    kind: str,
    period: str | None = None,
    source_url: str | None = None,
) -> tuple[str, bool]:
    """Returns (sha256, created). Skips work if the hash is already stored."""
    sha = sha256_file(path)
    existing = db.table("documents").select("sha256").eq("sha256", sha).execute().data
    if existing:
        return sha, False
    storage_path = f"{sha}.pdf"
    db.storage.from_(BUCKET).upload(
        storage_path,
        path.read_bytes(),
        {"content-type": "application/pdf", "upsert": "true"},
    )
    pages = extract_pages(path)
    db.table("documents").insert(
        {
            "sha256": sha,
            "symbol": symbol,
            "kind": kind,
            "period": period,
            "source_url": source_url,
            "storage_path": storage_path,
            "n_pages": len(pages),
        }
    ).execute()
    rows = [
        {"sha256": sha, "page": i + 1, "text": t.replace("\x00", "")} for i, t in enumerate(pages)
    ]
    for i in range(0, len(rows), 50):
        db.table("doc_pages").insert(rows[i : i + 50]).execute()
    return sha, True
