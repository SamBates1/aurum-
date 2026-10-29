"""Indicator library for the Strategy Designer (master build prompt: rule builder and charts).

Every indicator is computed at the close of each day from data up to and including that day, so a rule evaluated on
day t uses only what was known at the close of t; the order it implies fills at the next open (same convention as
every Aurum backtest). `tests/test_engine.py` checks this by truncating the data and recomputing.

Each entry in INDICATORS says how to compute it, what its parameters are (with defaults and sensible bounds for the
designer's inputs) and how to draw it: kind "price" is drawn on the asset's price chart (same units as the price),
kind "panel" gets its own chart panel underneath.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

TRADING_DAYS = 252


@dataclass(frozen=True)
class Param:
    name: str
    default: float
    lo: float
    hi: float
    step: float = 1.0
    integer: bool = True


@dataclass(frozen=True)
class Indicator:
    key: str
    label: str  # format string using the parameter names, e.g. "SMA {n}"
    kind: str  # "price" (overlay on the price chart) or "panel" (own panel)
    params: tuple[Param, ...] = field(default_factory=tuple)
    description: str = ""
    unit: str = ""  # "%" for indicators returned as decimals that should be shown as percentages
    levels: tuple[float, ...] = ()  # reference lines worth drawing (e.g. RSI 30/70)

    def defaults(self) -> dict:
        return {p.name: (int(p.default) if p.integer else float(p.default)) for p in self.params}

    def describe(self, params: dict) -> str:
        vals = {**self.defaults(), **{k: v for k, v in params.items() if k in {p.name for p in self.params}}}
        out = self.label.format(**vals)
        return out


def _n(params, key, default):
    v = params.get(key, default)
    return int(v) if float(v).is_integer() else float(v)


def _rsi(c: pd.Series, n: int) -> pd.Series:
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = up / dn.where(dn > 0)
    out = 100 - 100 / (1 + rs)
    return out.where(dn > 0, 100.0).where(up.notna())


def _atr(p: pd.DataFrame, n: int) -> pd.Series:
    prev = p["Close"].shift(1)
    tr = pd.concat([p["High"] - p["Low"], (p["High"] - prev).abs(), (p["Low"] - prev).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def compute(key: str, p: pd.DataFrame, params: dict | None = None) -> pd.Series:
    """Value of indicator `key` on OHLCV frame `p` at each close (NaN until enough history)."""
    params = params or {}
    c = p["Close"].astype(float)
    if key == "close":
        return c
    if key == "sma":
        return c.rolling(_n(params, "n", 200)).mean()
    if key == "ema":
        n = _n(params, "n", 50)
        return c.ewm(span=n, adjust=False, min_periods=n).mean()
    if key == "bb_upper" or key == "bb_lower":
        n, k = _n(params, "n", 20), float(params.get("k", 2.0))
        m, s = c.rolling(n).mean(), c.rolling(n).std(ddof=0)
        return m + k * s if key == "bb_upper" else m - k * s
    if key == "donchian_high":
        return p["High"].rolling(_n(params, "n", 50)).max()
    if key == "donchian_low":
        return p["Low"].rolling(_n(params, "n", 20)).min()
    if key == "rsi":
        return _rsi(c, _n(params, "n", 14))
    if key == "momentum":  # n-day total return
        return c / c.shift(_n(params, "n", 126)) - 1
    if key == "volatility":  # annualised realised volatility of daily returns (n=21 equals volatility.realised_21d)
        return c.pct_change(fill_method=None).rolling(_n(params, "n", 21)).std() * np.sqrt(TRADING_DAYS)
    if key == "drawdown":  # fall from the highest close of the last n days
        return c / c.rolling(_n(params, "n", 252), min_periods=1).max() - 1
    if key == "zscore":
        n = _n(params, "n", 60)
        return (c - c.rolling(n).mean()) / c.rolling(n).std(ddof=1)
    if key == "macd_hist":
        f, s, g = _n(params, "fast", 12), _n(params, "slow", 26), _n(params, "signal", 9)
        line = c.ewm(span=f, adjust=False, min_periods=f).mean() - c.ewm(span=s, adjust=False, min_periods=s).mean()
        return line - line.ewm(span=g, adjust=False, min_periods=g).mean()
    if key == "atr_pct":
        return _atr(p, _n(params, "n", 14)) / c
    raise KeyError(f"unknown indicator {key!r}")


INDICATORS: dict[str, Indicator] = {
    i.key: i
    for i in (
        Indicator("close", "Close", "price", (), "The day's closing price."),
        Indicator("sma", "SMA {n}", "price", (Param("n", 200, 2, 400),), "Simple moving average of closes."),
        Indicator("ema", "EMA {n}", "price", (Param("n", 50, 2, 400),), "Exponential moving average of closes."),
        Indicator(
            "bb_upper",
            "Bollinger upper ({n}, {k})",
            "price",
            (Param("n", 20, 5, 200), Param("k", 2.0, 0.5, 4.0, 0.5, False)),
            "Moving average plus k standard deviations.",
        ),
        Indicator(
            "bb_lower",
            "Bollinger lower ({n}, {k})",
            "price",
            (Param("n", 20, 5, 200), Param("k", 2.0, 0.5, 4.0, 0.5, False)),
            "Moving average minus k standard deviations.",
        ),
        Indicator("donchian_high", "{n}-day high", "price", (Param("n", 50, 5, 400),), "Highest high of n days."),
        Indicator("donchian_low", "{n}-day low", "price", (Param("n", 20, 5, 400),), "Lowest low of n days."),
        Indicator(
            "rsi", "RSI {n}", "panel", (Param("n", 14, 2, 100),), "Relative strength index (0-100).", "", (30, 70)
        ),
        Indicator(
            "momentum", "{n}-day return", "panel", (Param("n", 126, 5, 400),), "Total return over n days.", "%", (0,)
        ),
        Indicator(
            "volatility",
            "{n}-day volatility",
            "panel",
            (Param("n", 21, 5, 252),),
            "Annualised realised volatility.",
            "%",
        ),
        Indicator(
            "drawdown",
            "Fall from {n}-day high",
            "panel",
            (Param("n", 252, 5, 1000),),
            "How far the close is below its n-day high.",
            "%",
            (0,),
        ),
        Indicator("zscore", "Z-score {n}", "panel", (Param("n", 60, 5, 400),), "Distance from mean in SDs.", "", (0,)),
        Indicator(
            "macd_hist",
            "MACD histogram ({fast}/{slow}/{signal})",
            "panel",
            (Param("fast", 12, 2, 100), Param("slow", 26, 5, 200), Param("signal", 9, 2, 50)),
            "MACD line minus its signal line.",
            "",
            (0,),
        ),
        Indicator("atr_pct", "ATR {n} (% of price)", "panel", (Param("n", 14, 2, 100),), "Average true range.", "%"),
    )
}
