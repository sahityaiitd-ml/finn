"""SEBI Schedule III results parser. Rules only: the model never touches these numbers.

Columns 0..2 of every line are: this quarter, preceding quarter, same quarter last year.
Every figure carries its page and source line. Identity checks gate every column; a
column that fails is shown as "see PDF", never guessed. Banks/NBFCs are unsupported.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

NUM = re.compile(r"^\(?-?\d[\d,]*(?:\.\d+)?\)?$")
DASH = {"-", "–", "—"}

LABELS: dict[str, re.Pattern] = {
    "total_revenue_ops": re.compile(r"\btotal revenue from operations\b", re.I),
    "revenue_ops": re.compile(r"^\W*(?:[ivx\d]+\W+)?revenue from operations\b", re.I),
    "other_income": re.compile(r"^\W*(?:[ivx\d]+\W+)?other income\b", re.I),
    "total_income": re.compile(r"\btotal income\b", re.I),
    "finance_cost": re.compile(r"\bfinance costs?\b", re.I),
    "dep": re.compile(r"\bdepreciation\b", re.I),
    "total_expenses": re.compile(r"\btotal expenses\b", re.I),
    "pbt_pre_exc": re.compile(r"\bprofit\W.{0,12}before exceptional items\b", re.I),
    "pbt": re.compile(r"\bprofit\W.{0,12}before tax\b", re.I),
    "total_tax": re.compile(r"\btotal tax expenses?\b", re.I),
    "current_tax": re.compile(r"^\W*current tax\b", re.I),
    "deferred_tax": re.compile(r"^\W*deferred tax\b", re.I),
    "pat": re.compile(
        r"\bprofit\b.{0,14}?(?:for the (?:period|year|quarter)|after tax)\b(?!.*attributable)", re.I
    ),
    "jv_share": re.compile(
        r"^\W*(?:[ivx\d]+\W+)?share of (?:profit|proflt).{0,20}(?:joint|ioint|associate)", re.I
    ),
}
BANK_HINT = re.compile(r"interest earned|net interest income|\binterest expended\b", re.I)


def parse_number(tok: str) -> float | None:
    if tok in DASH:
        return 0.0
    if not NUM.match(tok):
        return None
    neg = tok.startswith("(") or tok.startswith("-")
    v = float(tok.strip("()-").replace(",", ""))
    return -v if neg else v


def split_line(line: str, min_run: int = 3) -> tuple[str, list[float]]:
    """Split into (label, first numeric run of >= min_run tokens); trailing damage is ignored."""
    toks = line.split()
    n = len(toks)
    for i in range(n):
        if parse_number(toks[i]) is None:
            continue
        j = i
        vals: list[float] = []
        while j < n and (v := parse_number(toks[j])) is not None:
            vals.append(v)
            j += 1
        if len(vals) >= min_run:
            return " ".join(toks[:i]), vals
    return line.strip(), []


@dataclass
class Line:
    page: int
    text: str
    label: str
    values: list[float]
    values2: list[float] = field(default_factory=list)  # looser: runs of >= 2


@dataclass
class Metric:
    values: list[float | None]
    page: int
    line: str


@dataclass
class Check:
    name: str
    ok: list[bool]  # per column (this quarter, preceding, year-ago)
    detail: str = ""


@dataclass
class ParsedResults:
    status: str  # ok | see_pdf | unsupported
    basis: str | None = None
    page: int | None = None
    metrics: dict[str, Metric] = field(default_factory=dict)
    derived: dict[str, list[float | None]] = field(default_factory=dict)
    checks: list[Check] = field(default_factory=list)
    column_ok: list[bool] = field(default_factory=lambda: [False, False, False])
    flags: list[str] = field(default_factory=list)
    reason: str = ""


def _lines(pages: list[str], first: int) -> list[Line]:
    out: list[Line] = []
    for pno in (first, first + 1):
        if pno > len(pages):
            break
        for raw in pages[pno - 1].splitlines():
            label, vals = split_line(raw)
            _, vals2 = split_line(raw, 2)
            out.append(Line(pno, raw, label, vals, vals2))
    return out


def find_statement_pages(pages: list[str]) -> list[int]:
    hits = []
    for i, t in enumerate(pages):
        if re.search(r"finance costs?", t, re.I) and re.search(r"total (income|expenses)", t, re.I):
            hits.append(i + 1)
    return hits


def detect_basis(page_text: str) -> str | None:
    head = page_text[:900].lower()
    c, s = head.find("consolidated"), head.find("standalone")
    if c < 0 and s < 0:
        return None
    if s < 0 or (0 <= c < s):
        return "consolidated"
    return "standalone"


def _first(lines: list[Line], key: str, after: int = -1) -> tuple[int, Line] | None:
    pat = LABELS[key]
    for i, ln in enumerate(lines):
        if i <= after or len(ln.values) < 3:
            continue
        if pat.search(ln.text if key in ("total_revenue_ops",) else ln.label):
            return i, ln
    return None


def _metric(lines: list[Line], key: str, after: int = -1):
    f = _first(lines, key, after)
    if not f:
        return None, None
    i, ln = f
    return i, Metric([*ln.values[:3]], ln.page, ln.text.strip())


def parse_statement(pages: list[str], page: int) -> ParsedResults:
    lines = _lines(pages, page)
    basis = detect_basis(pages[page - 1])
    res = ParsedResults(status="see_pdf", basis=basis, page=page)
    if BANK_HINT.search(pages[page - 1]) and not re.search(
        r"finance costs?", pages[page - 1], re.I
    ):
        res.status, res.reason = "unsupported", "format not supported"
        return res

    m: dict[str, Metric] = {}
    for key in (
        "total_revenue_ops", "revenue_ops", "other_income", "total_income", "finance_cost",
        "dep", "total_expenses", "total_tax",
    ):  # fmt: skip
        _, mt = _metric(lines, key)
        if mt:
            m[key] = mt
    pre_i, pre = _metric(lines, "pbt_pre_exc")
    pbt_i, pbt = _metric(lines, "pbt", after=-1)
    if pre:
        m["pbt_pre_exc"] = pre
    if pbt:
        m["pbt"] = pbt
    if "total_revenue_ops" in m:
        m["revenue"] = m["total_revenue_ops"]
    elif "revenue_ops" in m:
        m["revenue"] = m["revenue_ops"]
    # tax lines and PAT must come after PBT
    anchor = pbt_i if pbt_i is not None else -1
    if "total_tax" not in m:
        for key in ("current_tax", "deferred_tax"):
            _, mt = _metric(lines, key, after=anchor)
            if mt:
                m[key] = mt
    _, pat = _metric(lines, "pat", after=anchor)
    if pat:
        m["pat"] = pat
    jv_pre = None
    if pre_i is not None:
        j = [
            ln for i, ln in enumerate(lines)
            if i < pre_i and LABELS["jv_share"].search(ln.label or ln.text) and len(ln.values2) >= 2
        ]  # fmt: skip
        if j:
            v = [*j[-1].values2[:3]] + [None] * (3 - len(j[-1].values2[:3]))
            jv_pre = Metric(v, j[-1].page, j[-1].text.strip())
    res.metrics = m

    need = [
        "revenue",
        "other_income",
        "total_income",
        "finance_cost",
        "dep",
        "total_expenses",
        "pbt",
    ]
    missing = [k for k in need if k not in m]
    if missing or "pat" not in m:
        res.reason = "missing lines: " + ", ".join(missing + ([] if "pat" in m else ["pat"]))
        return res

    def col(k: str, c: int) -> float:
        return m[k].values[c]

    def tax(c: int) -> float | None:
        if "total_tax" in m:
            return col("total_tax", c)
        parts = [m[k].values[c] for k in ("current_tax", "deferred_tax") if k in m]
        return sum(parts) if parts else None

    def tol(*vals: float) -> float:
        return 1.0 if all(float(v).is_integer() for v in vals) else 0.15

    c1, c2, c3 = [], [], []
    for c in range(3):
        a, b = col("revenue", c), col("other_income", c)
        t = col("total_income", c)
        c1.append(abs(a + b - t) <= tol(a, b, t))
        te = col("total_expenses", c)
        base = t - te
        if pre:
            p = col("pbt_pre_exc", c)
            jv = jv_pre.values[c] if jv_pre else 0.0
            c2.append(jv is not None and abs(base + jv - p) <= tol(t, te, p, jv))
        else:
            p = col("pbt", c)
            c2.append(abs(base - p) <= tol(t, te, p))
        tx = tax(c)
        pt, pa = col("pbt", c), col("pat", c)
        c3.append(tx is not None and abs(pt - tx - pa) <= tol(pt, tx, pa))
    res.checks = [
        Check("revenue + other income = total income", c1),
        Check("total income − total expenses = profit before tax (pre-exceptional)", c2),
        Check("profit before tax − tax = profit after tax", c3),
    ]
    res.column_ok = [all(ch.ok[c] for ch in res.checks) for c in range(3)]

    exc, ebitda = [], []
    for c in range(3):
        p_pre = col("pbt_pre_exc", c) if pre else col("pbt", c)
        exc.append(round(col("pbt", c) - p_pre, 4) if pre else 0.0)
        ebitda.append(
            round(p_pre + col("finance_cost", c) + col("dep", c) - col("other_income", c), 4)
            if res.column_ok[c]
            else None
        )
    res.derived = {"ebitda": ebitda, "exceptional": exc}

    if res.column_ok[0]:
        res.status = "ok"
        oi, p0 = col("other_income", 0), col("pbt", 0)
        if p0 > 0 and oi > 0.20 * p0:
            res.flags.append("other_income_gt_20pct_pbt")
        if exc[0] != 0:
            res.flags.append("exceptional_item")
    else:
        res.reason = "identity check failed for this quarter"
    return res


def parse_results(pages: list[str]) -> ParsedResults:
    cands = find_statement_pages(pages)
    if not cands:
        return ParsedResults(status="see_pdf", reason="no statement found")
    parsed = [parse_statement(pages, p) for p in cands]
    unsupported = [p for p in parsed if p.status == "unsupported"]
    usable = [p for p in parsed if p.status != "unsupported"]
    if not usable:
        return unsupported[0]
    order = {"consolidated": 0, "standalone": 1, None: 2}
    usable.sort(key=lambda p: (p.status != "ok", order[p.basis]))
    # prefer consolidated if it parses ok; otherwise the best ok standalone
    best = next((p for p in usable if p.status == "ok"), None)
    cons = next((p for p in usable if p.basis == "consolidated"), None)
    if cons and cons.status != "ok" and best and best.basis != "consolidated":
        best.flags.append("standalone_only_consolidated_failed")
    return best or usable[0]


def to_dict(r: ParsedResults) -> dict:
    return {
        "status": r.status,
        "basis": r.basis,
        "page": r.page,
        "reason": r.reason,
        "column_ok": r.column_ok,
        "flags": r.flags,
        "checks": [{"name": c.name, "ok": c.ok} for c in r.checks],
        "metrics": {
            k: {"values": v.values, "page": v.page, "line": v.line} for k, v in r.metrics.items()
        },
        "derived": r.derived,
    }


def change_pct(cur: float | None, prev: float | None) -> float | None:
    """Percent change. None when either side is missing or the base is not positive."""
    if cur is None or prev is None or prev <= 0:
        return None
    return round((cur / prev - 1) * 100, 1)


def restatement_flags(current: dict, prior: dict | None) -> list[str]:
    """Compare this filing with the stored result of the previous quarter's filing.

    `current` and `prior` are to_dict() outputs. Prior's this-quarter figures should equal
    this filing's preceding-quarter column; if they do not, periods were restated.
    """
    if not prior or prior.get("status") != "ok" or current.get("status") != "ok":
        return []
    flags: list[str] = []
    if prior.get("basis") and current.get("basis") and prior["basis"] != current["basis"]:
        flags.append("basis_switch")
    for k in ("revenue", "pbt", "pat"):
        a = prior["metrics"].get(k, {}).get("values", [None])[0]
        b = current["metrics"].get(k, {}).get("values", [None, None])[1]
        if (
            a is not None
            and b is not None
            and abs(a - b) > (1.0 if float(a).is_integer() else 0.15)
        ):
            flags.append("restated_periods")
            break
    return flags
