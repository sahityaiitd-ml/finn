"""Rules-first filing classifier (17 ENAM categories) plus the never-collapse floor.

The model is only for leftovers (see extract/llm.py). When a filing could be material
and we are unsure, it is shown, never hidden.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

CATEGORIES = [
    "results", "M&A", "fund_raise", "management_change", "litigation", "insider_trading",
    "earnings_call", "investor_meetings", "credit_rating", "dividend", "bonus_split", "capex",
    "press_release", "postal_ballot", "agm_egm", "pledging", "unclassified",
]  # fmt: skip

# Categories that can never be collapsed into the routine drawer.
FLOOR_CATEGORIES = {
    "results", "M&A", "fund_raise", "management_change", "litigation", "credit_rating", "pledging",
}  # fmt: skip


@dataclass(frozen=True)
class Verdict:
    category: str
    rule: str
    never_collapse: bool
    floor_reason: str | None = None


def _r(p: str) -> re.Pattern:
    return re.compile(p, re.I)


# (rule id, category, pattern). First match wins, so order = priority.
RULES: list[tuple[str, str, re.Pattern]] = [
    ("pledge", "pledging", _r(r"\bpledg|encumbrance|invocation of (pledge|shares)")),
    ("rating", "credit_rating", _r(r"credit rating|\brating\b.*(assign|upgrad|downgrad|reaffirm|revis)|"
                                    r"(crisil|icra|care ratings|india ratings|brickwork)")),
    ("litigation", "litigation", _r(r"\bcirp\b|insolvency|nclt|show[- ]cause|\bpenalt(y|ies)\b|"
                                     r"\bfine[sd]?\b.*(impos|levi)|tribunal|lawsuit|legal proceeding|"
                                     r"orders? passed|action\(s\) initiated|\blitigation|"
                                     r"adjudicat|court order|search and seizure|raid")),
    ("m&a", "M&A", _r(r"\bacqui(re|sition)|\bmerger|amalgamat|demerger|scheme of arrangement|"
                       r"joint venture|\bstake (sale|purchase)|divest|strategic investment|"
                       r"incorporation of .*subsidiary|wholly[- ]owned subsidiary")),
    ("repay", "fund_raise", _r(r"(repayment|redemption|redeem) of (commercial paper|\bcp\b|debenture|ncd)")),
    ("fundraise", "fund_raise", _r(r"rights issue|\bqip\b|qualified institutions|preferential (issue|allot)|"
                                    r"\bbuy[- ]?back|commercial paper|non[- ]convertible|\bncds?\b|debentures?|"
                                    r"fund ?rais|raising of funds|\bfpo\b|\bipo\b|external commercial borrowing")),
    ("bonus_split", "bonus_split", _r(r"bonus (issue|shares)|stock split|sub-?division of (equity )?shares")),
    ("dividend", "dividend", _r(r"\bdividend|record date")),
    ("subsid_exit", "M&A", _r(r"(dissol|liquidat|strike[- ]?off|struck off|wound up|winding up|closure of).{0,60}(subsidiary|branch|step-down)|(subsidiary|step-down|branch).{0,60}(dissol|liquidat|struck off|wound up|closed|closure)")),
    ("auditor", "unclassified", _r(r"\bauditors?\b.*(resign|cessation|change|appoint|vacat)|"
                                    r"(resign|cessation|change|appoint).{0,30}\bauditors?\b")),
    ("mgmt", "management_change", _r(r"change in (directorate|management|key managerial)|"
                                      r"(appointment|resignation|cessation|retirement|re-?appointment) of .{0,60}"
                                      r"(director|ceo|cfo|chief|managing|company secretary|compliance officer|kmp)|"
                                      r"appoint(s|ed|ment)?\b.{0,60}(director|ceo|cfo|chief|managing|company secretary|compliance officer|kmp)|"
                                      r"key managerial personnel|\bkmp\b|"
                                      r"\bresign(s|ed|ation)\b|\bdemise\b")),
    ("results", "results", _r(r"(un)?audited (standalone |consolidated )?financial results|"
                               r"financial results|quarterly results|results? (of|for) the (quarter|year)|"
                               r"earnings presentation|results presentation|"
                               r"newspaper publication.*results|results.*newspaper")),
    ("earnings_call", "earnings_call", _r(r"earnings call|conference call|\bcon[- ]?call|"
                                           r"audio recording|transcript")),
    ("insider", "insider_trading", _r(r"insider trading|regulation 7\b|reg 7\(|sebi \(pit\)|"
                                       r"trading by (promoter|insider|designated)|disclosure under regulation 29")),
    ("investor_meet", "investor_meetings", _r(r"analyst\W*(s\W*)?/?\W*investor|investor\W*(s\W*)?meet|"
                                               r"investor conference|institutional investors?|"
                                               r"investor/analyst|schedule of (analyst|investor)")),
    ("capex", "capex", _r(r"\bcapex\b|capital expenditure|capacity expansion|new (plant|facility|unit)|"
                           r"expansion of .*(plant|facility|centre|center|capacity)|greenfield|brownfield")),
    ("postal", "postal_ballot", _r(r"postal ballot|scrutini[sz]er")),
    ("agm", "agm_egm", _r(r"\bagm\b|\begm\b|annual general meeting|extraordinary general meeting|"
                           r"book closure|e-voting")),
    ("press", "press_release", _r(r"press release|media release|bagging|receiving of order|order win|"
                                   r"rumou?r|clarification|production volume|sales volume|launch(es|ed)?\b|"
                                   r"partnership|collaborat|awards?\b|prize|announces?\b")),
    ("routine", "unclassified", _r(r"newspaper publication|allotment of esop|esop|espss?|share certificate|"
                                    r"registrar and share transfer|\brta\b|compliance certificate|"
                                    r"closure of trading window|trading window|annual report|"
                                    r"\besg\b|sustainability|business responsibility|"
                                    r"regulation 74|regulation 40|reg\. ?40|schedule of events|"
                                    r"investor presentation")),
]  # fmt: skip

BOARD_OUTCOME = _r(r"outcome of (the )?board meeting|board meeting outcome|board meeting")
GENERIC_HEADLINE = _r(
    r"^(announcement under regulation 30 \(lodr\)\W*)?(intimation|disclosure|submission|information)"
    r"[^-]*regulation|^intimation under|^disclosure under|^submission of information"
)


def classify(headline: str, description: str = "") -> Verdict | None:
    """Return a Verdict, or None when no rule fires (a leftover for the model)."""
    text = f"{headline} | {description}"
    floor_reason: str | None = None

    if BOARD_OUTCOME.search(text) and re.search(r"outcome", text, re.I):
        # Board outcomes are never collapsed, whatever else they contain.
        v = _first_match(text)
        cat = v[1] if v else "press_release"
        return Verdict(cat, "board_outcome", True, "board_outcome")

    hit = _first_match(text)
    if hit is None:
        return None
    rule, cat = hit
    if rule == "auditor":
        floor_reason = "auditor_change"
    elif rule == "repay":
        return Verdict(cat, rule, False)  # repaying a CP is routine, not a raise
    elif cat in FLOOR_CATEGORIES:
        floor_reason = f"floor:{cat}"
    return Verdict(cat, rule, floor_reason is not None, floor_reason)


def _first_match(text: str) -> tuple[str, str] | None:
    for rule, cat, pat in RULES:
        if pat.search(text):
            return rule, cat
    return None


def is_generic_headline(headline: str) -> bool:
    """Headline says little (e.g. 'Intimation Under Regulation 30...'): a summary helps."""
    return bool(GENERIC_HEADLINE.search(headline.strip()))
