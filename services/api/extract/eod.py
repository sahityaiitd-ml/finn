"""End-of-day prices via one batched yfinance call (.NS first, .BO fallback)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Bar:
    symbol: str
    d: date
    close: float
    volume: int


def avg_volume_20d(volumes: list[int]) -> float | None:
    """Mean of the 20 sessions before the latest one. None if fewer than 20."""
    prior = volumes[:-1][-20:]
    return sum(prior) / 20 if len(prior) == 20 else None


def bars_from_frame(frame, symbols: list[str], suffix: str) -> dict[str, list[Bar]]:
    """Turn a yfinance multi-ticker frame (group_by='ticker') into bars per symbol."""
    out: dict[str, list[Bar]] = {}
    for s in symbols:
        key = f"{s}{suffix}"
        if key not in frame.columns.get_level_values(0):
            continue
        sub = frame[key].dropna(subset=["Close"])
        out[s] = [
            Bar(s, idx.date(), float(r["Close"]), int(r["Volume"])) for idx, r in sub.iterrows()
        ]
    return out


def fetch_bars(symbols: list[str], period: str = "3mo") -> dict[str, list[Bar]]:
    import yfinance as yf

    def pull(suffix: str, syms: list[str]):
        tickers = [f"{s}{suffix}" for s in syms]
        frame = yf.download(
            tickers, period=period, group_by="ticker", auto_adjust=False, progress=False
        )
        return bars_from_frame(frame, syms, suffix)

    got = pull(".NS", symbols)
    missing = [s for s in symbols if not got.get(s)]
    if missing:
        got.update(pull(".BO", missing))
    return got


# ---------------- alerts ----------------
from datetime import datetime, time, timedelta, timezone  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))
CLOSE = time(15, 30)  # NSE/BSE close, IST
NO_FILING = "No related filing found"
FILING_FOUND = "Related filing found, cause unconfirmed"
DEFAULT_VOL_MULT = 2.0
DEFAULT_PRICE_PCT = 5.0


def evaluate(
    symbol: str, bars: list[Bar], vol_mult: float, price_pct: float, at: int = -1
) -> dict | None:
    """Did `bars[at]` breach a rule? A threshold of 0 means that rule is off.

    Volume: today's volume above `vol_mult` x the average of the 20 sessions before it.
    Price: close-to-close move beyond +/- `price_pct` percent. Needs 20 prior sessions.
    """
    i = at if at >= 0 else len(bars) + at
    if i < 21 - 1 or i >= len(bars):
        return None
    cur, prev = bars[i], bars[i - 1]
    avg = avg_volume_20d([b.volume for b in bars[: i + 1]])
    if avg is None or avg <= 0 or prev.close <= 0:
        return None
    ratio = cur.volume / avg
    pct = (cur.close / prev.close - 1) * 100
    triggered = []
    if vol_mult > 0 and ratio > vol_mult:
        triggered.append("volume")
    if price_pct > 0 and abs(pct) > price_pct:
        triggered.append("price")
    if not triggered:
        return None
    return {
        "symbol": symbol,
        "d": cur.d.isoformat(),
        "triggered": triggered,
        "volume": cur.volume,
        "avg_volume_20d": round(avg),
        "ratio": round(ratio, 2),
        "close": cur.close,
        "prev_close": prev.close,
        "pct": round(pct, 2),
        "vol_mult": vol_mult,
        "price_pct": price_pct,
    }


def window_for(d: date, prev_d: date) -> tuple[datetime, datetime]:
    """Filings that could explain day d's move: after the previous close, up to this close."""
    return (
        datetime.combine(prev_d, CLOSE, IST),
        datetime.combine(d, CLOSE, IST),
    )


def cause_label(d: date, prev_d: date, filings: list[dict]) -> tuple[str, list[dict]]:
    """One of exactly two labels. Never a guess at the cause.

    A filing is 'related' when it is for this stock, published in the window, and not routine
    (floored or materiality >= 30). Routine paperwork cannot be offered as a cause.
    """
    start, end = window_for(d, prev_d)
    found = []
    for f in filings:
        ts = datetime.fromisoformat(f["published_at"])
        if not (start <= ts <= end):
            continue
        if f.get("never_collapse") or (f.get("materiality") or 0) >= 30:
            found.append(f)
    return (FILING_FOUND if found else NO_FILING), found


def dry_run(
    bars_by_symbol: dict[str, list[Bar]],
    filings_by_symbol: dict[str, list[dict]],
    rules: dict[str, tuple[float, float]],
    sessions: int = 21,
) -> dict:
    """Replay the last `sessions` sessions: how many alerts would fire, how many had a filing."""
    total = with_filing = 0
    for sym, bars in bars_by_symbol.items():
        vm, pp = rules.get(sym, (DEFAULT_VOL_MULT, DEFAULT_PRICE_PCT))
        for i in range(max(20, len(bars) - sessions), len(bars)):
            a = evaluate(sym, bars, vm, pp, at=i)
            if a is None:
                continue
            total += 1
            label, _ = cause_label(bars[i].d, bars[i - 1].d, filings_by_symbol.get(sym, []))
            with_filing += label == FILING_FOUND
    return {"alerts": total, "with_filing": with_filing, "sessions": sessions}
