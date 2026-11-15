"""Materiality score 0-100, computed in Python. Never a model output."""

from __future__ import annotations

import re

BASE = {
    "results": 90, "M&A": 85, "litigation": 80, "fund_raise": 75, "management_change": 75,
    "credit_rating": 70, "pledging": 70, "dividend": 60, "bonus_split": 60, "capex": 55,
    "insider_trading": 45, "earnings_call": 40, "press_release": 35, "agm_egm": 25,
    "postal_ballot": 25, "investor_meetings": 15, "unclassified": 5,
}  # fmt: skip

BOOST = re.compile(
    r"resign|downgrad|default|fraud|penalt|insolven|\bcirp\b|delist|suspend|"
    r"qualified opinion|going concern|invocation|search|investigation|"
    r"\bceo\b|\bcfo\b|managing director",
    re.I,
)

ROUTINE_BELOW = 30  # below this (and not floored) a filing goes to the routine drawer


def materiality(category: str, headline: str, description: str, never_collapse: bool) -> int:
    score = BASE.get(category, 5)
    if BOOST.search(f"{headline} {description}"):
        score += 10
    if never_collapse:
        score = max(score, 50)  # the floor also lifts the score so it ranks sensibly
    return min(score, 100)


def is_routine(score: float, never_collapse: bool) -> bool:
    return (not never_collapse) and score < ROUTINE_BELOW
