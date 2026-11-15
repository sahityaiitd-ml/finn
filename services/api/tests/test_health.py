from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_jobs_require_secret():
    assert client.post("/jobs/eod").status_code == 401
    assert client.post("/jobs/eod", headers={"x-job-secret": "wrong"}).status_code == 401


def test_jobs_accept_secret(monkeypatch):
    import app.db
    import jobs.fetch_filings

    monkeypatch.setattr(app.db, "get_client", lambda: object())
    import jobs.classify_filings
    import jobs.eod

    monkeypatch.setattr(jobs.eod, "run", lambda db: {"alerts": []})
    monkeypatch.setattr(jobs.fetch_filings, "run", lambda db: {"companies": 0})
    monkeypatch.setattr(jobs.classify_filings, "run", lambda db: {"classified": 0})
    h = {"x-job-secret": settings.job_secret}
    assert client.post("/jobs/eod", headers=h).status_code == 200
    assert client.post("/jobs/fetch-filings", headers=h).status_code == 200
