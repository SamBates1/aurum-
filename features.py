"""Feature engineering. Every feature at date t uses only data up to t.
tests/test_no_lookahead.py checks this by truncating the data."""
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
    return f


def macro_features(macro: pd.DataFrame) -> pd.DataFrame:
    m = macro.ffill()
    f = pd.DataFrame(index=m.index)
    for col in m.columns:
        f[f"{col}_chg5"] = m[col].diff(5)
        f[f"{col}_chg21"] = m[col].diff(21)
    if "vix" in m:
        f["vix_level"] = m["vix"]
    if "real_yield_10y" in m:
        f["real_yield_level"] = m["real_yield_10y"]
    return f


def align(macro_feats: pd.DataFrame, index: pd.DatetimeIndex) -> pd.DataFrame:
    """Forward-fill macro data onto the asset's trading calendar."""
    union = macro_feats.index.union(index)
    return macro_feats.reindex(union).ffill().reindex(index)


def build_dataset(prices: pd.DataFrame, macro: pd.DataFrame | None, horizon: int, threshold: float = 0.0):
    """Returns (X, y, fwd_ret). y is NaN for the last `horizon` rows (future unknown)."""
    X = technical_features(prices)
    if macro is not None and not macro.empty:
        X = X.join(align(macro_features(macro), prices.index))
    fwd = prices["Close"].shift(-horizon) / prices["Close"] - 1
    y = (fwd > threshold).astype(float).where(fwd.notna())
    return X, y, fwd
