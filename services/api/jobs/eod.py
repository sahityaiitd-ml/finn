"""End-of-day job: one batched yfinance call after the close, then alerts.

Defaults: volume above 2x the 20-day average, price beyond +/-5%, overridable per stock.
A threshold of 0 switches that rule off. Cause labels are one of two fixed strings.
"""

from __future__ import annotations

from collections.abc import Callable

from supabase import Client

from extract.eod import (
    DEFAULT_PRICE_PCT,
    DEFAULT_VOL_MULT,
    Bar,
    cause_label,
    evaluate,
    fetch_bars,
)


def default_portfolio(db: Client) -> dict:
    rows = db.table("portfolios").select("*").order("created_at").limit(1).execute().data
    if not rows:
        raise RuntimeError("no portfolio")
    return rows[0]


def rules(db: Client, portfolio: dict) -> dict[str, tuple[float, float]]:
    """Per-stock (volume multiple, price percent). Null override = portfolio default."""
    vm = float(
        portfolio.get("vol_mult") if portfolio.get("vol_mult") is not None else DEFAULT_VOL_MULT
    )
    pp = float(
        portfolio.get("price_pct") if portfolio.get("price_pct") is not None else DEFAULT_PRICE_PCT
    )
    out: dict[str, tuple[float, float]] = {}
    held = db.table("portfolio_holdings").select("*").eq("portfolio_id", portfolio["id"]).execute()
    for h in held.data:
        out[h["symbol"]] = (
            float(h["vol_mult"]) if h.get("vol_mult") is not None else vm,
            float(h["price_pct"]) if h.get("price_pct") is not None else pp,
        )
    return out


def load_bars(db: Client, symbols: list[str]) -> dict[str, list[Bar]]:
    """Stored prices per symbol, oldest first. Pages through results: the API caps a request."""
    from datetime import date

    out: dict[str, list[Bar]] = {}
    start, page = 0, 1000
    while True:
        rows = (
            db.table("prices").select("*").in_("symbol", symbols).order("symbol").order("d")
            .range(start, start + page - 1).execute().data
        )  # fmt: skip
        for r in rows:
            out.setdefault(r["symbol"], []).append(
                Bar(r["symbol"], date.fromisoformat(r["d"]), float(r["close"]), int(r["volume"]))
            )
        if len(rows) < page:
            return out
        start += page


def run(db: Client, fetch: Callable[[list[str]], dict[str, list[Bar]]] = fetch_bars) -> dict:
    pf = default_portfolio(db)
    per_stock = rules(db, pf)
    symbols = sorted(per_stock)
    bars = fetch(symbols)

    # store prices (3 months): the dry run and later alerts read from here
    rows = [
        {"symbol": s, "d": b.d.isoformat(), "close": b.close, "volume": b.volume}
        for s, bs in bars.items()
        for b in bs
    ]
    for i in range(0, len(rows), 500):
        db.table("prices").upsert(rows[i : i + 500]).execute()

    created, missing = [], [s for s in symbols if not bars.get(s)]
    for s in symbols:
        bs = bars.get(s) or []
        vm, pp = per_stock[s]
        a = evaluate(s, bs, vm, pp)
        if a is None:
            continue
        from datetime import date

        d, prev = date.fromisoformat(a["d"]), bs[-2].d
        filings = (
            db.table("filings").select("id,headline,url,published_at,materiality,never_collapse")
            .eq("symbol", s).gte("published_at", f"{prev.isoformat()}T00:00:00+05:30")
            .lte("published_at", f"{d.isoformat()}T23:59:59+05:30").execute().data
        )  # fmt: skip
        label, related = cause_label(d, prev, filings)
        kind = "price" if "price" in a["triggered"] else "volume"
        old = (
            db.table("alerts").select("id,detail").eq("symbol", s).eq("d", a["d"]).eq("kind", kind)
        )
        old = old.execute().data
        detail = {
            **a,
            "filing_ids": [f["id"] for f in related],
            "reviewed": bool(old and old[0]["detail"].get("reviewed")),
        }
        db.table("alerts").upsert(
            {"symbol": s, "d": a["d"], "kind": kind, "detail": detail, "cause_label": label},
            on_conflict="symbol,d,kind",
        ).execute()
        created.append({"symbol": s, "kind": kind, "label": label})
    return {
        "symbols": len(symbols),
        "with_prices": len(symbols) - len(missing),
        "missing_prices": missing,
        "alerts": created,
    }
