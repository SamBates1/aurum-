"""Feature engineering. Every feature at date t uses only data up to the close of t.
tests/test_lookahead.py checks this by truncating the data and comparing."""

import numpy as np
import pandas as pd


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / down.replace(0, np.nan))


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    line = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
    return line, line.ewm(span=signal, adjust=False).mean()


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prev = df["Close"].shift(1)
    tr = pd.concat([df["High"] - df["Low"], (df["High"] - prev).abs(), (df["Low"] - prev).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def technical_features(df: pd.DataFrame) -> pd.DataFrame:
    c, v = df["Close"], df["Volume"]
    f = pd.DataFrame(index=df.index)
    for n in (1, 5, 21, 63):
        f[f"ret_{n}"] = c.pct_change(n)
    f["vol_21"] = c.pct_change().rolling(21).std() * np.sqrt(252)
    f["rsi_14"] = rsi(c)
    line, sig = macd(c)
    f["macd_hist"] = (line - sig) / c
    f["sma50_gap"] = c / c.rolling(50).mean() - 1
    f["sma200_gap"] = c / c.rolling(200).mean() - 1
    mid, sd = c.rolling(20).mean(), c.rolling(20).std()
    f["boll_z"] = (c - mid) / sd
    f["atr_pct"] = atr(df) / c
    f["volume_z"] = (v - v.rolling(21).mean()) / v.rolling(21).std()
    return f.replace([np.inf, -np.inf], np.nan)


def macro_features(macro: pd.DataFrame) -> pd.DataFrame:
    m = macro.ffill()
    f = pd.DataFrame(index=m.index)
    for col in m.columns:
        if col in CROSS_ASSET or col == "dxy":
            continue  # handled by cross_asset_features
        f[f"{col}_chg5"] = m[col].diff(5)
        f[f"{col}_chg21"] = m[col].diff(21)
    if "dxy" in m:  # an index level: use % change, not points
        f["dxy_chg5"], f["dxy_chg21"] = m["dxy"].pct_change(5), m["dxy"].pct_change(21)
    if "vix" in m:
        f["vix_level"] = m["vix"]
    if "real_yield_10y" in m:
        f["real_yield_level"] = m["real_yield_10y"]
    return f


# Price series used as cross-asset drivers (hypotheses, kept only if ablation shows value):
#   gold: miners are leveraged to the gold price; spx: miners are equities with market beta;
#   oil: energy is a large share of mining costs.
CROSS_ASSET = ("gold", "spx", "oil")


def cross_asset_features(macro: pd.DataFrame, asset_close: pd.Series) -> pd.DataFrame:
    m = macro.ffill()
    f = pd.DataFrame(index=asset_close.index)
    for col in CROSS_ASSET:
        if col not in m:
            continue
        s = align(m[[col]], asset_close.index)[col]
        f[f"{col}_ret21"] = s.pct_change(21, fill_method=None)
        if col == "gold":
            # relative strength vs gold: is the asset out- or under-performing its driver?
            f["rel_gold_ret21"] = asset_close.pct_change(21, fill_method=None) - f["gold_ret21"]
    return f


def align(macro_feats: pd.DataFrame, index: pd.DatetimeIndex) -> pd.DataFrame:
    """Forward-fill data onto the asset's trading calendar: each date gets the
    latest value known on or before it, never a later one."""
    union = macro_feats.index.union(index)
    return macro_feats.reindex(union).ffill().reindex(index)


def build_dataset(prices: pd.DataFrame, macro: pd.DataFrame | None, horizon: int, threshold: float = 0.0):
    """Returns (X, y, fwd_ret, groups).

    X[t] uses data up to the close of t. y[t] = 1 if Close[t+horizon] > Close[t]*(1+threshold),
    NaN for the last `horizon` rows. groups maps feature family -> column names (for ablation).
    """
    tech = technical_features(prices)
    parts, groups = [tech], {"technical": list(tech.columns)}
    if macro is not None and not macro.empty:
        mac = align(macro_features(macro), prices.index)
        cross = cross_asset_features(macro, prices["Close"])
        parts += [mac, cross]
        groups["macro"] = list(mac.columns)
        groups["cross_asset"] = list(cross.columns)
    X = pd.concat(parts, axis=1)
    fwd = prices["Close"].shift(-horizon) / prices["Close"] - 1
    y = (fwd > threshold).astype(float).where(fwd.notna())
    return X, y, fwd, groups


def triple_barrier_labels(
    prices: pd.DataFrame, atr_series: pd.Series, pt_mult: float = 2.0, sl_mult: float = 2.0, horizon: int = 20
) -> pd.Series:
    """Triple-barrier labels (Lopez de Prado, *Advances in Financial Machine Learning*, ch. 3).

    For a decision at the close of day t: upper barrier = Close[t] + pt_mult*ATR[t],
    lower = Close[t] - sl_mult*ATR[t], vertical = t + horizon trading days. Label 1 if the
    upper barrier is touched first (by a later High), 0 if the lower is touched first or
    the vertical barrier ends with a loss. If both are touched on the same day the lower
    one is assumed first (pessimistic). The last `horizon` labels are NaN: unknown yet.
    Labels mirror the trade the strategy would actually hold, which is what the trade-plan
    idea (entry, stop, target, maximum holding period) needs.
    """
    c, h, lo = prices["Close"].to_numpy(float), prices["High"].to_numpy(float), prices["Low"].to_numpy(float)
    a = atr_series.reindex(prices.index).to_numpy(float)
    n = len(c)
    out = np.full(n, np.nan)
    for t in range(n - horizon):
        if not np.isfinite(a[t]) or a[t] <= 0:
            continue
        up, dn = c[t] + pt_mult * a[t], c[t] - sl_mult * a[t]
        label = float(c[t + horizon] > c[t])
        for k in range(t + 1, t + horizon + 1):
            if lo[k] <= dn:
                label = 0.0
                break
            if h[k] >= up:
                label = 1.0
                break
        out[t] = label
    return pd.Series(out, index=prices.index, name="tb_label")
