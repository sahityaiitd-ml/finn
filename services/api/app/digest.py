"""Build the ranked digest from stored filings. Pure functions: no network, easy to test."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from rules.materiality import is_routine

WINDOWS = {"24h": 24, "3d": 72, "7d": 168, "30d": 720}
_PREFIX = re.compile(r"^announcement under regulation 30 \(lodr\)\s*-\s*", re.I)
_TRAIL_DATE = re.compile(r"\s+\d{1,2} (jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*$", re.I)


def display_headline(h: str) -> str:
    h = _PREFIX.sub("", h.strip())
    return _TRAIL_DATE.sub("", h)


def build_digest(
    rows: list[dict],
    names: dict[str, str],
    now: datetime,
    window: str,
    extra: list[dict] | None = None,
) -> dict:
    hours = WINDOWS.get(window, 24)
    since = now - timedelta(hours=hours)
    main: list[dict] = []
    routine: list[dict] = []
    for r in rows:
        ts = datetime.fromisoformat(r["published_at"])
        if ts < since or ts > now:
            continue
        item = {
            "id": r["id"],
            "symbol": r["symbol"],
            "name": names.get(r["symbol"], r["symbol"]),
            "category": r["category"],
            "headline": display_headline(r["headline"]),
            "summary": r.get("summary"),
            "published_at": r["published_at"],
            "source_url": r.get("url"),
            "never_collapse": bool(r.get("never_collapse")),
            "materiality": r.get("materiality") or 0,
            "reviewed": bool(r.get("reviewed")),
        }
        score = item["materiality"]
        # unclassified yet (no category) is never hidden
        if r["category"] is None or not is_routine(score, item["never_collapse"]):
            main.append(item)
        else:
            routine.append(item)
    main.sort(
        key=lambda i: (-i["materiality"], -datetime.fromisoformat(i["published_at"]).timestamp())
    )
    routine.sort(key=lambda i: -datetime.fromisoformat(i["published_at"]).timestamp())
    for it in extra or []:  # end-of-day alerts: always shown, never routine
        ts = datetime.fromisoformat(it["published_at"])
        if since <= ts <= now:
            main.append(it)
    main.sort(
        key=lambda i: (-i["materiality"], -datetime.fromisoformat(i["published_at"]).timestamp())
    )
    open_main = [i for i in main if not i["reviewed"]]
    return {
        "window": window if window in WINDOWS else "24h",
        "since": since.isoformat(),
        "generated_at": now.isoformat(),
        "main": main,
        "routine": routine,
        "counts": {"main": len(main), "routine": len(routine), "to_review": len(open_main)},
        "caught_up": len(open_main) == 0,
    }
