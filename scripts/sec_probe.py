"""Which request format does the SEC accept from GitHub's machines? Writes research/universe/sec-probe.md.

The SEC asks automated clients to identify themselves in the User-Agent (name and contact address) and to send
Accept-Encoding. This tries a few compliant variants against both SEC hosts and records the status codes only.
"""

from __future__ import annotations

import gzip
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTACT = "SamBates1@users.noreply.github.com"
AGENTS = {
    "name + contact": f"Aurum research project {CONTACT}",
    "short": f"SamBates1 {CONTACT}",
    "browser-style + contact": (
        f"Mozilla/5.0 (compatible; AurumResearch/1.0; +https://github.com/SamBates1/aurum-) {CONTACT}"
    ),
}
URLS = {
    "ticker list (www.sec.gov)": "https://www.sec.gov/files/company_tickers.json",
    "company facts (data.sec.gov)": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json",
}


def probe(url: str, ua: str, gz: bool) -> str:
    h = {"User-Agent": ua, "Accept-Encoding": "gzip, deflate" if gz else "identity"}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30) as r:
            body = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
            return f"{r.status} ({len(body):,} bytes)"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return f"error: {type(e).__name__}"


lines = ["# SEC access probe", "", "| User-Agent | gzip | " + " | ".join(URLS) + " |", "|---|---|" + "---|" * len(URLS)]
for name, ua in AGENTS.items():
    for gz in (True, False):
        lines.append(
            f"| {name} | {'yes' if gz else 'no'} | " + " | ".join(probe(u, ua, gz) for u in URLS.values()) + " |"
        )
out = ROOT / "research" / "universe" / "sec-probe.md"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(lines) + "\n")
print("\n".join(lines))
sys.exit(0)
