from datetime import UTC, datetime

from app.alerts_view import alert_item
from app.digest import build_digest


def alert(reviewed=False):
    return {
        "id": "a1", "symbol": "TCS", "d": "2026-11-13", "cause_label": "No related filing found",
        "detail": {"triggered": ["volume", "price"], "ratio": 4.2, "vol_mult": 2.0, "pct": -6.1,
                   "price_pct": 5.0, "filing_ids": ["f1"], "reviewed": reviewed},
    }  # fmt: skip


def test_alert_item_is_never_routine_and_shows_the_two_numbers_plainly():
    it = alert_item(alert(), {"TCS": "TCS Ltd"}, {"f1": {"headline": "h", "url": "https://x"}})
    assert it["never_collapse"] and it["category"] == "eod_alert"
    assert it["alert"]["ratio"] == 4.2 and it["alert"]["pct"] == -6.1
    assert it["source_url"] == "https://x" and it["name"] == "TCS Ltd"
    assert "colour" not in str(it) and "color" not in str(it)  # a price move is never coloured


def test_alerts_join_the_digest_within_the_window_and_can_be_reviewed():
    now = datetime(2026, 11, 13, 20, 0, tzinfo=UTC)
    it = alert_item(alert(), {}, {})
    d = build_digest([], {}, now, "24h", [it])
    assert d["counts"]["main"] == 1 and d["counts"]["to_review"] == 1 and not d["caught_up"]
    done = alert_item(alert(reviewed=True), {}, {})
    assert build_digest([], {}, now, "24h", [done])["caught_up"] is True
    old = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
    assert build_digest([], {}, old, "24h", [it])["counts"]["main"] == 0


def test_the_digest_endpoint_includes_alerts():
    """Guards the wiring, not just the pure functions: /digest must merge stored alerts."""
    from fastapi.testclient import TestClient

    import app.db
    from app.main import app as fastapi_app

    class Q:
        def __init__(self, table):
            self.t = table

        def select(self, *_):
            return self

        def eq(self, *_):
            return self

        def in_(self, *_):
            return self

        def gte(self, *_):
            return self

        def order(self, *_):
            return self

        def limit(self, *_):
            return self

        def execute(self):
            data = {
                "portfolios": [{"id": "p"}],
                "portfolio_holdings": [{"symbol": "TCS"}],
                "companies": [{"symbol": "TCS", "name": "TCS Ltd"}],
                "filings": [],
                "alerts": [alert()],
            }[self.t]
            return type("R", (), {"data": data})

    class DB:
        def table(self, t):
            return Q(t)

    orig = app.db.get_client
    app.db.get_client = lambda: DB()
    try:
        r = TestClient(fastapi_app).get("/digest?window=24h&as_of=2026-11-13T20:00:00%2B00:00")
    finally:
        app.db.get_client = orig
    items = [i for i in r.json()["main"] if i["category"] == "eod_alert"]
    assert items and items[0]["name"] == "TCS Ltd" and items[0]["alert"]["ratio"] == 4.2
