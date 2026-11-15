import secrets

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(title="FINN API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def require_job_secret(x_job_secret: str | None = Header(default=None)) -> None:
    if not x_job_secret or not secrets.compare_digest(x_job_secret, settings.job_secret):
        raise HTTPException(status_code=401, detail="invalid job secret")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "finn-api", "db_configured": bool(settings.supabase_url)}


@app.post("/jobs/fetch-filings", dependencies=[Depends(require_job_secret)])
def fetch_filings() -> dict:
    from app.db import get_client
    from jobs.fetch_filings import run

    return {"status": "done", "job": "fetch-filings", **run(get_client())}


@app.post("/jobs/eod", dependencies=[Depends(require_job_secret)])
def eod() -> dict:
    return {"status": "queued", "job": "eod", "note": "implemented in M5"}


@app.get("/results/{symbol}/latest")
def latest_results(symbol: str) -> dict:
    from app.db import get_client
    from app.results_view import build_view

    db = get_client()
    sym = symbol.upper()
    rows = (
        db.table("results").select("*").eq("symbol", sym).order("period", desc=True).limit(1)
        .execute().data
    )  # fmt: skip
    if not rows:
        raise HTTPException(status_code=404, detail="no results parsed for this symbol")
    comp = db.table("companies").select("name").eq("symbol", sym).execute().data
    row = rows[0]
    return build_view(sym, comp[0]["name"] if comp else sym, row["period"], row["doc_sha256"], row)


@app.get("/docs/{sha256}/page/{n}")
def doc_page(sha256: str, n: int) -> dict:
    from app.db import get_client

    db = get_client()
    doc = db.table("documents").select("*").eq("sha256", sha256).execute().data
    page = db.table("doc_pages").select("text").eq("sha256", sha256).eq("page", n).execute().data
    if not doc or not page:
        raise HTTPException(status_code=404, detail="page not found")
    d = doc[0]
    return {
        "sha256": sha256,
        "page": n,
        "n_pages": d["n_pages"],
        "symbol": d["symbol"],
        "kind": d["kind"],
        "period": d["period"],
        "text": page[0]["text"],
    }


@app.post("/jobs/parse-results", dependencies=[Depends(require_job_secret)])
def parse_results_job() -> dict:
    from app.db import get_client
    from jobs.parse_results import run

    return {"status": "done", **run(get_client())}
