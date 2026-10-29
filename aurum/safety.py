"""Pre-trade checks and decision records (brief 2026-10-29, §6 and §10).

Every order the paper trader (and later the Alpaca connection) wants to place passes through `pre_trade_checks`
first. A failed check blocks the order and is written to the decision log with the reason; nothing fails silently.

Checks (all configurable under `live:` in config.yaml):
  kill_switch       trading_enabled is false, or a file named STOP_TRADING exists in the project folder
  data_fresh        the decision was made on fresh, valid data (pipeline marks stale data untradeable)
  price_sane        price is positive and within max_price_jump of the last completed close (bad-tick guard)
  one_order_per_day at most one order per asset per trading day (prevents duplicate orders from a loop)
  max_orders        at most max_orders_per_day orders in total per day
  position_limit    target weight within [0, 1] of the asset's sleeve (no leverage, no unlimited adding)
  cash_available    buys never need more cash than the account holds

`decision_record` builds the structured explanation the brief asks for: signal, rationale, size, risk, exit rule
and the result of every check. Records are appended to a JSON-lines file (git-ignored).
"""

from __future__ import annotations

import json
import math
from datetime import date, datetime
from pathlib import Path

from .config import ROOT

KILL_FILE = ROOT / "STOP_TRADING"


def live_cfg(cfg: dict) -> dict:
    d = {
        "trading_enabled": True,
        "max_orders_per_day": 12,
        "max_price_jump": 0.25,
        "decision_log": "logs/decisions.jsonl",
    }
    d.update(cfg.get("live", {}) or {})
    return d


def pre_trade_checks(
    *,
    ticker: str,
    side: str,
    target_weight: float,
    price: float,
    last_close: float | None,
    tradeable: bool,
    state: dict,
    cfg: dict,
    cash_needed: float = 0.0,
    today: date | None = None,
) -> list[dict]:
    lc = live_cfg(cfg)
    today = today or date.today()
    orders = state.get("orders_by_day", {}).get(str(today), {})
    checks = []

    def add(name, ok, detail):
        checks.append({"check": name, "passed": bool(ok), "detail": detail})

    killed = (not lc["trading_enabled"]) or KILL_FILE.exists()
    add("kill_switch", not killed, "trading switched off" if killed else "trading enabled")
    add("data_fresh", tradeable, "fresh completed bars" if tradeable else "stale or invalid data: no trading")
    ok_px = isinstance(price, (int, float)) and math.isfinite(price) and price > 0
    jump = abs(price / last_close - 1) if ok_px and last_close and last_close > 0 else 0.0
    add(
        "price_sane",
        ok_px and jump <= lc["max_price_jump"],
        f"price {price!r}, {jump:.1%} from last close (limit {lc['max_price_jump']:.0%})",
    )
    add(
        "one_order_per_day",
        ticker not in orders,
        "first order today" if ticker not in orders else f"already ordered {ticker} today ({orders[ticker]})",
    )
    n = len(orders)
    add("max_orders", n < lc["max_orders_per_day"], f"{n} orders today (limit {lc['max_orders_per_day']})")
    add("position_limit", 0.0 <= target_weight <= 1.0, f"target {target_weight:.0%} of sleeve (allowed 0-100%)")
    if side == "BUY":
        cash = state.get("cash", 0.0)
        add("cash_available", cash_needed <= cash + 1e-9, f"needs {cash_needed:,.2f}, cash {cash:,.2f}")
    return checks


def passed(checks: list[dict]) -> bool:
    return all(c["passed"] for c in checks)


def record_order(state: dict, ticker: str, summary: str, today: date | None = None) -> None:
    day = str(today or date.today())
    book = state.setdefault("orders_by_day", {})
    book.setdefault(day, {})[ticker] = summary
    for old in sorted(book)[:-10]:  # keep the last 10 trading days
        book.pop(old, None)


def decision_record(d, *, current_weight: float, planned: dict | None, checks: list[dict], cfg: dict) -> dict:
    """Structured explanation of one decision (brief §10)."""
    scfg = cfg["strategy"]
    tw = getattr(d, "target_weight", None)
    vol = getattr(d, "ann_vol", float("nan"))
    return {
        "time": datetime.now().isoformat(timespec="seconds"),
        "ticker": d.ticker,
        "data_as_of": getattr(d, "as_of", None),
        "mode": scfg.get("mode", "timing"),
        "signal": {
            "target_weight_of_sleeve": tw,
            "rebalance_day": getattr(d, "rebalance_day", True),
            "context_only": {
                "score": getattr(d, "score", None),
                "p_up": getattr(d, "prob_up", None),
                "model_auc": getattr(d, "auc", None),
            },
        },
        "rationale": list(getattr(d, "notes", []))[:3],
        "position": {"current_weight_of_sleeve": current_weight, "band": scfg.get("rebalance_band", 0.05)},
        "planned_order": planned,
        "expected_risk": {
            "asset_volatility_21d": vol,
            "volatility_target": scfg.get("target_vol"),
            "position_volatility_contribution": (tw or 0.0) * vol if vol == vol else None,
        },
        "exit_rule": "No stop-loss in vol_hold mode (tested: stops did not help, EXP-005/023/033). The position "
        "shrinks as volatility rises and is sold only if the target falls below the current weight by more than "
        "the band; all orders stop if data are stale or a check fails.",
        "checks": checks,
        "allowed": passed(checks) if checks else None,
    }


def write_record(rec: dict, cfg: dict) -> Path:
    path = ROOT / live_cfg(cfg)["decision_log"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as fh:
        fh.write(json.dumps(rec, default=str) + "\n")
    return path
