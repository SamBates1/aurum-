"""Volatility forecasts for position sizing (EXP-017). All annualised, all point-in-time:
the value at date t uses only data up to the close of t.

    realised_21d   standard deviation of the last 21 daily returns (Aurum's current estimator)
    ewma           RiskMetrics exponentially weighted variance, lambda = 0.94
    har_parkinson  HAR model (Corsi 2009) on Parkinson high-low variance: tomorrow's average
                   variance over the next 21 days regressed on today's, the last week's and the last
                   month's average variance. Coefficients are refitted every 63 days on data whose
                   21-day-ahead target was already known (purged), so there is no look-ahead.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def realised_21d(close: pd.Series) -> pd.Series:
    return close.pct_change(fill_method=None).rolling(21).std() * np.sqrt(TRADING_DAYS)


def ewma(close: pd.Series, lam: float = 0.94, warmup: int = 63) -> pd.Series:
    r = close.pct_change(fill_method=None)
    var = (r**2).ewm(alpha=1 - lam, adjust=False).mean()
    out = np.sqrt(var * TRADING_DAYS)
    out.iloc[:warmup] = np.nan
    return out


def parkinson_variance(prices: pd.DataFrame) -> pd.Series:
    """Daily variance estimate from the high-low range (Parkinson 1980)."""
    hl = np.log(prices["High"] / prices["Low"]).replace([np.inf, -np.inf], np.nan)
    return hl**2 / (4 * np.log(2))


def har_parkinson(prices: pd.DataFrame, horizon: int = 21, refit_every: int = 63, min_obs: int = 504) -> pd.Series:
    rv = parkinson_variance(prices).clip(lower=1e-10)
    d, w, m = rv, rv.rolling(5).mean(), rv.rolling(22).mean()
    # target: mean squared close-to-close return over t+1..t+horizon. Using close-to-close (not
    # high-low) for the target calibrates the forecast to the risk actually held, including
    # overnight gaps that a high-low range misses.
    r2 = prices["Close"].pct_change(fill_method=None) ** 2
    target = r2[::-1].rolling(horizon).mean()[::-1].shift(-1)
    X = pd.concat([d, w, m], axis=1, keys=["d", "w", "m"])
    n = len(rv)
    out = np.full(n, np.nan)
    coef = None
    for t in range(n):
        if t >= min_obs + horizon and (coef is None or t % refit_every == 0):
            # training rows s with s + horizon <= t: their targets are fully observed by date t
            Xs, ys = X.iloc[: t - horizon + 1], target.iloc[: t - horizon + 1]
            ok = Xs.notna().all(axis=1) & ys.notna()
            if ok.sum() >= min_obs:
                A = np.column_stack([np.ones(ok.sum()), Xs[ok].to_numpy()])
                coef, *_ = np.linalg.lstsq(A, ys[ok].to_numpy(), rcond=None)
        if coef is not None and X.iloc[t].notna().all():
            f = coef[0] + X.iloc[t].to_numpy() @ coef[1:]
            out[t] = np.sqrt(max(f, 1e-10) * TRADING_DAYS)
    return pd.Series(out, index=prices.index, name="har_vol")


def gvz_adjusted(
    asset_vol: pd.Series, gvz: pd.Series, gold_vol: pd.Series, lo: float = 0.5, hi: float = 2.0
) -> pd.Series:
    """Scale an asset's realised volatility by gold's implied/realised ratio (GVZ / GLD 21-day vol):
    when options price more gold risk than has recently occurred, size every sleeve down."""
    ratio = (gvz / 100.0) / gold_vol.where(gold_vol > 0)
    return asset_vol * ratio.clip(lo, hi)
