import secrets

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
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
def doc_page(sha256: str, n: int, q: str | None = None) -> dict:
    from app.db import get_client

    db = get_client()
    doc = db.table("documents").select("*").eq("sha256", sha256).execute().data
    page = db.table("doc_pages").select("text").eq("sha256", sha256).eq("page", n).execute().data
    if not doc or not page:
        raise HTTPException(status_code=404, detail="page not found")
    d = doc[0]
    hl = None
    if q:
        from extract.quotes import locate

        h = locate(q, page[0]["text"])
        hl = {"start": h.start, "end": h.end, "score": h.score} if h else None
    return {
        "highlight": hl,
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


def _run_promise_job(job_id: str, symbol: str) -> None:
    from datetime import UTC, datetime

    from app.db import get_client
    from jobs.promises import run

    db = get_client()
    db.table("jobs").update({"status": "running"}).eq("id", job_id).execute()
    try:

        def progress(p):
            db.table("jobs").update({"result": {"state": "running", "progress": p}}).eq(
                "id", job_id
            ).execute()

        result = run(db, symbol, on_progress=progress)
        status = "done"
        err = None
    except Exception as e:  # report, never crash the worker
        result, status, err = None, "failed", str(e)[:300]
    db.table("jobs").update(
        {
            "status": status,
            "result": result,
            "error": err,
            "updated_at": datetime.now(UTC).isoformat(),
        }
    ).eq("id", job_id).execute()


@app.post("/promises/{symbol}")
def start_promises(symbol: str, background: BackgroundTasks, refresh: bool = False) -> dict:
    """Start (or reuse) the ledger job. Same inputs + prompt version means a cached answer."""
    from app.db import get_client
    from jobs.promises import ledger_key, results_rows, transcript_docs

    db, sym = get_client(), symbol.upper()
    key = ledger_key(sym, transcript_docs(db, sym), results_rows(db, sym))
    jobs = db.table("jobs").select("*").eq("kind", "promises").eq("key", key).execute().data
    live = [j for j in jobs if j["status"] in ("queued", "running")]
    done = [j for j in jobs if j["status"] == "done" and (j["result"] or {}).get("state") == "done"]
    if live:
        return {"job_id": live[0]["id"], "status": live[0]["status"], "cached": False}
    if done and not refresh:
        return {"job_id": done[0]["id"], "status": "done", "cached": True}
    job = (
        db.table("jobs")
        .insert({"kind": "promises", "key": key, "status": "queued"})
        .execute()
        .data[0]
    )
    background.add_task(_run_promise_job, job["id"], sym)
    return {"job_id": job["id"], "status": "queued", "cached": False}


@app.get("/jobs/{job_id}")
def job_status(job_id: str) -> dict:
    from app.db import get_client

    rows = get_client().table("jobs").select("*").eq("id", job_id).execute().data
    if not rows:
        raise HTTPException(status_code=404, detail="job not found")
    j = rows[0]
    return {
        "id": j["id"],
        "kind": j["kind"],
        "status": j["status"],
        "result": j["result"],
        "error": j["error"],
    }


@app.get("/promises/{symbol}")
def get_promises(symbol: str) -> dict:
    from app.db import get_client
    from jobs.promises import ledger, results_rows

    db, sym = get_client(), symbol.upper()
    comp = db.table("companies").select("name").eq("symbol", sym).execute().data
    rows = ledger(db, sym)
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    from extract.promises import horizon_end
    from jobs.promises import transcript_docs

    calls = [{"period": d["period"], "pages": d["n_pages"]} for d in transcript_docs(db, sym)]
    return {
        "symbol": sym,
        "name": comp[0]["name"] if comp else sym,
        "calls": calls,
        "rows": rows,
        "counts": counts,
        "reported_through": horizon_end(results_rows(db, sym)),
    }
