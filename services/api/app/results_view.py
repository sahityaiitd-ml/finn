"""Shape a stored result for the app. All arithmetic (changes, status) happens here, in Python."""

from __future__ import annotations

from extract.results import change_pct

CARD = [("revenue", "Revenue"), ("ebitda", "EBITDA"), ("pbt", "PBT"), ("pat", "PAT")]


def _values(parsed: dict, key: str) -> tuple[list[float | None], dict | None]:
    if key == "ebitda":
        # derived, so it cites the profit-before-tax line it was built from
        return parsed.get("derived", {}).get("ebitda", [None] * 3), parsed["metrics"].get("pbt")
    m = parsed["metrics"].get(key)
    return (m["values"] if m else [None] * 3), m


def build_view(symbol: str, name: str, period: str, sha: str, row: dict) -> dict:
    parsed = row["parsed"] or {}
    status = row["status"]
    view = {
        "symbol": symbol,
        "name": name,
        "period": period,
        "status": status,
        "basis": row.get("basis"),
        "flags": row.get("flags") or [],
        "reason": parsed.get("reason", ""),
        "source": {"sha256": sha, "page": parsed.get("page")},
        "unit": "₹ crore",
        "rows": [],
        "exceptional": None,
    }
    if status != "ok":
        if status == "unsupported":
            view["message"] = "Format not supported"
        else:
            view["message"] = "See PDF"
        return view

    ok = parsed["column_ok"]
    for key, label in CARD:
        vals, src = _values(parsed, key)
        cur = vals[0] if ok[0] else None
        prev = vals[1] if ok[1] else None
        yago = vals[2] if ok[2] else None
        view["rows"].append(
            {
                "key": key,
                "label": label,
                "value": cur,
                "qoq_pct": change_pct(cur, prev),
                "yoy_pct": change_pct(cur, yago),
                "qoq_available": ok[1],
                "yoy_available": ok[2],
                "derived": key == "ebitda",
                "page": src["page"] if src else None,
                "line": src["line"] if src else None,
            }
        )
    exc = parsed.get("derived", {}).get("exceptional", [0, 0, 0])
    view["exceptional"] = {"value": exc[0], "page": parsed.get("page")} if exc[0] != 0 else None
    return view
