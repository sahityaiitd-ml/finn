"""Small-model calls (Groq) for leftover classification and short summaries.

Every call is cached forever by sha256(model + prompt_version + input). The model only
labels and rewords what it is given; Python validates the output and sets all scores.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Protocol

import httpx

from app.config import settings
from rules.classify import CATEGORIES

SMALL_MODEL = "openai/gpt-oss-20b"
PROMPT_VERSION = "classify-v1"
MAX_SUMMARY_WORDS = 25

SYSTEM = (
    "You label Indian stock-exchange announcements. Use ONLY the text given. "
    'Reply with JSON: {"category": <one of CATEGORIES or "unsure">, '
    '"summary": <=25 words, plain, using only facts in the text>}. '
    'If the text could be material and you are not sure, use "unsure". '
    "CATEGORIES: " + ", ".join(CATEGORIES)
)


class Completer(Protocol):
    def complete(self, model: str, version: str, system: str, user: str) -> str: ...


def cache_key(model: str, version: str, text: str) -> str:
    return hashlib.sha256(f"{model}|{version}|{text}".encode()).hexdigest()


class GroqCompleter:
    """Groq chat completions with a Supabase-backed cache."""

    def __init__(self, db=None, api_key: str | None = None):
        self.db, self.key = db, api_key or settings.groq_api_key

    def complete(self, model: str, version: str, system: str, user: str) -> str:
        key = cache_key(model, version, system + "\n" + user)
        if self.db is not None:
            hit = self.db.table("llm_cache").select("response").eq("key", key).execute().data
            if hit:
                return hit[0]["response"]["text"]
        r = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
                "reasoning_effort": "low",
                "max_completion_tokens": 600,
                "temperature": 0,
            },
            timeout=60,
        )
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"] or ""
        if self.db is not None:
            self.db.table("llm_cache").upsert(
                {"key": key, "model": model, "prompt_version": version, "response": {"text": text}}
            ).execute()
        return text


_NUM = re.compile(r"\d[\d,.]*")


def clean_summary(summary: str, source: str) -> str | None:
    """Enforce <=25 words and that every number in the summary appears in the source text."""
    s = " ".join(str(summary or "").split())
    if not s:
        return None
    words = s.split()
    if len(words) > MAX_SUMMARY_WORDS:
        s = " ".join(words[:MAX_SUMMARY_WORDS]).rstrip(",;:") + "…"
    for n in _NUM.findall(s):
        if n.strip(".,") not in source:
            return None
    return s


def analyse(llm: Completer, headline: str, description: str) -> tuple[str, str | None]:
    """Return (category or 'unsure', summary or None). Bad model output means 'unsure'."""
    user = f"Headline: {headline}\nText: {description}"
    try:
        raw = llm.complete(SMALL_MODEL, PROMPT_VERSION, SYSTEM, user)
        data = json.loads(raw)
    except Exception:
        return "unsure", None
    cat = data.get("category")
    if cat not in CATEGORIES:
        cat = "unsure"
    return cat, clean_summary(data.get("summary", ""), f"{headline} {description}")
