"""Periods, targets and status rules for promised-vs-delivered. Pure Python, no model.

Every status is set here. The model only extracted the quote and the words it contained.
Statuses: Delivered / Missed / Partly / Vague / Not yet due / No comparable actual.
There is no score of any kind.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

STATUSES = ["Delivered", "Missed", "Partly", "Vague", "Not yet due", "No comparable actual"]
RULES_VERSION = "status-v1"

# Tolerances in percentage points. Every guided metric here is higher-is-better, so beating a
# target is "Delivered". "Partly" means a miss within this band below the threshold.
PARTLY_PP = {"margin": 0.5, "growth": 2.0}
POINT_PP = {"margin": 0.5, "growth": 2.0}  # "around X" is met within this below X


# ---------- periods ----------
def add_months(end: str, n: int) -> str:
    y, m = map(int, end.split("-"))
    t = y * 12 + (m - 1) + n
    return f"{t // 12}-{t % 12 + 1:02d}"


def fiscal_year(end: str) -> int:
    y, m = map(int, end.split("-"))
    return y + 1 if m >= 4 else y


@dataclass(frozen=True)
class Period:
    kind: str  # Q | H | FY
    end: str  # YYYY-MM of the period end
    label: str

    @property
    def key(self) -> str:
        return f"{self.kind}:{self.end}"


def fy_end(fy: int) -> str:
    return f"{fy}-03"


def quarter_period(fy: int, q: int) -> Period:
    end = {1: f"{fy - 1}-06", 2: f"{fy - 1}-09", 3: f"{fy - 1}-12", 4: f"{fy}-03"}[q]
    return Period("Q", end, f"Q{q} FY{str(fy)[-2:]}")


def quarter_label(end: str) -> str:
    y, m = map(int, end.split("-"))
    fy = fiscal_year(end)
    q = {6: 1, 9: 2, 12: 3, 3: 4}.get(m)
    return f"Q{q} FY{str(fy)[-2:]}" if q else end


def _fy_num(s: str) -> int:
    n = int(s)
    return 2000 + n if n < 100 else n


_FY = r"fy\s*'?\s*(\d{2,4})|fiscal\s*(?:year\s*)?(\d{2,4})"


def resolve_period(text: str, call_quarter_end: str) -> Period | None:
    """Turn the words management used into a concrete period, or None if ambiguous.

    `call_quarter_end` is the quarter the call reported (e.g. '2026-06'); the call itself is
    held about a month later, so "this year" means the fiscal year in progress after that date.
    """
    t = " ".join(text.lower().split())
    if not t:
        return None
    in_progress = fiscal_year(add_months(call_quarter_end, 1))
    m = re.search(r"\bq([1-4])\s*(?:of\s*)?(?:" + _FY + r")", t)
    if m:
        fy = _fy_num(m.group(2) or m.group(3))
        return quarter_period(fy, int(m.group(1)))
    m = re.search(r"\b(?:h([12])|(first|second)\s+half)\s*(?:of\s*)?(?:" + _FY + r")?", t)
    if m:
        half = int(m.group(1)) if m.group(1) else (1 if m.group(2) == "first" else 2)
        fy = _fy_num(m.group(3) or m.group(4)) if (m.group(3) or m.group(4)) else in_progress
        end = f"{fy - 1}-09" if half == 1 else f"{fy}-03"
        return Period("H", end, f"H{half} FY{str(fy)[-2:]}")
    m = re.search(_FY, t)
    if m:
        fy = _fy_num(m.group(1) or m.group(2))
        return Period("FY", fy_end(fy), f"FY{str(fy)[-2:]}")
    if re.search(r"next (?:fiscal )?year|following year", t):
        fy = in_progress + 1
        return Period("FY", fy_end(fy), f"FY{str(fy)[-2:]}")
    if re.search(r"full[- ]year|this (?:fiscal )?year|current (?:fiscal )?year|for the year", t):
        return Period("FY", fy_end(in_progress), f"FY{str(in_progress)[-2:]}")
    if re.search(r"next quarter|coming quarter|following quarter", t):
        end = add_months(call_quarter_end, 3)
        return Period("Q", end, quarter_label(end))
    return None  # "going forward", "next few quarters", "this quarter" are not a period


# ---------- actuals from parsed results ----------
def column_periods(doc_period: str, n: int) -> list[str | None]:
    """Period keys of each results column, by the SEBI Schedule III layout for that quarter."""
    m = int(doc_period.split("-")[1])
    q = f"Q:{doc_period}"
    base = [q, f"Q:{add_months(doc_period, -3)}", f"Q:{add_months(doc_period, -12)}"]
    if m == 6:
        extra = [f"FY:{add_months(doc_period, -3)}"]
    elif m == 9:
        extra = [
            f"H:{doc_period}",
            f"H:{add_months(doc_period, -12)}",
            f"FY:{add_months(doc_period, -6)}",
        ]
    elif m == 12:
        extra = [
            f"N:{doc_period}",
            f"N:{add_months(doc_period, -12)}",
            f"FY:{add_months(doc_period, -9)}",
        ]
    elif m == 3:
        extra = [f"FY:{doc_period}", f"FY:{add_months(doc_period, -12)}"]
    else:
        extra = []
    return (base + extra + [None] * 6)[:n]


def build_actuals(results_rows: list[dict]) -> dict[str, dict]:
    """Merge parsed results into {period key: {revenue, ebitda, ebit, pbt, pat, source}}.

    Only columns that passed every identity check are used. If two filings cover the same
    period, the later filing wins (it may be a restatement).
    """
    out: dict[str, dict] = {}
    for row in sorted(results_rows, key=lambda r: r["period"]):
        p = row.get("parsed") or {}
        if p.get("status") != "ok":
            continue
        ok = p["column_ok"]
        keys = column_periods(row["period"], len(ok))
        for c, key in enumerate(keys):
            if key is None or not ok[c]:
                continue
            m, d = p["metrics"], p["derived"]
            val = {
                "revenue": m["revenue"]["values"][c],
                "pbt": m["pbt"]["values"][c],
                "pat": m["pat"]["values"][c],
                "ebitda": d["ebitda"][c],
                "ebit": d["ebit"][c],
            }
            out[key] = {
                **val,
                "sha256": row["doc_sha256"],
                "page": m["revenue"]["page"],
                "line": m["revenue"]["line"],
                "basis": p["basis"],
            }
    return out


def horizon_end(results_rows: list[dict]) -> str | None:
    ok = [r["period"] for r in results_rows if (r.get("parsed") or {}).get("status") == "ok"]
    return max(ok) if ok else None


def lookup_actual(
    metric: str, basis: str, qualifier: str, period: Period, actuals: dict[str, dict]
) -> tuple[float, str, dict] | None:
    """Return (value in %, human text, source) for a comparable actual, or None."""
    if qualifier != "none":
        return None  # constant currency / organic / segment: not what the results PDF reports
    cur = actuals.get(period.key)
    if cur is None:
        return None
    if metric in ("ebitda_margin", "ebit_margin"):
        if basis not in ("level", "unspecified"):
            return None
        k = "ebitda" if metric == "ebitda_margin" else "ebit"
        if cur[k] is None or not cur["revenue"]:
            return None
        v = cur[k] / cur["revenue"] * 100
        return v, f"{v:.1f}%", cur
    growth_key = {"revenue_growth": "revenue", "ebitda_growth": "ebitda", "pat_growth": "pat",
                  "pbt_growth": "pbt"}.get(metric)  # fmt: skip
    if growth_key is None:
        return None
    if basis in ("yoy", "unspecified"):
        prior_key = f"{period.kind}:{add_months(period.end, -12)}"
        label = "YoY"
    elif basis == "qoq" and period.kind == "Q":
        prior_key = f"Q:{add_months(period.end, -3)}"
        label = "QoQ"
    else:
        return None
    prior = actuals.get(prior_key)
    if prior is None or not prior[growth_key] or prior[growth_key] <= 0 or cur[growth_key] is None:
        return None
    v = (cur[growth_key] / prior[growth_key] - 1) * 100
    return v, f"{v:+.1f}% {label}", cur


# ---------- comparing ----------
def compare(actual: float, direction: str, low: float | None, high: float | None, kind: str) -> str:
    """Delivered / Partly / Missed for a higher-is-better percentage metric."""
    partly = PARTLY_PP[kind]
    if direction == "range" and low is not None:
        threshold = low
    elif direction == "point" and low is not None:
        threshold = low - POINT_PP[kind]
    elif direction == "min" and low is not None:
        threshold = low
    elif direction == "max" and high is not None:
        return "Delivered" if actual <= high else "Partly" if actual <= high + partly else "Missed"
    else:
        raise ValueError("no comparable target")
    if actual >= threshold:
        return "Delivered"
    return "Partly" if actual >= threshold - partly else "Missed"


def target_text(direction: str, low: float | None, high: float | None, unit: str) -> str:
    u = "%" if unit == "percent" else ""
    if direction == "range" and low is not None and high is not None and low != high:
        return f"{low:g}–{high:g}{u}"
    if direction == "min" and low is not None:
        return f"{low:g}{u} or more"
    if direction == "max" and high is not None:
        return f"up to {high:g}{u}"
    if low is not None:
        return f"around {low:g}{u}"
    return ""


def decide_status(
    item: dict,
    call_quarter_end: str,
    actuals: dict[str, dict],
    horizon: str | None,
) -> tuple[str, dict]:
    """The one place a promise gets its status. Returns (status, detail)."""
    detail: dict = {
        "target": target_text(item["direction"], item["low"], item["high"], item["unit"])
    }
    if item["direction"] == "none" or (item["low"] is None and item["high"] is None):
        return "Vague", {**detail, "reason": "no number given, so it is never scored"}
    period = resolve_period(item["period"], call_quarter_end)
    if period is None:
        return "No comparable actual", {**detail, "reason": "the period is not specific"}
    detail["period"] = period.label
    if horizon is None or period.end > horizon:
        return "Not yet due", {**detail, "reason": f"{period.label} has not been reported yet"}
    if item["unit"] != "percent":
        return "No comparable actual", {**detail, "reason": "not a percentage metric"}
    found = lookup_actual(item["metric"], item["basis"], item["qualifier"], period, actuals)
    if found is None:
        return "No comparable actual", {**detail, "reason": "no matching figure in the results"}
    value, text, src = found
    kind = "margin" if item["metric"].endswith("margin") else "growth"
    status = compare(value, item["direction"], item["low"], item["high"], kind)
    return status, {
        **detail,
        "reported": text,
        "reported_value": round(value, 2),
        "source": {"sha256": src["sha256"], "page": src["page"], "line": src["line"]},
    }
