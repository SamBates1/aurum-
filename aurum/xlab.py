"""Cross-asset research lab (master brief Parts C, E, H; EXP-037 onwards).

Shared definitions so every cross-asset experiment uses the same universe, dates, costs, accounting
(portfolio.simulate_portfolio: one account, next-open fills, T-bill on cash, no borrowing unless an
experiment explicitly models leverage and its financing cost) and periods:

    pre      start -> 2013-10-17     dev      2013-10-18 -> 2023-12-31     holdout  2024-01-01 ->

Every signal here is computed from data known at the close of the decision day.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import strategy as S
from .portfolio import simulate_portfolio
from .volatility import realised_21d

# Tradable universe for cross-asset tests (all US-listed ETFs/stocks with history from mid-2006 unless noted)
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
# One-way cost assumptions in bps (spread + slippage), fixed before any run; GLD/SLV/GDX as in config.yaml
COSTS = {"SPY": 2, "QQQ": 2, "IWM": 3, "EFA": 3, "TLT": 3, "IEF": 3, "GLD": 3, "SLV": 5, "GDX": 5, "DBC": 8}
START = "2006-06-01"
DEV_START, HOLD_START = pd.Timestamp("2013-10-18"), pd.Timestamp("2024-01-01")


def periods(first: pd.Timestamp) -> dict:
    return {
        "pre": (first, DEV_START - pd.Timedelta(days=1)),
        "dev": (max(first, DEV_START), HOLD_START - pd.Timedelta(days=1)),
        "holdout": (HOLD_START, None),
    }


def common_index(prices: dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
    idx = None
    for p in prices.values():
        idx = p.index if idx is None else idx.intersection(p.index)
    return idx.sort_values()


def run(
    prices,
    target,
    rf,
    *,
    costs=None,
    band=0.0,
    fill="open",
    cost_mult=1.0,
    overlay=None,
    leverage=1.0,
    financing_spread=0.0,
):
    """Simulate target weights (shares of equity). With leverage > 1 the targets are scaled up and the borrowed
    amount pays T-bill + financing_spread (annual), modelled as a daily charge on (gross exposure - 1)."""
    tick = list(target.columns)
    c = {t: (costs or COSTS).get(t, 10) * cost_mult for t in tick}
    if leverage == 1.0:
        return simulate_portfolio(
            {t: prices[t] for t in tick}, target, cost_bps=c, cash_rate=rf, band=band, fill=fill, overlay=overlay
        )
    # leveraged: simulate the unlevered target in a 1/leverage-scaled account, then lever returns, charging
    # financing on the borrowed fraction (an approximation of a margin account with daily rebalancing of debt)
    base = simulate_portfolio(
        {t: prices[t] for t in tick},
        target,
        cost_bps=c,
        cash_rate=rf,
        band=band,
        fill=fill,
        overlay=overlay,
    )
    d = base.daily.copy()
    r_cash = rf.reindex(d.index).ffill().fillna(0.0) if isinstance(rf, pd.Series) else pd.Series(rf, index=d.index)
    borrow = (r_cash + financing_spread) / 252
    gross = d["exposure"]
    # levered return = L * unlevered asset return part - financing on (L*exposure - 1)+, cash part unchanged
    asset_ret = d["ret"] - (1 - gross) * r_cash.shift(1).fillna(0) / 252
    lev_ret = leverage * asset_ret + (1 - np.minimum(1.0, leverage * gross)) * r_cash.shift(1).fillna(0) / 252
    lev_ret -= np.maximum(leverage * gross - 1.0, 0.0) * borrow.shift(1).fillna(0)
    d["ret"] = lev_ret
    d["value"] = (1 + lev_ret).cumprod()
    d["exposure"] = leverage * gross
    d["cost"] = d["cost"] * leverage  # costs scale with the levered trades (already inside L x asset_ret)
    base.daily = d
    return base


def vol_weights(prices: dict[str, pd.DataFrame], idx, target_vol=0.15, cap=1.0, vol=None) -> pd.DataFrame:
    """Aurum's per-asset rule: min(cap, target_vol / 21-day realised vol), per asset (sleeve units)."""
    out = {}
    for t, p in prices.items():
        v = realised_21d(p["Close"]) if vol is None else vol[t]
        out[t] = S.vol_target_weight(v.reindex(idx), target_vol, cap)
    return pd.DataFrame(out, index=idx)


def inverse_vol(prices, idx, window=63) -> pd.DataFrame:
    inv = pd.DataFrame(
        {
            t: 1 / (p["Close"].pct_change(fill_method=None).rolling(window).std() * np.sqrt(252))
            for t, p in prices.items()
        }
    ).reindex(idx)
    return inv.div(inv.sum(axis=1), axis=0)


def scale_to_vol(w: pd.DataFrame, prices, target=0.10, window=126, refit=21, cap=1.0) -> pd.DataFrame:
    """Scale a weight table so forecast portfolio volatility (rolling covariance) equals `target`, gross <= cap."""
    rets = pd.DataFrame({t: prices[t]["Close"].pct_change(fill_method=None) for t in w.columns}).reindex(w.index)
    out = pd.DataFrame(np.nan, index=w.index, columns=w.columns)
    cov = None
    for i in range(window, len(w)):
        if cov is None or (i - window) % refit == 0:
            cov = rets.iloc[i - window + 1 : i + 1].cov().to_numpy() * 252
        a = w.iloc[i].to_numpy(float)
        if not np.isfinite(a).all() or not np.isfinite(cov).all():
            continue
        pv = float(np.sqrt(max(a @ cov @ a, 1e-12)))
        out.iloc[i] = a * min(cap / max(a.sum(), 1e-12), target / pv)
    return out


def monthly(w: pd.DataFrame) -> pd.DataFrame:
    """Keep only the first trading day of each month (other rows NaN = no order)."""
    first = w.index.to_series().groupby([w.index.year, w.index.month]).transform("min") == w.index.to_series()
    return w.where(first, np.nan)


# ---------------------------------------------------------------------------
# signal families (EXP-038 ... EXP-041); each returns a 0/1 (or 0..1) exposure series on the asset's dates
# ---------------------------------------------------------------------------
def sma_cross(c: pd.Series, fast: int, slow: int) -> pd.Series:
    f, s = c.rolling(fast).mean(), c.rolling(slow).mean()
    return (f > s).astype(float).where(s.notna())


def ema_cross(c: pd.Series, fast: int, slow: int) -> pd.Series:
    f, s = c.ewm(span=fast, adjust=False).mean(), c.ewm(span=slow, adjust=False).mean()
    out = (f > s).astype(float)
    out.iloc[:slow] = np.nan
    return out


def above_sma(c: pd.Series, n: int) -> pd.Series:
    s = c.rolling(n).mean()
    return (c > s).astype(float).where(s.notna())


def tsmom(c: pd.Series, n: int) -> pd.Series:
    r = c / c.shift(n) - 1
    return (r > 0).astype(float).where(r.notna())


def donchian(c: pd.Series, entry: int = 50, exit_: int = 20) -> pd.Series:
    hi, lo = c.shift(1).rolling(entry).max(), c.shift(1).rolling(exit_).min()
    state, out = 0.0, np.full(len(c), np.nan)
    for i, (x, h, low) in enumerate(zip(c.to_numpy(), hi.to_numpy(), lo.to_numpy())):
        if not (np.isfinite(h) and np.isfinite(low)):
            continue
        if x > h:
            state = 1.0
        elif x < low:
            state = 0.0
        out[i] = state
    return pd.Series(out, index=c.index)


def multi_tf_trend(c: pd.Series) -> pd.Series:
    """Long only when 1-, 3- and 12-month returns are all positive (multi-timeframe confirmation)."""
    parts = [tsmom(c, n) for n in (21, 63, 252)]
    return (sum(parts) == 3).astype(float).where(pd.concat(parts, axis=1).notna().all(axis=1))


def rsi(c: pd.Series, n: int) -> pd.Series:
    d = c.diff()
    up, dn = (
        d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(),
        (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean(),
    )
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def state_machine(enter: pd.Series, exit_: pd.Series) -> pd.Series:
    state, out = 0.0, np.zeros(len(enter))
    for i, (e, x) in enumerate(zip(enter.fillna(False).to_numpy(bool), exit_.fillna(False).to_numpy(bool))):
        if state == 0 and e:
            state = 1.0
        elif state == 1 and x:
            state = 0.0
        out[i] = state
    return pd.Series(out, index=enter.index)


def rsi2_reversion(c: pd.Series) -> pd.Series:
    """Connors-style: buy when RSI(2) < 10 and price above its 200-day average; exit when RSI(2) > 70."""
    r = rsi(c, 2)
    return state_machine((r < 10) & (c > c.rolling(200).mean()), r > 70)


def bollinger_reversion(c: pd.Series) -> pd.Series:
    mid, sd = c.rolling(20).mean(), c.rolling(20).std()
    z = (c - mid) / sd
    return state_machine(z < -2, z > 0)


def zscore_reversion(c: pd.Series, n: int = 60) -> pd.Series:
    z = (np.log(c) - np.log(c).rolling(n).mean()) / np.log(c).rolling(n).std()
    return state_machine(z < -2, z > 0)


def extreme_drop(c: pd.Series) -> pd.Series:
    """Buy after a 5-day fall worse than 2 standard deviations; hold 5 days."""
    r5 = c.pct_change(5)
    sd = c.pct_change().rolling(252).std() * np.sqrt(5)
    trig = (r5 < -2 * sd).astype(int)
    hold = trig.rolling(5, min_periods=1).max()
    return hold.astype(float).where(sd.notna())


# ---------------------------------------------------------------------------
# volatility forecasts (EXP-040)
# ---------------------------------------------------------------------------
def _garch_h(x: np.ndarray, w: float, a: float, b: float) -> np.ndarray:
    """Conditional variances h_t = w + a x_{t-1}^2 + b h_{t-1} (h_0 from the sample variance), vectorised."""
    from scipy.signal import lfilter

    u = w + a * np.r_[np.var(x), x[:-1] ** 2]
    h0 = np.var(x)
    h, _ = lfilter([1.0], [1.0, -b], u, zi=[b * h0])
    return np.maximum(h, 1e-12)


def garch11(returns: pd.Series, min_obs: int = 756, refit: int = 63) -> pd.Series:
    """GARCH(1,1) forecast of next-day volatility (annualised) made at each close, Gaussian quasi-maximum
    likelihood fitted on the expanding window up to the decision date and refitted every `refit` days."""
    from scipy.optimize import minimize

    r = returns.fillna(0.0).to_numpy(float)
    n = len(r)
    out = np.full(n, np.nan)

    def nll(p, x):
        w, a, b = p
        if w <= 0 or a < 0 or b < 0 or a + b >= 0.999:
            return 1e10
        h = _garch_h(x, w, a, b)
        return 0.5 * np.sum(np.log(h) + x**2 / h)

    for t0 in range(min_obs, n, refit):
        x = r[: t0 + 1]  # data known at the close of day t0
        v = np.var(x)
        res = minimize(
            nll,
            x0=[v * 0.05, 0.08, 0.9],
            args=(x,),
            method="Nelder-Mead",
            options={"maxiter": 600, "xatol": 1e-9, "fatol": 1e-7},
        )
        w, a, b = res.x
        t1 = min(n, t0 + refit)
        seg = r[:t1]
        h = _garch_h(seg, w, a, b)
        nxt = w + a * seg**2 + b * h  # forecast for day t+1 made at the close of t
        out[t0:t1] = np.sqrt(nxt[t0:t1] * 252)
    return pd.Series(out, index=returns.index)


def qlike(forecast_var: pd.Series, realised_var: pd.Series) -> float:
    """QLIKE loss (Patton 2011): robust for comparing variance forecasts; lower is better."""
    f, r = forecast_var.align(realised_var, join="inner")
    m = f.notna() & r.notna() & (f > 0) & (r > 0)
    f, r = f[m], r[m]
    return float(np.mean(r / f - np.log(r / f) - 1))


# ---------------------------------------------------------------------------
# candlestick patterns (EXP-041): every pattern defined from OHLC, no visual judgement
# ---------------------------------------------------------------------------
def candle_patterns(p: pd.DataFrame) -> pd.DataFrame:
    o, h, lo, c = p["Open"], p["High"], p["Low"], p["Close"]
    body = (c - o).abs()
    rng = (h - lo).replace(0, np.nan)
    upper = h - np.maximum(o, c)
    lower = np.minimum(o, c) - lo
    atr = pd.concat([h - lo, (h - c.shift()).abs(), (lo - c.shift()).abs()], axis=1).max(axis=1).rolling(14).mean()
    down5 = c < c.shift(5)
    up5 = c > c.shift(5)
    bull = c > o
    bear = c < o
    po, pc, ph, pl = o.shift(), c.shift(), h.shift(), lo.shift()
    pbody = (pc - po).abs()
    f = pd.DataFrame(index=p.index)
    f["doji"] = body <= 0.1 * rng
    f["hammer"] = (lower >= 2 * body) & (upper <= 0.25 * rng) & down5
    f["hanging_man"] = (lower >= 2 * body) & (upper <= 0.25 * rng) & up5
    f["shooting_star"] = (upper >= 2 * body) & (lower <= 0.25 * rng) & up5
    f["bullish_engulfing"] = bull & (pc < po) & (o <= pc) & (c >= po) & (body > pbody)
    f["bearish_engulfing"] = bear & (pc > po) & (o >= pc) & (c <= po) & (body > pbody)
    f["inside_bar"] = (h < ph) & (lo > pl)
    f["outside_bar"] = (h > ph) & (lo < pl)
    f["bullish_pin_bar"] = (lower >= 0.6 * rng) & (body <= 0.25 * rng)
    f["bearish_pin_bar"] = (upper >= 0.6 * rng) & (body <= 0.25 * rng)
    # three-candle stars (body of the middle candle small, third closes past the first's midpoint)
    o2, c2 = o.shift(2), c.shift(2)
    small_mid = (c.shift() - o.shift()).abs() <= 0.3 * (c2 - o2).abs()
    f["morning_star"] = (c2 < o2) & small_mid & bull & (c > (o2 + c2) / 2) & down5.shift()
    f["evening_star"] = (c2 > o2) & small_mid & bear & (c < (o2 + c2) / 2) & up5.shift()
    f["gap_up"] = o > ph
    f["gap_down"] = o < pl
    f["wide_range_up"] = bull & ((h - lo) > 2 * atr)
    f["wide_range_down"] = bear & ((h - lo) > 2 * atr)
    f["breakout_20"] = c > h.shift().rolling(20).max()
    f["failed_breakout_20"] = (h > h.shift().rolling(20).max()) & (c < h.shift().rolling(20).max()) & bear
    return f.fillna(False).astype(bool)


BULLISH = {"hammer", "bullish_engulfing", "bullish_pin_bar", "morning_star", "gap_up", "wide_range_up", "breakout_20"}


def newey_west_t(y: np.ndarray, X: np.ndarray, lags: int) -> tuple[np.ndarray, np.ndarray]:
    """OLS coefficients and Newey-West (HAC) t-statistics: overlapping forward returns are autocorrelated."""
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    u = y - X @ beta
    Xu = X * u[:, None]
    S_ = Xu.T @ Xu
    for k in range(1, lags + 1):
        w = 1 - k / (lags + 1)
        G = Xu[k:].T @ Xu[:-k]
        S_ += w * (G + G.T)
    V = XtX_inv @ S_ @ XtX_inv
    se = np.sqrt(np.maximum(np.diag(V), 1e-30))
    return beta, beta / se


def benjamini_hochberg(p: np.ndarray, q: float = 0.10) -> np.ndarray:
    """Boolean mask of discoveries at false-discovery rate q."""
    p = np.asarray(p, float)
    n = len(p)
    order = np.argsort(p)
    thresh = q * (np.arange(1, n + 1) / n)
    passed = p[order] <= thresh
    k = np.max(np.where(passed)[0]) + 1 if passed.any() else 0
    mask = np.zeros(n, bool)
    mask[order[:k]] = True
    return mask


def norm_sf(x):
    from math import erfc, sqrt

    return np.array([0.5 * erfc(v / sqrt(2)) for v in np.atleast_1d(x)])


def engle_granger(y: pd.Series, x: pd.Series) -> dict:
    """Engle-Granger cointegration: OLS hedge ratio, ADF t-stat on residuals (no lags; approximate 5% critical
    value -3.34 for two series), and the mean-reversion half-life of the spread."""
    a, b = np.log(y).align(np.log(x), join="inner")
    m = a.notna() & b.notna()
    a, b = a[m].to_numpy(), b[m].to_numpy()
    X = np.column_stack([np.ones(len(b)), b])
    beta = np.linalg.lstsq(X, a, rcond=None)[0]
    e = a - X @ beta
    de, el = np.diff(e), e[:-1]
    Z = np.column_stack([np.ones(len(el)), el])
    g = np.linalg.lstsq(Z, de, rcond=None)[0]
    resid = de - Z @ g
    se = np.sqrt(resid.var(ddof=2) / np.sum((el - el.mean()) ** 2))
    t = g[1] / se
    half_life = -np.log(2) / g[1] if g[1] < 0 else np.inf
    return {
        "hedge_ratio": float(beta[1]),
        "adf_t": float(t),
        "cointegrated_5pct": bool(t < -3.34),
        "half_life_days": float(half_life),
    }
