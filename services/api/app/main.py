import secrets

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(title="FINN API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
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

    db = get_client()
    fetched = run(db)
    from jobs.classify_filings import run as classify

    return {"status": "done", "job": "fetch-filings", **fetched, "classified": classify(db)}


@app.post("/jobs/eod", dependencies=[Depends(require_job_secret)])
def eod() -> dict:
    from app.db import get_client
    from jobs.eod import run

    return {"status": "done", "job": "eod", **run(get_client())}


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
    from app.alerts_view import alert_item

    alerts = db.table("alerts").select("*").in_("symbol", syms).execute().data
    fids = [i for a in alerts for i in a["detail"].get("filing_ids", [])]
    fmap: dict[str, dict] = {}
    if fids:
        for f in db.table("filings").select("id,headline,url").in_("id", fids).execute().data:
            fmap[f["id"]] = f
    extra = [alert_item(a, names, fmap) for a in alerts]
    return {"portfolio_id": pid, **build_digest(rows, names, now, window, extra)}


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


# ---------------- alerts + settings ----------------
@app.post("/alerts/{alert_id}/reviewed")
def alert_reviewed(alert_id: str, reviewed: bool = True) -> dict:
    from app.db import get_client

    db = get_client()
    rows = db.table("alerts").select("detail").eq("id", alert_id).execute().data
    if not rows:
        raise HTTPException(status_code=404, detail="alert not found")
    detail = {**rows[0]["detail"], "reviewed": reviewed}
    db.table("alerts").update({"detail": detail}).eq("id", alert_id).execute()
    return {"id": alert_id, "reviewed": reviewed}


def _settings_payload(db) -> dict:
    from extract.eod import DEFAULT_PRICE_PCT, DEFAULT_VOL_MULT
    from jobs.eod import default_portfolio

    pf = default_portfolio(db)
    held = db.table("portfolio_holdings").select("*").eq("portfolio_id", pf["id"]).execute().data
    comps = {c["symbol"]: c for c in db.table("companies").select("symbol,name,grp").execute().data}
    vm = pf["vol_mult"] if pf.get("vol_mult") is not None else DEFAULT_VOL_MULT
    pp = pf["price_pct"] if pf.get("price_pct") is not None else DEFAULT_PRICE_PCT
    overrides = [
        {
            "symbol": h["symbol"], "name": comps.get(h["symbol"], {}).get("name", h["symbol"]),
            "vol_mult": h["vol_mult"], "price_pct": h["price_pct"],
        }
        for h in held
        if h.get("vol_mult") is not None or h.get("price_pct") is not None
    ]  # fmt: skip
    return {
        "portfolio_id": pf["id"],
        "window_hours": pf["window_hours"],
        "vol_mult": float(vm),
        "price_pct": float(pp),
        "overrides": overrides,
        "holdings": len(held),
        "holdings_list": sorted(
            (
                {"symbol": h["symbol"], "name": comps.get(h["symbol"], {}).get("name", h["symbol"])}
                for h in held
            ),
            key=lambda x: x["name"],
        ),
        "research": sum(1 for c in comps.values() if c.get("grp") == "research"),
    }


@app.get("/settings")
def get_settings() -> dict:
    from app.db import get_client

    return _settings_payload(get_client())


@app.put("/settings")
def put_settings(body: dict) -> dict:
    """Update the default: window_hours (24/72/168), vol_mult, price_pct (0 turns a rule off)."""
    from app.db import get_client
    from jobs.eod import default_portfolio

    db = get_client()
    upd: dict = {}
    if "window_hours" in body:
        if body["window_hours"] not in (24, 72, 168):
            raise HTTPException(status_code=422, detail="window_hours must be 24, 72 or 168")
        upd["window_hours"] = body["window_hours"]
    for k, hi in (("vol_mult", 20), ("price_pct", 50)):
        if k in body:
            v = float(body[k])
            if not 0 <= v <= hi:
                raise HTTPException(status_code=422, detail=f"{k} must be between 0 and {hi}")
            upd[k] = v
    if upd:
        db.table("portfolios").update(upd).eq("id", default_portfolio(db)["id"]).execute()
    return _settings_payload(db)


@app.put("/settings/overrides/{symbol}")
def put_override(symbol: str, body: dict) -> dict:
    """Set a per-stock override. Omitted/null keeps the default for that rule; 0 turns it off."""
    from app.db import get_client
    from jobs.eod import default_portfolio

    db = get_client()
    pid = default_portfolio(db)["id"]
    sym = symbol.upper()
    upd = {k: (None if body.get(k) is None else float(body[k])) for k in ("vol_mult", "price_pct")}
    res = (
        db.table("portfolio_holdings")
        .update(upd)
        .eq("portfolio_id", pid)
        .eq("symbol", sym)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="not a holding")
    return _settings_payload(db)


@app.delete("/settings/overrides/{symbol}")
def delete_override(symbol: str) -> dict:
    return put_override(symbol, {"vol_mult": None, "price_pct": None})


@app.get("/settings/dry-run")
def dry_run_endpoint(vol_mult: float = 2.0, price_pct: float = 5.0) -> dict:
    """Replay the last ~30 days of stored prices at these settings (overrides still apply)."""
    from app.db import get_client
    from extract.eod import dry_run
    from jobs.eod import default_portfolio, load_bars, rules

    db = get_client()
    pf = {**default_portfolio(db), "vol_mult": vol_mult, "price_pct": price_pct}
    per = rules(db, pf)
    bars = load_bars(db, sorted(per))
    fl: dict[str, list[dict]] = {}
    q = db.table("filings").select("symbol,published_at,materiality,never_collapse")
    for f in q.in_("symbol", sorted(per)).execute().data:
        fl.setdefault(f["symbol"], []).append(f)
    return dry_run(bars, fl, per)
