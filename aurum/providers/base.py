"""Common provider interface, timeframes and data labels."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd

# timeframe key -> (Alpaca name, default look-back, pandas resample rule for live aggregation)
TIMEFRAMES = {
    "5m": ("5Min", pd.Timedelta(days=10), "5min"),
    "15m": ("15Min", pd.Timedelta(days=30), "15min"),
    "1h": ("1Hour", pd.Timedelta(days=120), "1h"),
    "4h": ("4Hour", pd.Timedelta(days=400), "4h"),
    "1d": ("1Day", pd.Timedelta(days=365 * 10), "1D"),
    "1w": ("1Week", pd.Timedelta(days=365 * 20), "W"),
}
INTRADAY = ("5m", "15m", "1h", "4h")

SOURCE_TEXT = {
    "IEX": "IEX real-time (one exchange; volume = IEX trades only)",
    "SIP": "consolidated, all US exchanges (history older than 15 minutes)",
    "YAHOO": "Yahoo Finance, delayed about 15 minutes",
    "SYNTHETIC": "SYNTHETIC test data, not real prices",
}


@dataclass
class DataLabel:
    provider: str
    sources: list[str]
    last_bar: pd.Timestamp | None
    live: bool  # True only for IEX real-time with a recent trade
    text: str


def label_for(source: str) -> str:
    return SOURCE_TEXT.get(source, source)


def data_label(bars: pd.DataFrame, provider: str, last_trade_age_s: float | None = None) -> DataLabel:
    srcs = list(dict.fromkeys(bars["source"].tolist())) if len(bars) and "source" in bars else []
    last = bars.index[-1] if len(bars) else None
    live = "IEX" in srcs and last_trade_age_s is not None and last_trade_age_s < 120
    parts = [label_for(s) for s in srcs]
    if "IEX" in srcs and not live:
        parts.append("no IEX trade in the last 2 minutes" if last_trade_age_s is not None else "no live trade yet")
    text = "; ".join(parts) or "no data"
    if last is not None:
        text += f". Latest bar {pd.Timestamp(last).tz_convert('America/New_York'):%Y-%m-%d %H:%M} New York."
    return DataLabel(provider, srcs, last, live, text)


class Provider:
    name = "base"

    def bars(
        self, symbol: str, timeframe: str, start: datetime | None = None, end: datetime | None = None
    ) -> pd.DataFrame:
        raise NotImplementedError

    def news(self, symbols: list[str], limit: int = 20) -> list[dict]:
        return []

    def clock(self) -> dict:
        """{'is_open', 'next_open', 'next_close', 'timestamp'} (fallback: weekday 09:30-16:00 New York)."""
        t = pd.Timestamp(datetime.now(timezone.utc)).tz_convert("America/New_York")
        is_open = t.weekday() < 5 and (t.hour, t.minute) >= (9, 30) and t.hour < 16
        return {
            "is_open": is_open,
            "timestamp": t.isoformat(),
            "next_open": None,
            "next_close": None,
            "estimated": True,
        }


def finish(df: pd.DataFrame, source: str | pd.Series) -> pd.DataFrame:
    """Standard frame: UTC index named 'time', Open/High/Low/Close/Volume floats, a 'source' column, sorted, unique."""
    out = df[["Open", "High", "Low", "Close", "Volume"]].astype(float).copy()
    if out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    out.index.name = "time"
    out["source"] = source
    out = out[~out.index.duplicated(keep="last")].sort_index()
    return out[(out[["Open", "High", "Low", "Close"]] > 0).all(axis=1)]
