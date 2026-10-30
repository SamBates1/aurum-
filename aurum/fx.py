"""Pound / dollar conversion (platform phase 1). Every converted amount says which rate and date it used.

Source: Yahoo Finance GBPUSD=X daily closes (available the same evening), with FRED DEXUSUK (USD per GBP, Federal
Reserve H.10, published weekly so it lags) as a fallback. Offline mode returns a flat SYNTHETIC rate, labelled.
Platform currency-conversion fees are a separate cost (aurum/costs, phase 6), not part of the rate.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import data
from .config import CFG

SYNTHETIC_RATE = 1.30


@dataclass
class Rate:
    usd_per_gbp: float
    date: str
    source: str

    def to_gbp(self, usd: float) -> float:
        return usd / self.usd_per_gbp

    def to_usd(self, gbp: float) -> float:
        return gbp * self.usd_per_gbp

    @property
    def label(self) -> str:
        return f"£1 = ${self.usd_per_gbp:.4f} ({self.source}, {self.date})"


def history(cfg: dict = CFG) -> tuple[pd.Series, str]:
    """Daily USD per GBP, and where it came from."""
    if cfg.get("offline"):
        idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=2600)
        return pd.Series(SYNTHETIC_RATE, index=idx, name="usd_per_gbp"), "SYNTHETIC"
    try:
        p = data.daily_prices("GBPUSD=X", cfg)
        s = p["Close"].dropna()
        s = s[(s > 0.8) & (s < 3.0)]  # drop obviously broken prints
        if len(s):
            return s.rename("usd_per_gbp"), "Yahoo GBPUSD=X"
    except Exception as exc:  # fall back to the Fed's weekly-published series
        data.log_event("warning", "fx", f"Yahoo GBPUSD unavailable, using FRED DEXUSUK ({exc})")
    s = data.fred("DEXUSUK", cfg).dropna()
    return s.rename("usd_per_gbp"), "FRED DEXUSUK (published weekly)"


def rate(on=None, cfg: dict = CFG) -> Rate:
    """The rate known on `on` (default: latest): the last observation on or before that date."""
    s, src = history(cfg)
    if on is not None:
        s = s[s.index <= pd.Timestamp(on)]
    if not len(s):
        raise data.DataError("no GBP/USD rate available")
    return Rate(float(s.iloc[-1]), str(pd.Timestamp(s.index[-1]).date()), src)
