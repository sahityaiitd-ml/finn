"""Guidance extraction from earnings-call transcripts.

The model only extracts what management said, with a verbatim quote and the page it came from.
Python then verifies every quote against its page and decides everything else.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from extract.llm import Completer
from extract.quotes import locate, numbers_in

BIG_MODEL = "openai/gpt-oss-120b"
PROMPT_VERSION = "guidance-v2"
PAGES_PER_CALL = 6

METRICS = [
    "revenue_growth", "ebitda_margin", "ebitda_growth", "ebit_margin", "pat_growth",
    "pbt_growth", "revenue_level", "ebitda_level", "pat_level", "capex", "volume_growth",
    "order_book", "other",
]  # fmt: skip
BASES = ["yoy", "qoq", "cagr", "level", "unspecified"]
QUALIFIERS = ["none", "constant_currency", "organic", "volume", "segment", "other"]
DIRECTIONS = ["range", "point", "min", "max", "none"]

FORWARD = re.compile(
    r"\b(expect\w*|guid\w+|aspir\w+|target\w*|outlook|going forward|next (?:quarter|year|few)|"
    r"fy ?'?2?\d|full[- ]year|for the year|range|band|should (?:be|grow|see|remain)|"
    r"anticipat\w+|at least|around|approximately|between|double[- ]digit|confident|"
    r"on track|aim\w*|plan\w* to)\b",
    re.I,
)
NUMERIC = re.compile(r"\d[\d,.]*\s?(?:%|bps|basis points|crore|cr\b|billion|million|x\b)", re.I)

SYSTEM = (
    "You extract forward-looking management guidance from an Indian company's earnings-call "
    "transcript pages. Use ONLY the text given. Include a statement only if management says "
    "something about the company's FUTURE performance. Copy each quote VERBATIM from the page "
    '(max 40 words), never paraphrase. Include qualitative statements too (direction "none"). '
    "Do not compute anything. Reply with JSON only:\n"
    '{"items":[{"page":<int>,"quote":"<verbatim>","metric":<one of METRICS>,'
    '"basis":<one of BASES>,"qualifier":<one of QUALIFIERS>,'
    '"period":"<as spoken, e.g. FY27, Q2 FY27, next quarter, second half>",'
    '"direction":<one of DIRECTIONS>,"low":<number or null>,"high":<number or null>,'
    '"unit":"percent|inr_crore|other"}]}\n'
    "METRICS: "
    + ", ".join(METRICS)
    + "\nBASES: "
    + ", ".join(BASES)
    + "\nQUALIFIERS: "
    + ", ".join(QUALIFIERS)
    + "\nDIRECTIONS: "
    + ", ".join(DIRECTIONS)
    + "\nIf the speaker gives a number, put it in low/high exactly as spoken (e.g. 14-15%: "
    "low 14, high 15). If there is no number, use direction none and null low/high."
)


DOUBLE_DIGIT = re.compile(r"double[- ]digit", re.I)
MARGIN_CTX = re.compile(r"margin", re.I)
GROWTH_CTX = re.compile(r"growth|grow|increase|expan", re.I)


def refine_metric(metric: str, quote: str, page_text: str, start: int, end: int) -> str:
    """Python guard: a metric label must be supported by the words around the quote.

    The model sometimes labels "exit at 25% plus" as a margin when the page never says margin.
    Unsupported labels become "other", which is never compared with a reported number.
    """
    ctx = page_text[max(0, start - 350) : end + 350]
    if metric in ("ebitda_margin", "ebit_margin"):
        if not MARGIN_CTX.search(ctx):
            return "other"
        low = ctx.lower()
        if "ebitda" in low:
            return "ebitda_margin"
        if "operating margin" in low or "ebit margin" in low or "ebit " in low:
            return "ebit_margin"
        return "other"  # a bare "margin" is ambiguous, so it is not compared
    if metric.endswith("_growth") and not GROWTH_CTX.search(ctx):
        return "other"
    return metric


@dataclass
class Item:
    page: int
    quote: str
    metric: str
    basis: str
    qualifier: str
    period: str
    direction: str
    low: float | None
    high: float | None
    unit: str
    match_score: float
    start: int
    end: int


@dataclass
class Extraction:
    items: list[Item] = field(default_factory=list)
    pages_sent: list[int] = field(default_factory=list)
    dropped_quote: int = 0
    dropped_other: int = 0
    error: str | None = None  # set when the model call or its JSON failed: NOT "no guidance"


def score_page(text: str) -> float:
    fw = len(FORWARD.findall(text))
    return fw + (0.5 * len(NUMERIC.findall(text)) if fw else 0.0)


def pick_pages(pages: dict[int, str], k: int = PAGES_PER_CALL) -> list[int]:
    """Top-k pages by forward-looking cues, returned in page order. Saves tokens per call."""
    ranked = sorted(pages, key=lambda p: (-score_page(pages[p]), p))
    return sorted(p for p in ranked[:k] if score_page(pages[p]) > 0)


def _num(v) -> float | None:
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def extract(llm: Completer, pages: dict[int, str], k: int = PAGES_PER_CALL) -> Extraction:
    picked = pick_pages(pages, k)
    out = Extraction(pages_sent=picked)
    if not picked:
        return out
    user = "\n\n".join(f"=== PAGE {p} ===\n{pages[p]}" for p in picked)
    try:
        data = json.loads(
            llm.complete(getattr(llm, "big_model", BIG_MODEL), PROMPT_VERSION, SYSTEM, user)
        )
    except Exception as e:
        out.error = f"{type(e).__name__}: {str(e)[:120]}"
        return out
    seen: set[str] = set()
    for raw in data.get("items", []):
        try:
            page, quote = int(raw["page"]), str(raw["quote"]).strip()
        except (KeyError, TypeError, ValueError):
            out.dropped_other += 1
            continue
        if page not in picked or not quote:
            out.dropped_other += 1
            continue
        hit = locate(quote, pages[page])  # fuzzy >= 90 against the cited page, or dropped
        if hit is None:
            out.dropped_quote += 1
            continue
        key = re.sub(r"\W+", " ", quote.lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        low, high = _num(raw.get("low")), _num(raw.get("high"))
        spoken = set(numbers_in(quote))
        # a number the model returns must appear in the quote; otherwise it is not guidance
        if (low is not None and low not in spoken) or (high is not None and high not in spoken):
            low = high = None
        direction = raw.get("direction") if raw.get("direction") in DIRECTIONS else "none"
        unit = str(raw.get("unit") or "other")
        if low is None and high is None and DOUBLE_DIGIT.search(quote):
            # "double-digit" is a number management gave: at least 10 (percent)
            direction, low, unit = "min", 10.0, "percent"
        if low is None and high is None:
            direction = "none"
        out.items.append(
            Item(
                page=page,
                quote=quote,
                metric=refine_metric(
                    raw.get("metric") if raw.get("metric") in METRICS else "other",
                    quote,
                    pages[page],
                    hit.start,
                    hit.end,
                ),
                basis=raw.get("basis") if raw.get("basis") in BASES else "unspecified",
                qualifier=raw.get("qualifier") if raw.get("qualifier") in QUALIFIERS else "other",
                period=str(raw.get("period") or ""),
                direction=direction,
                low=low,
                high=high,
                unit=unit,
                match_score=hit.score,
                start=hit.start,
                end=hit.end,
            )
        )
    return out
