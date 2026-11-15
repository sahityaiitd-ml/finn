"""PDF hashing and per-page text extraction. Pages are the citation unit."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

DEMO_NAME_RE = re.compile(r"^(?P<symbol>[A-Z0-9&-]+)_(?P<period>\d{4}-\d{2})\.pdf$")


@dataclass(frozen=True)
class DemoDoc:
    path: Path
    symbol: str
    period: str
    kind: str  # results | transcript


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_pages(path: Path) -> list[str]:
    """Text per page (1-indexed by list position + 1). Empty string if no text layer."""
    with pdfplumber.open(path) as pdf:
        return [(p.extract_text() or "") for p in pdf.pages]


def demo_docs(root: Path) -> list[DemoDoc]:
    out: list[DemoDoc] = []
    for sub, kind in (("results", "results"), ("transcripts", "transcript")):
        for p in sorted((root / sub).glob("*.pdf")):
            m = DEMO_NAME_RE.match(p.name)
            if m:
                out.append(DemoDoc(p, m["symbol"], m["period"], kind))
    return out
