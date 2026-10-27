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


# ---------------------------------------------------------------------------
# Overfitting statistics (own implementations from the published formulas)
# ---------------------------------------------------------------------------
EULER_GAMMA = 0.5772156649015329


def _norm_cdf(x):
    from math import erf, sqrt

    return 0.5 * (1 + erf(x / sqrt(2)))


def _norm_ppf(p: float) -> float:
    from statistics import NormalDist

    return NormalDist().inv_cdf(p)


def probabilistic_sharpe(returns: pd.Series, sr_benchmark: float = 0.0) -> float:
    """Probabilistic Sharpe Ratio (Bailey & Lopez de Prado, 2012): the probability that
    the true per-period Sharpe exceeds `sr_benchmark`, allowing for sample length,
    skewness and fat tails. Inputs are per-period (daily), not annualised."""
    r = pd.Series(returns).dropna().to_numpy(float)
    n = len(r)
    if n < 30 or r.std(ddof=1) == 0:
        return float("nan")
    sr = r.mean() / r.std(ddof=1)
    z = (r - r.mean()) / r.std(ddof=0)
    skew, kurt = float(np.mean(z**3)), float(np.mean(z**4))  # kurt is non-excess (3 for normal)
    denom = 1 - skew * sr + (kurt - 1) / 4 * sr**2
    if denom <= 0:
        return float("nan")
    return float(_norm_cdf((sr - sr_benchmark) * np.sqrt(n - 1) / np.sqrt(denom)))


def expected_max_sharpe(n_trials: int, var_sharpe: float) -> float:
    """Expected maximum of n_trials Sharpe estimates when every true Sharpe is zero
    (False Strategy Theorem, Bailey & Lopez de Prado, 2014)."""
    if n_trials < 2 or var_sharpe <= 0:
        return 0.0
    return float(
        np.sqrt(var_sharpe)
        * ((1 - EULER_GAMMA) * _norm_ppf(1 - 1 / n_trials) + EULER_GAMMA * _norm_ppf(1 - 1 / (n_trials * np.e)))
    )


def deflated_sharpe(returns: pd.Series, trial_sharpes: list[float] | np.ndarray) -> float:
    """Deflated Sharpe Ratio: PSR against the Sharpe you would expect from the best of
    all the trials you ran by luck alone. `trial_sharpes` are per-period Sharpe ratios of
    every variant tried (including this one)."""
    s = np.asarray([x for x in trial_sharpes if np.isfinite(x)], float)
    if len(s) < 2:
        return probabilistic_sharpe(returns, 0.0)
    return probabilistic_sharpe(returns, expected_max_sharpe(len(s), float(s.var(ddof=1))))


def probability_of_backtest_overfitting(returns: pd.DataFrame, n_blocks: int = 16) -> dict:
    """PBO via combinatorially symmetric cross-validation (Bailey, Borwein, Lopez de Prado
    & Zhu, 2017). `returns`: one column per strategy variant, aligned daily returns.

    The sample is cut into n_blocks; for every way of choosing half the blocks as
    in-sample, the best in-sample variant's rank out-of-sample is recorded. PBO is the
    share of splits where that winner falls in the bottom half out of sample."""
    from itertools import combinations

    m = returns.dropna(how="any")
    t, n = m.shape
    if n < 2 or t < n_blocks * 20:
        return {"pbo": float("nan"), "n_splits": 0}
    blocks = np.array_split(np.arange(t), n_blocks)
    x = m.to_numpy(float)
    s1 = np.array([x[b].sum(axis=0) for b in blocks])
    s2 = np.array([(x[b] ** 2).sum(axis=0) for b in blocks])
    cnt = np.array([len(b) for b in blocks], float)

    def sharpe_of(sel):
        k = cnt[sel].sum()
        mu = s1[sel].sum(axis=0) / k
        var = s2[sel].sum(axis=0) / k - mu**2
        return mu / np.sqrt(np.where(var > 0, var, np.nan))

    logits = []
    for is_blocks in combinations(range(n_blocks), n_blocks // 2):
        is_sel = np.array(is_blocks)
        oos_sel = np.setdiff1d(np.arange(n_blocks), is_sel)
        sr_is, sr_oos = sharpe_of(is_sel), sharpe_of(oos_sel)
        best = int(np.nanargmax(sr_is))
        rank = (np.argsort(np.argsort(sr_oos)) + 1)[best]  # 1 = worst ... n = best
        w = rank / (n + 1)
        logits.append(np.log(w / (1 - w)))
    logits = np.array(logits)
    return {"pbo": float(np.mean(logits <= 0)), "n_splits": len(logits), "median_logit": float(np.median(logits))}
