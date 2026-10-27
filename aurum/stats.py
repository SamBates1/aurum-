"""Uncertainty and robustness analysis.

Daily strategy returns are autocorrelated (positions last weeks, labels
overlap), so i.i.d. resampling understates uncertainty. We use the
stationary bootstrap (Politis & Romano, 1994): resample blocks of random
geometric length with mean `block`, preserving short-range dependence.

Nothing here is a formal significance test with multiple-testing correction;
intervals are reported as descriptive uncertainty, and the research report
says so.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .features import align

TRADING_DAYS = 252


def stationary_bootstrap_indices(n: int, block: float, reps: int, rng: np.random.Generator) -> np.ndarray:
    """reps x n matrix of resampled indices."""
    p = 1.0 / block
    idx = np.empty((reps, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, reps)
    new_block = rng.random((reps, n)) < p
    starts = rng.integers(0, n, (reps, n))
    for t in range(1, n):
        idx[:, t] = np.where(new_block[:, t], starts[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def sharpe(r: np.ndarray, axis=-1) -> np.ndarray:
    sd = r.std(axis=axis, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(sd > 0, r.mean(axis=axis) / sd * np.sqrt(TRADING_DAYS), np.nan)


def bootstrap_sharpe(
    excess: pd.Series, benchmark_excess: pd.Series | None = None, block: float = 21, reps: int = 1000, seed: int = 42
) -> dict:
    """Sharpe ratio with a 90% stationary-bootstrap interval; optionally the
    paired difference versus a benchmark over the same resampled days."""
    a = excess.dropna()
    if benchmark_excess is not None:
        a, b = a.align(benchmark_excess.dropna(), join="inner")
    if len(a) < 2 * block:
        return {}
    rng = np.random.default_rng(seed)
    idx = stationary_bootstrap_indices(len(a), block, reps, rng)
    sa = sharpe(a.to_numpy()[idx])
    out = {
        "sharpe": float(sharpe(a.to_numpy())),
        "sharpe_p05": float(np.nanpercentile(sa, 5)),
        "sharpe_p95": float(np.nanpercentile(sa, 95)),
    }
    if benchmark_excess is not None:
        sb = sharpe(b.to_numpy()[idx])
        diff = sa - sb
        out.update(
            {
                "sharpe_diff": float(sharpe(a.to_numpy()) - sharpe(b.to_numpy())),
                "diff_p05": float(np.nanpercentile(diff, 5)),
                "diff_p95": float(np.nanpercentile(diff, 95)),
                "share_resamples_better": float(np.nanmean(diff > 0)),
            }
        )
    return out


def yearly_returns(returns: dict[str, pd.Series]) -> pd.DataFrame:
    df = pd.DataFrame(returns)
    return (1 + df).groupby(df.index.year).prod() - 1


def regime_table(ret: dict[str, pd.Series], regimes: pd.Series) -> pd.DataFrame:
    """Annualised mean return of each strategy within each regime.
    `regimes` must be known at the start of each day (lag it before passing)."""
    df = pd.DataFrame(ret).join(regimes.rename("regime"), how="inner").dropna(subset=["regime"])
    g = df.groupby("regime")
    out = g.mean() * TRADING_DAYS
    out["days"] = g.size()
    return out


def make_regimes(close: pd.Series, macro: pd.DataFrame) -> dict[str, pd.Series]:
    """Regime labels known at the previous close (shifted one day)."""
    out = {}
    sma = close.rolling(200).mean()
    out["asset_trend"] = pd.Series(np.where(close > sma, "uptrend", "downtrend"), close.index).where(sma.notna())
    if "vix" in macro:
        v = align(macro[["vix"]], close.index)["vix"]
        out["volatility"] = pd.Series(
            np.select([v < 15, v > 25], ["calm (VIX<15)", "stressed (VIX>25)"], "normal"), close.index
        ).where(v.notna())
    if "real_yield_10y" in macro:
        ry = align(macro[["real_yield_10y"]], close.index)["real_yield_10y"].diff(63)
        out["real_yields"] = pd.Series(np.where(ry > 0, "rising", "falling"), close.index).where(ry.notna())
    return {k: v.shift(1) for k, v in out.items()}
