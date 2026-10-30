"""Logic behind the Strategy Designer page (kept out of the Streamlit file so it can be tested).

describe(spec)              the strategy in plain English
load_prices(...)            daily data for every asset a strategy needs, plus the cash rate and GBP/USD
freshness(...)              how fresh each series is: LIVE (intraday, delayed), EOD (completed daily bars), STALE,
                            or SYNTHETIC (offline test data, never real prices)
sweep(...)                  research lab: one number varied over a grid, scored on the DEVELOPMENT period only
scanner(...)                the strategy's conditions evaluated today on every asset in the research universe
sweepable(spec)             the numbers a sweep can vary
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import data
from . import engine as E
from . import spec as SP
from .config import CFG
from .indicators import INDICATORS, compute

UNIVERSE = {
    "SPY": "US large-cap equities",
    "QQQ": "US Nasdaq-100 equities",
    "IWM": "US small-cap equities",
    "EFA": "Developed ex-US equities",
    "TLT": "US long Treasuries",
    "IEF": "US 7-10y Treasuries",
    "GLD": "Gold",
    "SLV": "Silver",
    "GDX": "Gold miners",
    "DBC": "Broad commodities",
}
DEV = (pd.Timestamp("2013-10-18"), pd.Timestamp("2023-12-31"))
HOLDOUT_START = pd.Timestamp("2024-01-01")


def pct(x: float) -> str:
    return f"{x:.0%}" if abs(x * 100 - round(x * 100)) < 1e-9 else f"{x:.1%}"


def describe(spec: dict) -> list[str]:
    s = SP.normalise(spec)
    out = []
    held = ", ".join(f"{pct(w)} {t}" for t, w in s["base_weights"].items() if w > 0)
    cash = 1 - sum(s["base_weights"].values())
    out.append(f"Starts from {held}" + (f" and {pct(cash)} cash" if cash > 1e-9 else "") + ".")
    sch = s["schedule"]
    when = {
        "once": "Buys once on the first day and never trades again",
        "daily": "Checks every trading day",
        "weekly": "Checks on the last trading day of each week",
        "monthly": "Trades back to target on the first trading day of each month",
        "quarterly": "Trades back to target on the first trading day of each quarter",
        "yearly": "Trades back to target on the first trading day of each year",
    }[sch["rebalance"]]
    out.append(
        when
        + (
            f", but only moves an asset more than {pct(sch['band'])} of the account away from its target"
            if sch["band"] > 0
            else ""
        )
        + (", and also on any day a rule flips" if sch["act_on_signal_change"] else "")
        + "."
    )
    sz = s["sizing"]
    if sz["method"] == "vol_cap":
        out.append(
            f"Risk cap: each asset's share is multiplied by min(1, {pct(sz['target_vol'])} / its "
            f"{sz['vol_window']}-day volatility); what is cut is held as cash earning the T-bill rate."
        )
    elif sz["method"] == "inverse_vol":
        out.append(
            "Risk balance: the invested total is split in proportion to 1 / each asset's "
            f"{sz['vol_window']}-day volatility."
        )
    for g in s["signals"]:
        conds = [SP.condition_label(c) for c in g["conditions"]]
        joiner = {"all": " AND ", "any": " OR "}.get(g["combine"], ", ")
        head = "When " if g["combine"] != "k_of_n" else f"When at least {g['k']} of: "
        out.append(
            f"Rule '{g['label']}': {head}{joiner.join(conds)}, hold {pct(g['when_true'])} of the normal "
            f"{', '.join(g['apply_to'])} share; otherwise hold {pct(g['when_false'])}"
            + (" (assumed met until there is enough history)" if g["assume_when_unknown"] else "")
            + "."
        )
    ex = s["exits"]
    if "trailing_stop" in ex:
        ts = ex["trailing_stop"]
        out.append(
            f"Trailing stop: sells an asset when its close is {pct(float(ts['pct']))} below its highest "
            f"close since it was bought, then waits {int(ts.get('cooldown_days', 21))} days before "
            "re-entering."
        )
    if "stop_target" in ex:
        stg = ex["stop_target"]
        unit = stg.get("unit", "atr")

        def lvl(v):
            return f"{float(v):g} x the {int(stg.get('atr_window', 14))}-day ATR" if unit == "atr" else pct(float(v))

        bits = []
        if stg.get("stop") is not None:
            bits.append(f"sells an asset when its close falls {lvl(stg['stop'])} below the close it was bought on")
        if stg.get("target") is not None:
            bits.append(f"takes profit when its close rises {lvl(stg['target'])} above it")
        out.append(
            "Stop-loss / take-profit: "
            + "; ".join(bits)
            + f"; then waits {int(stg.get('cooldown_days', 10))} days before buying again if the rules still want it."
        )
    if "account_drawdown" in ex:
        ad = ex["account_drawdown"]
        out.append(
            f"Account brake: if the account falls {pct(float(ad['trigger']))} below its peak, all "
            f"targets are multiplied by {float(ad['scale']):g} until the fall is back under "
            f"{pct(float(ad['release']))}."
        )
    exe = s["execution"]
    out.append(
        f"Orders are decided on completed daily closes and fill at the next day's {exe['fill']}; costs "
        + ", ".join(f"{t} {v * exe['cost_mult']:g} bps" for t, v in exe["costs_bps"].items())
        + " per trade; cash earns the 3-month T-bill rate; no borrowing."
    )
    return out


def load_prices(tickers: list[str], start: str, cfg: dict = CFG) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    """Daily OHLCV for each ticker from `start` (cached); returns (prices, errors)."""
    prices, errors = {}, {}
    for t in tickers:
        try:
            prices[t] = data.daily_prices_from(t, start, cfg)
        except Exception as exc:  # network or data problems are shown, never hidden
            errors[t] = str(exc)
    return prices, errors


def gbp_usd(start: str, cfg: dict = CFG) -> pd.Series | None:
    """US dollars per pound on each day (Yahoo GBPUSD=X), or None offline / unavailable."""
    if cfg.get("offline"):
        return None
    try:
        return data.daily_prices_from("GBPUSD=X", start, cfg)["Close"]
    except Exception:
        return None


def freshness(prices: dict[str, pd.DataFrame], cfg: dict = CFG, now: datetime | None = None) -> pd.DataFrame:
    rows = []
    max_age = cfg["data"].get("max_stale_days", 4)
    for t, p in prices.items():
        if cfg.get("offline"):
            label = "SYNTHETIC (offline test data, not real prices)"
        else:
            age = data.staleness_days(p, now)
            label = f"EOD: completed daily bars, last {p.index[-1].date()}" + (
                f" (STALE: {age} days old, no trading)" if age > max_age else ""
            )
        rows.append(
            {"asset": t, "rows": len(p), "first": p.index[0].date(), "last": p.index[-1].date(), "status": label}
        )
    return pd.DataFrame(rows)


def data_label(prices: dict[str, pd.DataFrame], cfg: dict = CFG) -> str:
    if cfg.get("offline"):
        return "SYNTHETIC test data (offline mode): not real prices"
    last = min(p.index[-1] for p in prices.values())
    return (
        f"Yahoo Finance adjusted daily data (EOD), completed bars to {last.date()}; historical backtest, net of costs"
    )


# ---------------------------------------------------------------------------------------------------------------
# research lab
# ---------------------------------------------------------------------------------------------------------------
def sweepable(spec: dict) -> dict[str, tuple]:
    """label -> (path into the spec, current value, low, high, integer?)"""
    s = SP.normalise(spec)
    out = {}
    for t, w in s["base_weights"].items():
        out[f"{t} base weight"] = (("base_weights", t), w, 0.0, 1.0, False)
    out["Rebalance band"] = (("schedule", "band"), s["schedule"]["band"], 0.0, 0.2, False)
    if s["sizing"]["method"] != "fixed":
        out["Target volatility"] = (("sizing", "target_vol"), s["sizing"]["target_vol"], 0.05, 0.6, False)
        out["Volatility window"] = (("sizing", "vol_window"), s["sizing"]["vol_window"], 5, 252, True)
    for gi, g in enumerate(s["signals"]):
        for ci, c in enumerate(g["conditions"]):
            for side in ("left", "right"):
                o = c[side]
                if isinstance(o, float):
                    out[f"{g['label']}: threshold ({side})"] = (
                        ("signals", gi, "conditions", ci, side),
                        o,
                        o - abs(o) - 1,
                        o + abs(o) + 1,
                        False,
                    )
                else:
                    for p in INDICATORS[o["ind"]].params:
                        out[f"{g['label']}: {SP.operand_label(o)} {p.name}"] = (
                            ("signals", gi, "conditions", ci, side, p.name),
                            o[p.name],
                            p.lo,
                            p.hi,
                            p.integer,
                        )
    if "trailing_stop" in s["exits"]:
        out["Trailing stop %"] = (
            ("exits", "trailing_stop", "pct"),
            float(s["exits"]["trailing_stop"]["pct"]),
            0.02,
            0.5,
            False,
        )
    stg = s["exits"].get("stop_target")
    if stg:
        atr = stg.get("unit", "atr") == "atr"
        for k in ("stop", "target"):
            if stg.get(k) is not None:
                out[f"{k.title()} ({'ATR x' if atr else '%'})"] = (
                    ("exits", "stop_target", k),
                    float(stg[k]),
                    0.25 if atr else 0.01,
                    10.0 if atr else 0.9,
                    False,
                )
    return out


def set_path(spec: dict, path: tuple, value) -> dict:
    s = copy.deepcopy(SP.normalise(spec))
    node = s
    for k in path[:-1]:
        node = node[k]
    node[path[-1]] = value
    return s


def sweep(
    spec: dict, path: tuple, values: list, prices, rf, *, registry=None, progress=None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run the strategy once per value; statistics on the development period only (the holdout stays unseen).
    Returns (table, daily development returns per value)."""
    rows, rets = [], {}
    for k, v in enumerate(values):
        s = set_path(spec, path, v)
        # keep weights summing to <= 1 when sweeping a base weight in a two-asset strategy
        if path[0] == "base_weights" and len(s["universe"]) == 2:
            other = [t for t in s["universe"] if t != path[1]][0]
            s["base_weights"][other] = round(max(0.0, 1 - float(v)), 6)
        try:
            s = SP.validate(s)
        except SP.SpecError as exc:
            rows.append({"value": v, "error": str(exc)})
            continue
        r = E.run_spec(s, prices, rf)
        sm = E.summary(r, *DEV)
        rows.append(
            {
                "value": v,
                "sharpe": sm.get("sharpe"),
                "cagr": sm.get("cagr"),
                "max_drawdown": sm.get("max_drawdown"),
                "costs_per_year": sm.get("costs_per_year"),
            }
        )
        d = E.slice_daily(r.daily, *DEV)["ret"]
        rets[str(v)] = d
        if registry is not None:
            h = registry.register(s)
            ex = d - E.risk_free_daily(rf, d.index)
            registry.log_run(
                h,
                "lab",
                period="dev",
                sharpe_daily=float(ex.mean() / ex.std(ddof=1)) if ex.std(ddof=1) > 0 else None,
                metrics=sm,
            )
        if progress:
            progress(k + 1, len(values))
    return pd.DataFrame(rows), pd.DataFrame(rets)


# ---------------------------------------------------------------------------------------------------------------
# scanner
# ---------------------------------------------------------------------------------------------------------------
def scanner(spec: dict, prices: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Latest standard indicators for each asset, and whether each of the strategy's conditions would be met if it
    were applied to that asset (its own asset replaced by the scanned one). Completed daily bars only."""
    s = SP.normalise(spec)
    rows = []
    for t, p in prices.items():
        if len(p) < 30:
            continue
        c = p["Close"]
        row = {
            "asset": t,
            "what": UNIVERSE.get(t, ""),
            "last close": round(float(c.iloc[-1]), 2),
            "as of": p.index[-1].date(),
            "1-month return": float(c.iloc[-1] / c.iloc[-22] - 1) if len(c) > 22 else np.nan,
            "6-month return": float(c.iloc[-1] / c.iloc[-127] - 1) if len(c) > 127 else np.nan,
            "21-day volatility": float(compute("volatility", p, {"n": 21}).iloc[-1]),
            "RSI 14": float(compute("rsi", p, {"n": 14}).iloc[-1]),
            "above 200-day average": bool(c.iloc[-1] > c.rolling(200).mean().iloc[-1]) if len(c) > 200 else None,
            "fall from 1-year high": float(compute("drawdown", p, {"n": 252}).iloc[-1]),
        }
        for g in s["signals"]:
            states = []
            for cnd in g["conditions"]:
                vals = []
                for o in (cnd["left"], cnd["right"]):
                    if isinstance(o, float):
                        vals.append(o)
                    else:
                        params = {k: v for k, v in o.items() if k not in ("ind", "asset")}
                        vals.append(float(compute(o["ind"], p, params).iloc[-1]))
                l_, r_ = vals
                if not (np.isfinite(l_) and np.isfinite(r_)):
                    states.append(None)
                    continue
                op = cnd["op"]
                states.append({">": l_ > r_, "<": l_ < r_, ">=": l_ >= r_, "<=": l_ <= r_}.get(op, None))
            known = [x for x in states if x is not None]
            if g["combine"] == "all":
                met = all(known) if len(known) == len(states) else None
            elif g["combine"] == "any":
                met = any(known) if known else None
            else:
                met = sum(known) >= g["k"] if known else None
            row[f"rule: {g['label']}"] = met
        rows.append(row)
    return pd.DataFrame(rows)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
