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
    return {"status": "queued", "job": "fetch-filings", "note": "implemented in M1"}


@app.post("/jobs/eod", dependencies=[Depends(require_job_secret)])
def eod() -> dict:
    return {"status": "queued", "job": "eod", "note": "implemented in M5"}
