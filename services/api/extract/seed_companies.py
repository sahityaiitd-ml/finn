"""One-off: build data/demo/companies.json (symbol, name, BSE code) from screener pages."""

import json
import re
import sys
import time
from pathlib import Path

import httpx

from extract.screener import parse_bse_code

UA = "FINN-research-bot/0.1 (educational project)"
PORTFOLIO = [
    "RELIANCE", "TCS", "INFY", "HINDUNILVR", "ITC", "LT", "SUNPHARMA", "MARUTI", "TATASTEEL",
    "ASIANPAINT", "TITAN", "ULTRACEMCO", "BHARTIARTL", "DABUR", "POLYCAB", "PIDILITIND",
    "CEATLTD", "AARTIIND",
]  # fmt: skip
RESEARCH = ["DIXON", "TRENT", "DMART", "ASTRAL"]


def main(out: Path) -> None:
    rows = []
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=30) as c:
        for sym in PORTFOLIO + RESEARCH:
            r = c.get(f"https://www.screener.in/company/{sym}/consolidated/")
            html = r.text
            m = re.search(r"<title>(.*?)</title>", html)
            name = html.unescape((m.group(1).split(" share price")[0] if m else sym).strip())
            rows.append(
                {
                    "symbol": sym,
                    "name": name,
                    "bse_code": parse_bse_code(html),
                    "group": "portfolio" if sym in PORTFOLIO else "research",
                    "status": r.status_code,
                }
            )
            print(rows[-1], file=sys.stderr)
            time.sleep(1.5)
    out.write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
