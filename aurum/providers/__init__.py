"""Market-data providers behind one interface (live-charts plan, stage 1).

    from aurum.providers import get_provider
    p = get_provider()            # Alpaca when keys are set, else Yahoo (delayed), or synthetic offline
    bars = p.bars("AAPL", "15m")  # OHLCV DataFrame, UTC index, plus a "source" column per bar

Every bar says where it came from, so nothing delayed or partial is ever shown as live:
    SIP        consolidated data from all US exchanges (Alpaca history older than 15 minutes)
    IEX        real-time trades on the IEX exchange only (Alpaca free plan): prices close to the market for liquid
               stocks, volume = IEX trades only
    YAHOO      Yahoo Finance, delayed about 15 minutes
    SYNTHETIC  offline test data, not real prices

Keys are read from the environment (ALPACA_API_KEY, ALPACA_SECRET_KEY) or a private .env file in the project folder
(git-ignored). They never reach the browser, logs or reports.
"""

from __future__ import annotations

from .base import TIMEFRAMES, DataLabel, Provider, data_label, label_for
from .keys import alpaca_keys


def get_provider(cfg=None) -> Provider:
    from ..config import CFG

    cfg = cfg or CFG
    if cfg.get("offline"):
        from .synthetic import SyntheticProvider

        return SyntheticProvider()
    if alpaca_keys():
        from .alpaca import AlpacaProvider

        return AlpacaProvider()
    from .yahoo import YahooProvider

    return YahooProvider()


__all__ = ["TIMEFRAMES", "DataLabel", "Provider", "alpaca_keys", "data_label", "get_provider", "label_for"]
