"""Performance measurement for simulated strategies (see strategy.simulate).

Conventions
  * Daily returns, 252 trading days per year.
  * Risk-free rate = the 3-month T-bill (lagged, point-in-time), the same rate
    uninvested cash earns in the simulation.
  * Sharpe  = annualised mean excess return / annualised std of excess return.
  * Sortino = annualised mean excess return / annualised downside deviation,
    where downside deviation = sqrt(mean(min(excess, 0)^2)) over ALL days.
    (The previous version used the std of negative days only, which is not
    the textbook definition and overstates the ratio.)
  * Strategy and benchmark are always measured over identical dates.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .strategy import SimResult

TRADING_DAYS = 252


def _nan_if(cond, value):
    return np.nan if cond else float(value)


def risk_free_daily(rf: pd.Series | float, index: pd.DatetimeIndex) -> pd.Series:
    """Daily risk-free return earned on each day: yesterday's annual rate / 252,
    matching how the simulator accrues interest on cash."""
    if isinstance(rf, pd.Series):
        return rf.reindex(index).ffill().shift(1).fillna(0.0) / TRADING_DAYS
    return pd.Series(rf / TRADING_DAYS, index=index)


def performance(sim: SimResult, rf: pd.Series | float = 0.0) -> dict:
    with np.errstate(divide="ignore", invalid="ignore"):
        return _performance(sim, rf)


def _performance(sim: SimResult, rf: pd.Series | float = 0.0) -> dict:
    d = sim.daily
    r = d["ret"].astype(float)
    n = len(r)
    if n < 2:
        return {"days": n}
    rf_daily = risk_free_daily(rf, r.index)
    ex = r - rf_daily
    equity = (1 + r).cumprod()
    years = n / TRADING_DAYS
    total = equity.iloc[-1] - 1
    cagr = equity.iloc[-1] ** (1 / years) - 1 if equity.iloc[-1] > 0 else np.nan
    vol = r.std(ddof=1) * np.sqrt(TRADING_DAYS)
    ex_sd = ex.std(ddof=1)
    downside = np.sqrt(np.mean(np.minimum(ex, 0.0) ** 2))
    mdd = (equity / equity.cummax() - 1).min()
    t = sim.trades
    closed = t[t["exit_reason"] != "open"] if len(t) else t
    wins = closed[closed["pnl"] > 0] if len(closed) else closed
    losses = closed[closed["pnl"] <= 0] if len(closed) else closed
    avg_value = d["value"].mean()
    return {
        "days": n,
        "start": r.index[0].date(),
        "end": r.index[-1].date(),
        "total_return": total,
        "cagr": cagr,
        "volatility": vol,
        "sharpe": _nan_if(not np.isfinite(ex_sd) or ex_sd < 1e-10, ex.mean() / ex_sd * np.sqrt(TRADING_DAYS)),
        "sortino": _nan_if(downside < 1e-10, ex.mean() * TRADING_DAYS / (downside * np.sqrt(TRADING_DAYS))),
        "max_drawdown": mdd,
        "calmar": _nan_if(mdd == 0 or not np.isfinite(cagr), cagr / abs(mdd)),
        "time_in_market": float(d["invested"].mean()),  # portfolio: average share of sleeves invested
        "avg_exposure": float(d["exposure"].mean()),
        "trades": int(len(closed)),
        "win_rate": _nan_if(len(closed) == 0, len(wins) / max(1, len(closed))),
        "avg_win": _nan_if(len(wins) == 0, wins["ret"].mean() if len(wins) else np.nan),
        "avg_loss": _nan_if(len(losses) == 0, losses["ret"].mean() if len(losses) else np.nan),
        "avg_holding_days": _nan_if(len(closed) == 0, closed["days"].mean() if len(closed) else np.nan),
        "turnover_per_year": d["traded"].sum() / avg_value / years if avg_value > 0 else np.nan,
        "costs_per_year": d["cost"].sum() / avg_value / years if avg_value > 0 else np.nan,
    }


def relative(strategy: SimResult, benchmark: SimResult) -> dict:
    """Benchmark-relative statistics over the common dates."""
    with np.errstate(divide="ignore", invalid="ignore"):
        return _relative(strategy, benchmark)


def _relative(strategy: SimResult, benchmark: SimResult) -> dict:
    a, b = strategy.daily["ret"].align(benchmark.daily["ret"], join="inner")
    if len(a) < 2:
        return {}
    active = a - b
    te = active.std(ddof=1) * np.sqrt(TRADING_DAYS)
    var_b = b.var(ddof=1)
    return {
        "excess_return_ann": active.mean() * TRADING_DAYS,
        "tracking_error": te,
        "information_ratio": _nan_if(te == 0, active.mean() * TRADING_DAYS / te),
        "beta": _nan_if(var_b == 0, a.cov(b) / var_b),
        "correlation": a.corr(b),
    }


def slice_sim(sim: SimResult, start=None, end=None) -> SimResult:
    """Restrict to a date range, rebasing so returns are measured within it."""
    d = sim.daily.loc[start:end].copy()
    if len(d) and start is not None:
        d.iloc[0, d.columns.get_loc("ret")] = 0.0  # returns are measured from the slice start
    t = sim.trades
    if len(t):
        lo = pd.Timestamp(start) if start is not None else t["entry_date"].min()
        hi = pd.Timestamp(end) if end is not None else pd.Timestamp.max
        t = t[(t["entry_date"] >= lo) & (t["entry_date"] <= hi)]
    return SimResult(d, t)


def combine_sleeves(
    sims: dict[str, SimResult], weights: dict[str, float], cash_rate: pd.Series | float = 0.0
) -> SimResult:
    """Portfolio of independent sleeves plus any unallocated cash, over common dates."""
    idx = None
    for s in sims.values():
        idx = s.daily.index if idx is None else idx.intersection(s.daily.index)
    value = pd.Series(0.0, index=idx)
    invested = pd.Series(0.0, index=idx)
    expo = pd.Series(0.0, index=idx)
    cost = pd.Series(0.0, index=idx)
    traded = pd.Series(0.0, index=idx)
    for k, s in sims.items():
        d = s.daily.loc[idx]
        scale = weights[k] / d["value"].iloc[0]
        value += d["value"] * scale
        expo += d["exposure"] * d["value"] * scale
        cost += d["cost"] * scale
        traded += d["traded"] * scale
        invested += d["invested"] / len(sims)
    spare = 1.0 - sum(weights.values())
    if spare > 1e-12:
        rate = (
            cash_rate.reindex(idx).ffill().fillna(0.0)
            if isinstance(cash_rate, pd.Series)
            else pd.Series(cash_rate, index=idx)
        )
        value += spare * (1 + rate / TRADING_DAYS).cumprod().shift(1).fillna(1.0)
    daily = pd.DataFrame(
        {
            "value": value,
            "cash": np.nan,
            "shares": np.nan,
            "invested": invested,
            "exposure": expo / value,
            "cost": cost,
            "traded": traded,
        }
    )
    daily["ret"] = daily["value"].pct_change().fillna(0.0)
    trades = (
        pd.concat([s.trades.assign(ticker=k) for k, s in sims.items() if len(s.trades)], ignore_index=True)
        if any(len(s.trades) for s in sims.values())
        else pd.DataFrame(columns=["entry_value", "exit_reason", "pnl", "ret", "days"])
    )
    return SimResult(daily, trades)


def summary_table(results: dict[str, dict]) -> pd.DataFrame:
    return pd.DataFrame(results).T
