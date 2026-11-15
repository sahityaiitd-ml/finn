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


@app.get("/digest")
def digest(portfolio_id: str | None = None, window: str = "24h", as_of: str | None = None) -> dict:
    from datetime import UTC, datetime

    from app.db import get_client
    from app.digest import build_digest

    db = get_client()
    pid = portfolio_id
    if not pid:
        p = db.table("portfolios").select("id").order("created_at").limit(1).execute().data
        if not p:
            raise HTTPException(status_code=404, detail="no portfolio")
        pid = p[0]["id"]
    syms = [
        r["symbol"]
        for r in db.table("portfolio_holdings")
        .select("symbol")
        .eq("portfolio_id", pid)
        .execute()
        .data
    ]
    names = {
        c["symbol"]: c["name"]
        for c in db.table("companies").select("symbol,name").in_("symbol", syms).execute().data
    }
    now = datetime.fromisoformat(as_of) if as_of else datetime.now(UTC)
    rows = (
        db.table("filings")
        .select("*")
        .in_("symbol", syms)
        .gte("published_at", "2000-01-01")
        .execute()
        .data
    )
    return {"portfolio_id": pid, **build_digest(rows, names, now, window)}


@app.post("/filings/{filing_id}/reviewed")
def mark_reviewed(filing_id: str, reviewed: bool = True) -> dict:
    from app.db import get_client

    res = get_client().table("filings").update({"reviewed": reviewed}).eq("id", filing_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="filing not found")
    return {"id": filing_id, "reviewed": reviewed}


@app.post("/jobs/classify-filings", dependencies=[Depends(require_job_secret)])
def classify_filings_job() -> dict:
    from app.db import get_client
    from jobs.classify_filings import run

    return {"status": "done", **run(get_client())}
