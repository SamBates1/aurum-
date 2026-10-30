"""Strategy definitions (master build prompt: one configuration shared by backtest, designer and paper trading).

A strategy is a plain dictionary (stored as YAML in strategies/) with these parts:

    id, name, version, description          identification; the version must be raised for any change in behaviour
    universe: [SPY, GLD]                     assets the strategy may hold
    base_weights: {SPY: 0.7, GLD: 0.3}       share of the account each asset gets before any rule (rest = cash)
    benchmark: SPY                           what the Fair Test compares against (a ticker or another strategy id)
    schedule:  rebalance: once | daily | weekly | monthly | quarterly | yearly
               band: 0.05                    trade an asset only when it is more than this (share of the account)
                                             away from its target; 0 = always trade back to target on schedule
               act_on_signal_change: false   also rebalance on the day a signal flips
    sizing:    method: fixed | vol_cap | inverse_vol
               target_vol: 0.20, vol_window: 21, max_weight: 1.0
    signals:   list of rules; each multiplies the base weight of the assets in apply_to:
               - id, label
                 conditions: [{left: {ind: close, asset: SPY}, op: ">", right: {ind: sma, asset: SPY, n: 200}}]
                     an operand is {ind: <indicator key>, asset: <ticker>, <params>} or a number;
                     op is one of > < >= <= crosses_above crosses_below
                 combine: all | any | k_of_n   (k: 2)
                 apply_to: [SPY]
                 when_true: 1.0, when_false: 0.0     multipliers on the base weight
                 assume_when_unknown: false          state used before an indicator has enough history
    exits:     trailing_stop: {pct: 0.15, cooldown_days: 21}          per asset, on closes
               stop_target: {unit: atr | pct, stop: 2.0, target: 4.0, atr_window: 14, cooldown_days: 10}
                   stop-loss / take-profit per asset, fixed at the entry close (ATR multiples or fractions);
                   either may be left out; acted on at the close that reaches it (fills at the next open)
               account_drawdown: {trigger: 0.20, release: 0.10, scale: 0.5}
    execution: fill: open | close, costs_bps: {SPY: 2, GLD: 3}, cost_mult: 1.0
    start: "2006-06-01"                     first date of data

`spec_hash` fingerprints everything that changes behaviour, so approvals and results are tied to an exact definition:
editing any rule gives a new hash and the old approval no longer applies.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import yaml

from .config import ROOT
from .indicators import INDICATORS

STRATEGY_DIR = ROOT / "strategies"
SCHEDULES = ("once", "daily", "weekly", "monthly", "quarterly", "yearly")
SIZING = ("fixed", "vol_cap", "inverse_vol")
OPS = (">", "<", ">=", "<=", "crosses_above", "crosses_below")
COMBINE = ("all", "any", "k_of_n")
BEHAVIOUR_KEYS = ("universe", "base_weights", "schedule", "sizing", "signals", "exits", "execution", "start")
DEFAULT_COSTS = {"SPY": 2, "QQQ": 2, "IWM": 3, "EFA": 3, "TLT": 3, "IEF": 3, "GLD": 3, "SLV": 5, "GDX": 5, "DBC": 8}
DEFAULT_START = "2006-06-01"


class SpecError(ValueError):
    pass


def normalise(spec: dict) -> dict:
    """Fill defaults so two definitions that behave the same look the same (and hash the same)."""
    s = copy.deepcopy(spec)
    s.setdefault("version", 1)
    s.setdefault("description", "")
    s["universe"] = [str(t).upper() for t in s.get("universe", [])]
    s["base_weights"] = {str(k).upper(): float(v) for k, v in s.get("base_weights", {}).items()}
    sch = s.setdefault("schedule", {})
    sch.setdefault("rebalance", "monthly")
    sch["band"] = float(sch.get("band", 0.0))
    sch["act_on_signal_change"] = bool(sch.get("act_on_signal_change", False))
    sz = s.setdefault("sizing", {})
    sz.setdefault("method", "fixed")
    sz["target_vol"] = float(sz.get("target_vol", 0.20))
    sz["vol_window"] = int(sz.get("vol_window", 21))
    sz["max_weight"] = float(sz.get("max_weight", 1.0))
    sigs = []
    for i, g in enumerate(s.get("signals") or []):
        g = dict(g)
        g.setdefault("id", f"signal_{i + 1}")
        g.setdefault("label", g["id"])
        g.setdefault("combine", "all")
        g["k"] = int(g.get("k", 1))
        g["apply_to"] = [str(t).upper() for t in g.get("apply_to", s["universe"])]
        g["when_true"] = float(g.get("when_true", 1.0))
        g["when_false"] = float(g.get("when_false", 0.0))
        g["assume_when_unknown"] = bool(g.get("assume_when_unknown", False))
        conds = []
        for c in g.get("conditions") or []:
            conds.append({"left": _operand(c.get("left")), "op": c.get("op", ">"), "right": _operand(c.get("right"))})
        g["conditions"] = conds
        sigs.append(g)
    s["signals"] = sigs
    ex = s.setdefault("exits", {}) or {}
    s["exits"] = {k: v for k, v in ex.items() if v}
    exe = s.setdefault("execution", {})
    exe.setdefault("fill", "open")
    exe["cost_mult"] = float(exe.get("cost_mult", 1.0))
    exe["costs_bps"] = {t: float(exe.get("costs_bps", {}).get(t, DEFAULT_COSTS.get(t, 10))) for t in s["universe"]}
    s["start"] = str(s.get("start", DEFAULT_START))
    s.setdefault("benchmark", "SPY")
    return s


def _operand(o):
    if o is None:
        return None
    if isinstance(o, (int, float)):
        return float(o)
    o = dict(o)
    o["ind"] = o.get("ind", "close")
    o["asset"] = str(o.get("asset", "")).upper()
    ind = INDICATORS.get(o["ind"])
    if ind is not None:
        for p in ind.params:
            v = o.get(p.name, p.default)
            o[p.name] = int(v) if p.integer else float(v)
    return o


def validate(spec: dict) -> dict:
    """Return the normalised definition, or raise SpecError with every problem found (in plain words)."""
    s = normalise(spec)
    errs = []
    if not s.get("id") or not str(s["id"]).replace("-", "").replace("_", "").isalnum():
        errs.append("id must be letters, digits, '-' or '_'")
    if not s.get("name"):
        errs.append("name is required")
    if not s["universe"]:
        errs.append("universe must list at least one asset")
    for t, w in s["base_weights"].items():
        if t not in s["universe"]:
            errs.append(f"base weight for {t}, which is not in the universe")
        if not 0 <= w <= 1:
            errs.append(f"base weight for {t} must be between 0 and 1")
    if sum(s["base_weights"].values()) > 1 + 1e-9:
        errs.append("base weights add up to more than 100% (borrowing is not allowed)")
    if s["schedule"]["rebalance"] not in SCHEDULES:
        errs.append(f"rebalance must be one of {', '.join(SCHEDULES)}")
    if not 0 <= s["schedule"]["band"] < 0.5:
        errs.append("band must be between 0 and 0.5")
    sz = s["sizing"]
    if sz["method"] not in SIZING:
        errs.append(f"sizing method must be one of {', '.join(SIZING)}")
    if not 0.01 <= sz["target_vol"] <= 1.0:
        errs.append("target volatility must be between 1% and 100%")
    if not 2 <= sz["vol_window"] <= 504:
        errs.append("volatility window must be between 2 and 504 days")
    if not 0 < sz["max_weight"] <= 1.0:
        errs.append("max weight per asset must be above 0 and at most 100%")
    for g in s["signals"]:
        if g["combine"] not in COMBINE:
            errs.append(f"{g['id']}: combine must be one of {', '.join(COMBINE)}")
        if not g["conditions"]:
            errs.append(f"{g['id']}: needs at least one condition")
        if g["combine"] == "k_of_n" and not 1 <= g["k"] <= max(1, len(g["conditions"])):
            errs.append(f"{g['id']}: k must be between 1 and the number of conditions")
        for t in g["apply_to"]:
            if t not in s["universe"]:
                errs.append(f"{g['id']}: applies to {t}, which is not in the universe")
        for m in ("when_true", "when_false"):
            if not 0 <= g[m] <= 1:
                errs.append(f"{g['id']}: {m} must be between 0 and 1 (no leverage)")
        for c in g["conditions"]:
            if c["op"] not in OPS:
                errs.append(f"{g['id']}: unknown comparison {c['op']!r}")
            for side in ("left", "right"):
                o = c[side]
                if o is None:
                    errs.append(f"{g['id']}: condition is missing its {side} side")
                elif isinstance(o, dict):
                    if o["ind"] not in INDICATORS:
                        errs.append(f"{g['id']}: unknown indicator {o['ind']!r}")
                    if not o["asset"]:
                        errs.append(f"{g['id']}: indicator {o['ind']} needs an asset")
                    for p in INDICATORS.get(o["ind"], INDICATORS["close"]).params:
                        if not p.lo <= o[p.name] <= p.hi:
                            errs.append(f"{g['id']}: {o['ind']} {p.name} must be between {p.lo:g} and {p.hi:g}")
            if isinstance(c["left"], float) and isinstance(c["right"], float):
                errs.append(f"{g['id']}: a condition must use at least one indicator")
    ex = s["exits"]
    if "trailing_stop" in ex:
        ts = ex["trailing_stop"]
        if not 0 < float(ts.get("pct", 0)) < 1:
            errs.append("trailing stop must be between 0% and 100%")
    if "stop_target" in ex:
        stg = ex["stop_target"] or {}
        unit = stg.get("unit", "atr")
        if unit not in ("atr", "pct"):
            errs.append("stop/target unit must be 'atr' or 'pct'")
        if stg.get("stop") is None and stg.get("target") is None:
            errs.append("stop/target exit needs a stop, a target or both")
        hi = 10.0 if unit == "atr" else 0.9
        for k in ("stop", "target"):
            v = stg.get(k)
            if v is not None and not 0 < float(v) <= hi:
                errs.append(
                    f"{k} must be above 0 and at most {hi:g} ({'ATR multiples' if unit == 'atr' else 'fraction'})"
                )
        if not 2 <= int(stg.get("atr_window", 14)) <= 100:
            errs.append("ATR window must be between 2 and 100 days")
        if not 0 <= int(stg.get("cooldown_days", 10)) <= 252:
            errs.append("cooldown must be between 0 and 252 days")
    if "account_drawdown" in ex:
        ad = ex["account_drawdown"]
        if not 0 < float(ad.get("release", 0)) <= float(ad.get("trigger", 0)) < 1:
            errs.append("account drawdown: need 0 < release <= trigger < 100%")
        if not 0 <= float(ad.get("scale", 0)) <= 1:
            errs.append("account drawdown: scale must be between 0 and 1")
    if s["execution"]["fill"] not in ("open", "close"):
        errs.append("fill must be 'open' (next day's open) or 'close' (next day's close)")
    if errs:
        raise SpecError("; ".join(errs))
    return s


def spec_hash(spec: dict) -> str:
    s = normalise(spec)
    core = {k: s.get(k) for k in BEHAVIOUR_KEYS}
    return hashlib.sha256(json.dumps(core, sort_keys=True, default=str).encode()).hexdigest()[:12]


def assets_needed(spec: dict) -> list[str]:
    """Universe plus any other asset a rule reads (e.g. a gold rule that looks at SPY)."""
    s = normalise(spec)
    out = list(s["universe"])
    for g in s["signals"]:
        for c in g["conditions"]:
            for o in (c["left"], c["right"]):
                if isinstance(o, dict) and o["asset"] and o["asset"] not in out:
                    out.append(o["asset"])
    return out


def load(path: str | Path) -> dict:
    with open(path) as fh:
        return validate(yaml.safe_load(fh))


def dump(spec: dict) -> str:
    return yaml.safe_dump(normalise(spec), sort_keys=False, allow_unicode=True)


def save(spec: dict, folder: Path | None = None) -> Path:
    s = validate(spec)
    folder = Path(folder or STRATEGY_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{s['id']}.yaml"
    path.write_text(dump(s))
    return path


def library(folder: Path | None = None) -> dict[str, dict]:
    """All saved strategies by id (invalid files are skipped and reported by `library_errors`)."""
    out = {}
    for p in sorted(Path(folder or STRATEGY_DIR).glob("*.yaml")):
        try:
            s = load(p)
            out[s["id"]] = s
        except Exception:
            continue
    return out


def library_errors(folder: Path | None = None) -> dict[str, str]:
    out = {}
    for p in sorted(Path(folder or STRATEGY_DIR).glob("*.yaml")):
        try:
            load(p)
        except Exception as exc:
            out[p.name] = str(exc)
    return out


def operand_label(o) -> str:
    if isinstance(o, float):
        return f"{o:g}"
    ind = INDICATORS[o["ind"]]
    return f"{o['asset']} {ind.describe(o)}"


def condition_label(c: dict) -> str:
    words = {"crosses_above": "crosses above", "crosses_below": "crosses below"}
    return f"{operand_label(c['left'])} {words.get(c['op'], c['op'])} {operand_label(c['right'])}"
