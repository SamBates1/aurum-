"""Long-term loss-limit lab (EXP-054): the long-term pot's rules with and without a loss limit on each holding.

One account, decisions at the close, fills at the next open, sells before buys, never borrows. Monthly: sell holdings
ranked below `exit_rank` (or no longer eligible), fill empty places with the best-ranked names. Daily (variants B, C):
sell a holding whose close is below its own level. Only the extra exit differs between variants.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

VARIANTS = ("A_none", "B_plan_level", "C_fixed_20pct")
MAX_POS, EXIT_RANK, COST = 12, 150, 0.0010


@dataclass
class Result:
    equity: pd.Series
    trades: list[dict] = field(default_factory=list)
    invested: float = 0.0


def momentum_rank(close: pd.DataFrame, volume: pd.DataFrame) -> pd.DataFrame:
    """1 = strongest 12-1 month momentum among stocks priced >= $10 with >= $20M traded a day; NaN = not eligible."""
    mom = close.shift(21) / close.shift(252) - 1
    ok = (close >= 10.0) & ((close * volume).rolling(20).mean() >= 20e6)
    return mom.where(ok).rank(axis=1, ascending=False)


def plan_level(high: pd.DataFrame, low: pd.DataFrame, close: pd.DataFrame) -> pd.DataFrame:
    """The long-term plan's invalidation level on each day (investplan.build): the lower of the 200-day average minus
    one ATR(14) and the close minus two ATR(14)."""
    prev = close.shift(1)
    tr = np.maximum(high - low, np.maximum((high - prev).abs(), (low - prev).abs()))
    atr = tr.rolling(14).mean()
    return np.minimum(close.rolling(200).mean() - atr, close - 2 * atr)


def simulate(
    open_: pd.DataFrame,
    close: pd.DataFrame,
    rank: pd.DataFrame,
    level: pd.DataFrame,
    variant: str,
    start: str,
    cash0: float = 50_000.0,
    max_pos: int = MAX_POS,
    exit_rank: int = EXIT_RANK,
    cost: float = COST,
) -> Result:
    idx = close.index[close.index >= pd.Timestamp(start)]
    months = pd.Series(idx, index=idx).groupby(idx.to_period("M")).min()
    decision_days = set(months.values)
    cash, pos = float(cash0), {}  # pos: symbol -> {shares, entry, level, bought}
    sells, buys = set(), []
    eq, trades, inv = [], [], 0.0
    for d in idx:
        o, c = open_.loc[d], close.loc[d]
        # fills at this open, decided at the previous close: sells first
        for s in sorted(sells):
            h = pos.pop(s)
            px = float(o[s]) if np.isfinite(o[s]) else h["last"]
            cash += h["shares"] * px * (1 - cost)
            trades.append({"symbol": s, "bought": h["bought"], "sold": d, "ret": px / h["entry"] - 1, "why": h["why"]})
        sells = set()
        if buys:
            value = cash + sum(h["shares"] * (float(o[s]) if np.isfinite(o[s]) else h["last"]) for s, h in pos.items())
            for s, lv in buys:
                px = float(o[s]) if np.isfinite(o[s]) else np.nan
                spend = min(value / max_pos, cash / (1 + cost))
                if s in pos or not np.isfinite(px) or px <= 0 or spend <= 0:
                    continue
                cash -= spend * (1 + cost)
                pos[s] = {"shares": spend / px, "entry": px, "level": lv, "bought": d, "last": px, "why": ""}
            buys = []
        # mark at the close
        for s, h in pos.items():
            if np.isfinite(c[s]):
                h["last"] = float(c[s])
        held_value = sum(h["shares"] * h["last"] for h in pos.values())
        eq.append(cash + held_value)
        inv += held_value / (cash + held_value) if cash + held_value > 0 else 0.0
        # the extra exit, judged on this close
        for s, h in pos.items():
            if variant == "B_plan_level" and np.isfinite(h["level"]) and h["last"] < h["level"]:
                sells.add(s)
                h["why"] = "loss limit"
            elif variant == "C_fixed_20pct" and h["last"] <= 0.8 * h["entry"]:
                sells.add(s)
                h["why"] = "loss limit"
        # the monthly check
        if d in decision_days:
            r = rank.loc[d]
            for s, h in pos.items():
                if s not in sells and not (np.isfinite(r[s]) and r[s] < exit_rank):
                    sells.add(s)
                    h["why"] = "rank"
            free = max_pos - (len(pos) - len(sells))
            best = [s for s in r.dropna().sort_values().index if s not in pos or s in sells]
            best = [s for s in best if s not in pos][:free]  # a name being sold today is not re-bought the same day
            buys = [(s, float(level.at[d, s]) if np.isfinite(level.at[d, s]) else np.nan) for s in best]
    return Result(pd.Series(eq, index=idx), trades, inv / max(1, len(idx)))


def stats(eq: pd.Series) -> dict:
    r = eq.pct_change().dropna()
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    return {
        "cagr": float((eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1) if years > 0 else np.nan,
        "max_dd": float((eq / eq.cummax() - 1).min()),
        "sharpe": float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else np.nan,
    }


def passes(a: dict, v: dict, a_h1: dict, v_h1: dict, a_h2: dict, v_h2: dict) -> bool:
    """The pre-registered rule: worst fall at least 20% smaller, growth no more than 1 point a year lower, and the
    worst fall not larger than the control's in either half."""
    return bool(
        v["max_dd"] >= 0.8 * a["max_dd"]
        and v["cagr"] >= a["cagr"] - 0.01
        and v_h1["max_dd"] >= a_h1["max_dd"] - 1e-12
        and v_h2["max_dd"] >= a_h2["max_dd"] - 1e-12
    )
