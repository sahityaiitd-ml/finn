"""Locate a quote on a page. A quote that cannot be found (rapidfuzz >= 90) is dropped."""

from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz

MIN_SCORE = 90.0


@dataclass(frozen=True)
class Hit:
    start: int  # indices into the ORIGINAL page text
    end: int
    score: float


def _normalise(text: str) -> tuple[str, list[int]]:
    """Lower-case, collapse whitespace, normalise quotes; keep a map back to original indices."""
    out: list[str] = []
    idx: list[int] = []
    prev_space = True
    for i, ch in enumerate(text):
        ch = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-"}.get(ch, ch)
        if ch.isspace():
            if prev_space:
                continue
            ch, prev_space = " ", True
        else:
            prev_space = False
        out.append(ch.lower())
        idx.append(i)
    return "".join(out).strip(), idx


def locate(quote: str, page_text: str, min_score: float = MIN_SCORE) -> Hit | None:
    q, _ = _normalise(quote)
    t, idx = _normalise(page_text)
    if len(q) < 12 or not t:
        return None
    al = fuzz.partial_ratio_alignment(q, t)
    if al is None or al.score < min_score:
        return None
    start = idx[min(al.dest_start, len(idx) - 1)]
    end = idx[min(max(al.dest_end - 1, 0), len(idx) - 1)] + 1
    return Hit(start, end, round(al.score, 1))


def numbers_in(text: str) -> list[float]:
    return [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*\.?\d*", text) if x.strip(",.")]
