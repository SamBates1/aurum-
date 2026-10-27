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
