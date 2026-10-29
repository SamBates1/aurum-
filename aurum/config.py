"""Configuration loading. All research choices live in config.yaml."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_config(path: str | os.PathLike | None = None) -> dict:
    path = Path(path or os.environ.get("AURUM_CONFIG", ROOT / "config.yaml"))
    with open(path) as fh:
        cfg = yaml.safe_load(fh)
    if os.environ.get("AURUM_OFFLINE", "").lower() in ("1", "true", "yes"):
        cfg["offline"] = True
    return cfg


CFG = load_config()


def all_tickers(cfg: dict = CFG) -> list[str]:
    return list(cfg["universe"]["core"]) + list(cfg["universe"]["equities"])


def is_equity(ticker: str, cfg: dict = CFG) -> bool:
    return ticker in cfg["universe"]["equities"]


def cost_bps(ticker: str, cfg: dict = CFG) -> float:
    """One-way trading cost assumption for a ticker, in basis points."""
    c = cfg["costs"]
    return float(c.get("per_ticker", {}).get(ticker, c["default_bps"]))


def config_hash(cfg: dict = CFG) -> str:
    """Short fingerprint of the configuration, recorded with every research run."""
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, default=str).encode()).hexdigest()[:12]


def code_fingerprint() -> str:
    """Hash of the research code (aurum/*.py and the run_*.py scripts). Recorded with every result and used in
    checkpoint names, so a code change can never silently reuse results computed by older code."""
    h = hashlib.sha256()
    for p in sorted([*(ROOT / "aurum").glob("*.py"), *ROOT.glob("run_*.py")]):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def git_commit() -> str:
    """Current git commit (short), or 'unknown' outside a git checkout."""
    import subprocess

    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=10
        )
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--", "aurum", "run_*.py", "config.yaml"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        return (out.stdout.strip() or "unknown") + ("-dirty" if dirty else "")
    except Exception:
        return "unknown"
