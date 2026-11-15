"""Shape a stored result for the app. All arithmetic (changes, status) happens here, in Python."""

from __future__ import annotations

from extract.results import change_pct


def fmt_cr(x: float) -> str:
    """Indian digit grouping, no decimals for large values: 123456 -> '1,23,456'."""
    neg, n = x < 0, abs(x)
    s = f"{n:.0f}" if n >= 100 else f"{n:.1f}".rstrip("0").rstrip(".")
    whole, _, frac = s.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join([*parts, tail])
    return ("-" if neg else "") + whole + ("." + frac if frac else "")


def flag_notes(parsed: dict, flags: list[str]) -> list[dict]:
    """Plain-language notes for each flag. Numbers come from parsed lines, so they cite a page."""
    notes: list[dict] = []
    m = parsed.get("metrics", {})
    oi, pbt = m.get("other_income"), m.get("pbt")
    for f in flags:
        if f == "other_income_gt_20pct_pbt" and oi and pbt and pbt["values"][0]:
            a, b = oi["values"][0], pbt["values"][0]
            prev = oi["values"][1]
            txt = f"Other income ₹{fmt_cr(a)} Cr is {a / b * 100:.0f}% of PBT"
            txt += f" (previous quarter: ₹{fmt_cr(prev)} Cr)." if parsed["column_ok"][1] else "."
            notes.append({"flag": f, "text": txt, "page": oi["page"]})
        elif f == "exceptional_item":
            e = parsed["derived"]["exceptional"][0]
            kind = "gain" if e > 0 else "charge"
            notes.append(
                {
                    "flag": f,
                    "text": f"Exceptional {kind}: ₹{fmt_cr(abs(e))} Cr, shown separately.",
                    "page": pbt["page"] if pbt else None,
                }
            )
        elif f == "basis_switch":
            notes.append(
                {
                    "flag": f,
                    "text": "Reporting basis differs from the previous filing.",
                    "page": None,
                }
            )
        elif f == "restated_periods":
            notes.append(
                {"flag": f, "text": "Earlier periods were restated in this filing.", "page": None}
            )
        elif f == "standalone_only_consolidated_failed":
            notes.append(
                {
                    "flag": f,
                    "text": "Consolidated figures could not be verified; showing standalone.",
                    "page": None,
                }
            )
    return notes


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
    rev = next(r for r in view["rows"] if r["key"] == "revenue")
    eb = parsed["derived"]["ebitda"]
    rv = _values(parsed, "revenue")[0]
    margins = [
        (eb[c] / rv[c] * 100) if (ok[c] and eb[c] is not None and rv[c]) else None for c in range(3)
    ]
    bp = lambda a, b: None if a is None or b is None else round((a - b) * 100)  # noqa: E731
    view["rows"].insert(
        2,
        {
            "key": "margin", "label": "Margin",
            "value": None if margins[0] is None else round(margins[0], 1),
            "qoq_bp": bp(margins[0], margins[1]), "yoy_bp": bp(margins[0], margins[2]),
            "qoq_pct": None, "yoy_pct": None,
            "qoq_available": ok[1], "yoy_available": ok[2], "derived": True,
            "page": rev["page"], "line": None, "unit": "%",
        },
    )  # fmt: skip
    view["notes"] = flag_notes(parsed, view["flags"])
    exc = parsed.get("derived", {}).get("exceptional", [0, 0, 0])
    view["exceptional"] = {"value": exc[0], "page": parsed.get("page")} if exc[0] != 0 else None
    return view
