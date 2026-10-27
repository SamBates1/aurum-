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
