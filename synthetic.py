"""Synthetic market data so the whole pipeline runs offline (demos, tests, CI).

Prices follow a regime-switching random walk with a weak, *genuine* link to a
synthetic real-yield series, so the ML model has something real (but small)
to find. Nothing here resembles actual market history.
"""
import zlib
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


def _rng(name: str) -> np.random.Generator:
    return np.random.default_rng(zlib.crc32(name.encode()))


def _dates(start: str | None) -> pd.DatetimeIndex:
    end = pd.Timestamp.today().normalize()
    return pd.bdate_range(start or "2010-01-01", end)


def _real_yield(dates: pd.DatetimeIndex) -> pd.Series:
    rng = _rng("real_yield")
    steps = rng.normal(0, 0.03, len(dates))
    level = 0.5 + np.cumsum(steps) * 0.3
    return pd.Series(level, index=dates)


def daily_prices(ticker: str, start: str | None = None) -> pd.DataFrame:
    dates = _dates("2010-01-01")
    rng = _rng(ticker)
    n = len(dates)
    ry_change = _real_yield(dates).diff().fillna(0).to_numpy()
    regime_vol = np.where(rng.random(n) < 0.15, 0.02, 0.01)
    beta = -0.4 if ticker in ("GLD", "SLV") else -0.6
    drift = 0.0002
    # the past week's real-yield move feeds today's return: a weak, learnable
    # signal, so the offline demo can show the pipeline finding real structure
    ry_week = pd.Series(ry_change).rolling(5).sum().shift(1).fillna(0).to_numpy()
    rets = drift + beta * ry_week * 0.25 + rng.normal(0, 1, n) * regime_vol
    close = 100 * np.exp(np.cumsum(rets))
    spread = np.abs(rng.normal(0, 0.006, n))
    open_ = close * (1 + rng.normal(0, 0.003, n))
    high = np.maximum(open_, close) * (1 + spread)
    low = np.minimum(open_, close) * (1 - spread)
    vol = rng.lognormal(15, 0.3, n)
    df = pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol}, index=dates)
    return df.loc[pd.Timestamp(start or "2010-01-01"):]


def intraday_prices(ticker: str, interval: str = "5m") -> pd.DataFrame:
    last = daily_prices(ticker).Close.iloc[-1]
    rng = _rng(ticker + datetime.now().strftime("%Y%m%d%H"))
    idx = pd.date_range(end=datetime.now().replace(second=0, microsecond=0), periods=78, freq="5min")
    close = last * np.exp(np.cumsum(rng.normal(0, 0.001, len(idx))))
    df = pd.DataFrame({"Open": close, "High": close * 1.001, "Low": close * 0.999, "Close": close,
                       "Volume": rng.lognormal(12, 0.3, len(idx))}, index=idx)
    return df


def macro(names: list[str]) -> pd.DataFrame:
    dates = _dates("2010-01-01")
    out = {}
    for name in names:
        if name == "real_yield_10y":
            out[name] = _real_yield(dates)
        else:
            rng = _rng(name)
            base = {"dxy": 95, "us10y": 2.5, "vix": 18, "breakeven_10y": 2.2}.get(name, 1.0)
            scale = {"dxy": 0.3, "us10y": 0.04, "vix": 0.8, "breakeven_10y": 0.02}.get(name, 0.01)
            walk = np.cumsum(rng.normal(0, scale, len(dates)))
            series = base + walk - np.linspace(0, walk[-1], len(dates)) * 0.9  # keep it bounded-ish
            if name == "vix":
                series = np.clip(series, 9, 80)
            out[name] = series
    return pd.DataFrame(out, index=dates)


def fundamentals(ticker: str) -> dict:
    rng = _rng("fund" + ticker)
    return {
        "forwardPE": float(rng.uniform(8, 35)),
        "priceToBook": float(rng.uniform(0.8, 4)),
        "profitMargins": float(rng.uniform(-0.05, 0.35)),
        "debtToEquity": float(rng.uniform(5, 120)),
        "freeCashflow": float(rng.uniform(-2e8, 2e9)),
    }


_HEADLINES = [
    "{t} rallies as investors seek safe havens amid rate uncertainty",
    "{t} slips as strong dollar weighs on precious metals",
    "Analysts upgrade outlook for {t} on record production",
    "{t} falls after weaker-than-expected quarterly guidance",
    "Central bank gold buying supports {t}",
    "{t} steady ahead of Fed decision",
]


def news(ticker: str) -> list[dict]:
    rng = _rng("news" + ticker + datetime.now().strftime("%Y%m%d"))
    picks = rng.choice(len(_HEADLINES), size=4, replace=False)
    now = datetime.now()
    return [{"title": _HEADLINES[i].format(t=ticker), "publisher": "Synthetic Wire",
             "link": "", "published": now - timedelta(hours=int(h))}
            for i, h in zip(picks, rng.integers(1, 48, size=4))]
