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
