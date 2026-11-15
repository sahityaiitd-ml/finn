"""Small-model calls (Groq) for leftover classification and short summaries.

Every call is cached forever by sha256(model + prompt_version + input). The model only
labels and rewords what it is given; Python validates the output and sets all scores.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
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


MAX_TRIES = 6


def retry_wait(retry_after: str | None, attempt: int) -> float:
    """Seconds to wait after a 429: Groq's retry-after if given, else a growing backoff."""
    try:
        return min(float(retry_after), 65.0) + 1.0
    except (TypeError, ValueError):
        return min(10.0 * attempt, 65.0)


class Completer(Protocol):
    def complete(self, model: str, version: str, system: str, user: str) -> str: ...


def cache_key(model: str, version: str, text: str) -> str:
    return hashlib.sha256(f"{model}|{version}|{text}".encode()).hexdigest()


class GroqCompleter:
    """Groq chat completions with a Supabase-backed cache."""

    def __init__(self, db=None, api_key: str | None = None, max_tokens: int = 600):
        self.db, self.key, self.max_tokens = db, api_key or settings.groq_api_key, max_tokens

    def complete(self, model: str, version: str, system: str, user: str) -> str:
        key = cache_key(model, version, system + "\n" + user)
        if self.db is not None:
            hit = self.db.table("llm_cache").select("response").eq("key", key).execute().data
            if hit:
                return hit[0]["response"]["text"]
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "reasoning_effort": "low",
            "max_completion_tokens": self.max_tokens,
            "temperature": 0,
        }
        r = None
        for attempt in range(1, MAX_TRIES + 1):
            r = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.key}"},
                json=body,
                timeout=90,
            )
            if r.status_code != 429 or attempt == MAX_TRIES:
                break
            time.sleep(retry_wait(r.headers.get("retry-after"), attempt))
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


GEMINI_MODEL = settings.gemini_model.strip() or "gemini-3.5-flash"


def gemini_keys() -> list[str]:
    raw = f"{settings.gemini_api_keys},{settings.gemini_api_key}"
    seen: list[str] = []
    for k in (x.strip() for x in raw.split(",")):
        if k and k not in seen:
            seen.append(k)
    return seen


class GeminiCompleter:
    """Gemini with a Supabase-backed cache. Rotates through several keys on 429/5xx."""

    big_model = GEMINI_MODEL

    def __init__(self, db=None, keys: list[str] | None = None, max_tokens: int = 8000):
        self.db, self.keys, self.max_tokens = db, keys or gemini_keys(), max_tokens
        self._next = 0

    def complete(self, model: str, version: str, system: str, user: str) -> str:
        key = cache_key(model, version, system + "\n" + user)
        if self.db is not None:
            hit = self.db.table("llm_cache").select("response").eq("key", key).execute().data
            if hit:
                return hit[0]["response"]["text"]
        if not self.keys:
            raise RuntimeError("no Gemini key configured")
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0,
                "maxOutputTokens": self.max_tokens,
            },
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        r = None
        tries = MAX_TRIES * max(1, len(self.keys))
        for attempt in range(1, tries + 1):
            k = self.keys[self._next % len(self.keys)]
            r = httpx.post(url, headers={"x-goog-api-key": k}, json=body, timeout=120)
            if r.status_code not in (429, 500, 503) or attempt == tries:
                break
            self._next += 1  # try the next key straight away
            if attempt % len(self.keys) == 0:  # a full lap of keys is limited: wait a bit
                time.sleep(retry_wait(r.headers.get("retry-after"), attempt // len(self.keys)))
        r.raise_for_status()
        parts = r.json()["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        if self.db is not None:
            self.db.table("llm_cache").upsert(
                {"key": key, "model": model, "prompt_version": version, "response": {"text": text}}
            ).execute()
        return text


def big_completer(db=None) -> Completer:
    """Gemini for guidance when a key exists (far higher free-tier limits), else Groq."""
    if gemini_keys():
        return GeminiCompleter(db)
    return GroqCompleter(db, max_tokens=4000)
