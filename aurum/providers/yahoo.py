"""Yahoo Finance fallback (no keys needed): about 15 minutes delayed, labelled YAHOO everywhere."""

from __future__ import annotations

import pandas as pd

from .base import Provider, finish

# Yahoo interval and the longest period it serves for it
YF = {
    "5m": ("5m", "60d"),
    "15m": ("15m", "60d"),
    "1h": ("60m", "730d"),
    "4h": ("60m", "730d"),
    "1d": ("1d", "max"),
    "1w": ("1wk", "max"),
}


class YahooProvider(Provider):
    name = "Yahoo (delayed)"

    def bars(self, symbol, timeframe, start=None, end=None) -> pd.DataFrame:
        from .. import data

        interval, period = YF[timeframe]
        df = data._yf_download(symbol, period=period, interval=interval)
        if timeframe == "4h":  # Yahoo has no 4-hour bars: built from hourly bars
            df = (
                df.resample("4h", origin="start_day", offset="9h30min")
                .agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"})
                .dropna()
            )
        out = finish(df, "YAHOO")
        if start is not None:
            out = out[
                out.index >= pd.Timestamp(start, tz="UTC")
                if pd.Timestamp(start).tzinfo is None
                else out.index >= pd.Timestamp(start)
            ]
        return out
