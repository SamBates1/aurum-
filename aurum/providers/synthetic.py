"""Offline test provider: deterministic synthetic bars for every timeframe, labelled SYNTHETIC."""

from __future__ import annotations

import zlib

import numpy as np
import pandas as pd

from .base import TIMEFRAMES, Provider, finish

STEP = {"5m": "5min", "15m": "15min", "1h": "1h", "4h": "4h"}


class SyntheticProvider(Provider):
    name = "Synthetic (offline)"

    def __init__(self, now: pd.Timestamp | None = None):
        self.now = pd.Timestamp(now or pd.Timestamp.now(tz="UTC")).tz_convert("UTC")

    def bars(self, symbol, timeframe, start=None, end=None) -> pd.DataFrame:
        from .. import synthetic

        if timeframe in ("1d", "1w"):
            d = synthetic.daily_prices(symbol if symbol in ("SPY", "GLD", "SLV", "GDX") else symbol)
            d.index = d.index.tz_localize("UTC")
            d = d[d.index <= self.now]
            if timeframe == "1w":
                d = (
                    d.resample("W-FRI")
                    .agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"})
                    .dropna()
                )
            return finish(d, "SYNTHETIC")
        lookback = TIMEFRAMES[timeframe][1]
        idx = pd.date_range(self.now - lookback, self.now, freq=STEP[timeframe], tz="UTC")
        ny = idx.tz_convert("America/New_York")
        mins = ny.hour * 60 + ny.minute
        idx = idx[(ny.day_of_week < 5) & (mins >= 570) & (mins < 960)]
        rng = np.random.default_rng(zlib.crc32(f"{symbol}{timeframe}".encode()))
        r = rng.normal(0, 0.002, len(idx))
        c = 100 * np.exp(np.cumsum(r))
        o = np.r_[c[0], c[:-1]]
        hi = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.001, len(idx))))
        lo = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.001, len(idx))))
        df = pd.DataFrame(
            {"Open": o, "High": hi, "Low": lo, "Close": c, "Volume": rng.lognormal(10, 0.5, len(idx))}, index=idx
        )
        return finish(df, "SYNTHETIC")

    def news(self, symbols, limit=20):
        return [
            {
                "time": str(self.now),
                "headline": f"SYNTHETIC headline for {symbols[0]}",
                "summary": "Offline test data.",
                "source": "synthetic",
                "url": "",
                "symbols": symbols,
            }
        ]
