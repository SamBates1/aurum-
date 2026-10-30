"""API keys from the environment or a private .env file (never committed: .env is git-ignored)."""

from __future__ import annotations

import os

from ..config import ROOT


def _dotenv() -> dict[str, str]:
    path = ROOT / ".env"
    out = {}
    if not path.is_file():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def alpaca_keys() -> tuple[str, str] | None:
    """(key id, secret) or None. Environment variables win over the .env file."""
    env = _dotenv()
    key = os.environ.get("ALPACA_API_KEY") or env.get("ALPACA_API_KEY")
    secret = os.environ.get("ALPACA_SECRET_KEY") or env.get("ALPACA_SECRET_KEY")
    return (key, secret) if key and secret else None


def redact(text: str) -> str:
    """Remove any key material from a message before it is shown or logged."""
    k = alpaca_keys()
    if k:
        for s in k:
            if s:
                text = text.replace(s, "***")
    return text
