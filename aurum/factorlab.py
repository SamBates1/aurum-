"""Stock-factor lab (EXP-051): do cross-sectional stock signals beat holding every stock equally, after costs?

Inputs are wide panels (rows = trading days, columns = symbols) of open, high, low, close and volume, plus optional
point-in-time fundamental panels (value known on each day, e.g. ROIC). Every signal on a ranking day uses data up to
that day's close only; the chosen stocks are bought at the next open and held to the open after the next ranking day.

Long-term: monthly ranking, top fifth equal-weighted, one month. Swing: weekly (Friday) ranking, top fifth, held four
weeks as four overlapping cohorts of a quarter of the capital each. The benchmark holds every stock with data equally,
rebalanced on the same days with the same cost. Results: yearly extra return after costs, Newey-West t, both halves,
recent period, Benjamini-Hochberg across all signals (the EXP-051 pass rule).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .xlab import benjamini_hochberg, newey_west_t, norm_sf


@dataclass
class Panels:
    open: pd.DataFrame
    high: pd.DataFrame
    low: pd.DataFrame
    close: pd.DataFrame
    volume: pd.DataFrame
    fundamentals: dict[str, pd.DataFrame] | None = None  # name -> panel of point-in-time values


# ---------------------------------------------------------------------------------------------------------------
# signals: higher = more attractive; NaN = not ranked that day
# ---------------------------------------------------------------------------------------------------------------
def _rsi(c: pd.DataFrame, n: int) -> pd.DataFrame:
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + up / dn.where(dn > 0))


def _adx(p: Panels, n: int = 14) -> pd.DataFrame:
    h, lo, c = p.high, p.low, p.close
    up, dn = h.diff(), -lo.diff()
    plus = up.where((up > dn) & (up > 0), 0.0)
    minus = dn.where((dn > up) & (dn > 0), 0.0)
    prev = c.shift(1)
    tr = np.maximum(h - lo, np.maximum((h - prev).abs(), (lo - prev).abs()))
    w = {"alpha": 1 / n, "adjust": False, "min_periods": n}
    atr = tr.ewm(**w).mean()
    pdi = 100 * plus.ewm(**w).mean() / atr
    mdi = 100 * minus.ewm(**w).mean() / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi)
    return dx.ewm(**w).mean()


def long_term_signals(p: Panels) -> dict[str, pd.DataFrame]:
    c = p.close
    r = c.pct_change(fill_method=None)
    out = {
        "momentum": c.shift(21) / c.shift(252) - 1,
        "low_volatility": -r.rolling(252, min_periods=200).std(),
        "near_52w_high": c / c.rolling(252, min_periods=200).max(),
    }
    f = p.fundamentals or {}
    if "roic" in f:
        out["quality"] = f["roic"].reindex_like(c)
    if "fcf_yield" in f:
        out["value"] = f["fcf_yield"].reindex_like(c)
    if {"quality", "value"} <= set(out):
        ranks = [out[k].rank(axis=1, pct=True) for k in ("momentum", "quality", "value")]
        out["combined"] = sum(ranks) / 3
    return out


def swing_signals(p: Panels) -> dict[str, pd.DataFrame]:
    c, v = p.close, p.volume
    ret3m = c / c.shift(63) - 1
    breakout = (c >= c.rolling(20).max()) & (v > v.rolling(50).mean())
    pullback = (c > c.rolling(200).mean()) & (_rsi(c, 2) < 10)
    trend = (_adx(p) > 25) & (c > c.rolling(50).mean())
    return {
        "short_term_reversal": -(c / c.shift(21) - 1),
        "breakout": (c / c.rolling(20).max()).where(breakout),  # only names that broke out, ranked by closeness
        "pullback_in_uptrend": (-_rsi(c, 2)).where(pullback),
        "trend_strength": ret3m.where(trend),
    }


# ---------------------------------------------------------------------------------------------------------------
# portfolio test
# ---------------------------------------------------------------------------------------------------------------
def rank_days(index: pd.DatetimeIndex, how: str) -> pd.DatetimeIndex:
    s = pd.Series(index, index=index)
    key = s.dt.to_period("M") if how == "monthly" else s.dt.to_period("W-FRI")
    return pd.DatetimeIndex(s.groupby(key).max().values)


def top_fifth(sig: pd.Series, eligible: pd.Series, frac: float = 0.2, min_names: int = 10) -> list[str]:
    x = sig[eligible].dropna()
    if len(x) < min_names:
        return []
    n = max(1, int(round(len(x) * frac))) if len(x) * frac >= 1 else len(x)
    return list(x.sort_values(ascending=False).index[:n])


def _period_return(op: pd.DataFrame, a, b, names: list[str]) -> float:
    """Equal-weight open-to-open return from day a to day b (a missing open = the name dropped, return 0 for it)."""
    if not names:
        return 0.0
    r = op.loc[b, names] / op.loc[a, names] - 1
    return float(r.fillna(0.0).mean())


def backtest(
    p: Panels,
    signal: pd.DataFrame,
    how: str = "monthly",
    hold: int = 1,
    cost_bps: float = 10.0,
    start: str | None = None,
) -> pd.DataFrame:
    """Per period: strategy and benchmark returns after costs and their difference. `hold` = cohorts held at once
    (swing: 4 weekly cohorts of a quarter each)."""
    idx = p.close.index
    days = rank_days(idx, how)
    if start:
        days = days[days >= pd.Timestamp(start)]
    pos = idx.get_indexer(days)
    fills = idx[np.minimum(pos + 1, len(idx) - 1)]  # bought at the next open
    rows = []
    cohorts: list[list[str]] = []
    prev_all: list[str] = []
    for i in range(len(days) - 1):
        d, a, b = days[i], fills[i], fills[i + 1]
        elig = p.close.loc[d].notna() & p.open.loc[a].notna()
        picks = top_fifth(signal.loc[d], elig)
        everyone = list(elig[elig].index)
        old_w = _weights(cohorts, hold)
        cohorts = (cohorts + [picks])[-hold:]
        new_w = _weights(cohorts, hold)
        turn = sum(abs(new_w.get(k, 0) - old_w.get(k, 0)) for k in set(new_w) | set(old_w))
        bturn = len(set(everyone) ^ set(prev_all)) / max(len(everyone), 1)
        prev_all = everyone
        if not picks:
            continue
        strat = sum(_period_return(p.open, a, b, c) for c in cohorts) / hold if cohorts else 0.0
        bench = _period_return(p.open, a, b, everyone)
        rows.append(
            {
                "date": d,
                "strategy": strat - turn * cost_bps / 1e4,
                "benchmark": bench - bturn * cost_bps / 1e4,
                "turnover": turn,
                "names": len(picks),
            }
        )
    out = pd.DataFrame(rows).set_index("date") if rows else pd.DataFrame(columns=["strategy", "benchmark"])
    out["excess"] = out["strategy"] - out["benchmark"]
    return out


def _weights(cohorts: list[list[str]], hold: int) -> dict[str, float]:
    w: dict[str, float] = {}
    for c in cohorts:
        for k in c:
            w[k] = w.get(k, 0.0) + 1 / (hold * len(c))
    return w


def judge(res: pd.DataFrame, how: str, halves: tuple[str, str], recent: str, min_excess: float = 0.03) -> dict:
    """The EXP-051 statistics for one signal (the BH step is applied across signals in `verdicts`)."""
    per_year = 12 if how == "monthly" else 52
    lags = 3 if how == "monthly" else 4
    x = res["excess"].dropna()
    if len(x) < 24:
        return {"periods": len(x), "verdict": "NOT ENOUGH DATA"}
    _, t = newey_west_t(x.to_numpy(), np.ones((len(x), 1)), lags)
    t = float(t[0])
    split, end_first = pd.Timestamp(halves[1]), pd.Timestamp(halves[0])
    first, second = x[x.index <= end_first], x[x.index >= split]
    rec = x[x.index >= pd.Timestamp(recent)]
    out = {
        "periods": len(x),
        "excess_per_year": float(x.mean() * per_year),
        "t": t,
        "p": float(2 * np.asarray(norm_sf(abs(t))).ravel()[0]),
        "first_half": float(first.mean() * per_year) if len(first) else float("nan"),
        "second_half": float(second.mean() * per_year) if len(second) else float("nan"),
        "recent": float(rec.mean() * per_year) if len(rec) else float("nan"),
        "strategy_per_year": float(res["strategy"].mean() * per_year),
        "benchmark_per_year": float(res["benchmark"].mean() * per_year),
        "turnover": float(res["turnover"].mean()),
    }
    out["rule_ok"] = bool(
        out["excess_per_year"] >= min_excess
        and t >= 2.0
        and out["first_half"] > 0
        and out["second_half"] > 0
        and out["recent"] > 0
    )
    return out


def verdicts(stats: dict[str, dict], q: float = 0.10) -> dict[str, dict]:
    names = [k for k, s in stats.items() if "p" in s]
    if names:
        # one-sided: only a positive extra return counts as a discovery
        p = np.array([stats[k]["p"] / 2 if stats[k]["t"] > 0 else 1.0 for k in names])
        found = benjamini_hochberg(p, q)
        for k, f in zip(names, found):
            stats[k]["bh"] = bool(f)
            stats[k]["verdict"] = "PASS" if stats[k]["rule_ok"] and f else "FAIL"
    return stats
