"""Data layer: prices, macro, fundamentals and news.

Live sources: Yahoo Finance (via yfinance) and FRED (public CSV endpoint).
Set `offline: true` in config.yaml, or AURUM_OFFLINE=1, to use synthetic data.
"""
from datetime import datetime, timezone

import pandas as pd

from . import synthetic
from .config import CFG

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
OHLCV = ["Open", "High", "Low", "Close", "Volume"]


def _offline(cfg: dict) -> bool:
    return bool(cfg.get("offline"))


def _clean_yf(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    idx = pd.to_datetime(df.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)  # keep exchange-local wall time
    df.index = idx
    return df[OHLCV].dropna(subset=["Close"])


def daily_prices(ticker: str, start: str | None = None, cfg: dict = CFG) -> pd.DataFrame:
    """Daily OHLCV, split/dividend adjusted. During market hours the last row
    is today's partial bar, so signals update intraday."""
    start = start or cfg["backtest"]["start"]
    if _offline(cfg):
        return synthetic.daily_prices(ticker, start)
    import yfinance as yf
    df = yf.download(ticker, start=start, auto_adjust=True, progress=False)
    if df is None or df.empty:
        raise ValueError(f"No price data returned for {ticker}")
    return _clean_yf(df)


def intraday_prices(ticker: str, interval: str | None = None, cfg: dict = CFG) -> pd.DataFrame:
    interval = interval or cfg["live"]["interval"]
    if _offline(cfg):
        return synthetic.intraday_prices(ticker, interval)
    import yfinance as yf
    df = yf.download(ticker, period="5d", interval=interval, auto_adjust=True, progress=False)
    if df is None or df.empty:
        raise ValueError(f"No intraday data returned for {ticker}")
    df = _clean_yf(df)
    return df


def _fred_series(series_id: str) -> pd.Series:
    raw = pd.read_csv(FRED_CSV.format(series=series_id))
    date_col, value_col = raw.columns[0], raw.columns[-1]
    s = pd.to_numeric(raw[value_col], errors="coerce")
    s.index = pd.to_datetime(raw[date_col])
    return s.dropna()


def macro_daily(cfg: dict = CFG) -> pd.DataFrame:
    """Macro drivers of gold as a daily DataFrame, one column per series.

    FRED series are lagged one day: they are published after the close, so
    using the same-day value would leak information the bot couldn't have had.
    """
    yahoo_map = cfg["macro"]["yahoo"]
    fred_map = cfg["macro"]["fred"]
    if _offline(cfg):
        df = synthetic.macro(list(yahoo_map) + list(fred_map))
        df[list(fred_map)] = df[list(fred_map)].shift(1)
        return df
    frames = {}
    for name, ticker in yahoo_map.items():
        try:
            frames[name] = daily_prices(ticker, cfg=cfg)["Close"]
        except Exception as exc:  # one missing series shouldn't kill the bot
            print(f"[aurum] macro {name} ({ticker}) unavailable: {exc}")
    for name, series_id in fred_map.items():
        try:
            frames[name] = _fred_series(series_id).shift(1)
        except Exception as exc:
            print(f"[aurum] FRED {series_id} unavailable: {exc}")
    df = pd.DataFrame(frames).sort_index()
    return df.loc[cfg["backtest"]["start"]:]


FUNDAMENTAL_KEYS = ["forwardPE", "trailingPE", "priceToBook", "profitMargins",
                    "debtToEquity", "freeCashflow", "marketCap", "dividendYield"]


def fundamentals(ticker: str, cfg: dict = CFG) -> dict:
    """Current fundamentals snapshot. Not point-in-time, so it is used only for
    today's decision, never in the backtest (that would be lookahead bias)."""
    if _offline(cfg):
        return synthetic.fundamentals(ticker)
    import yfinance as yf
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception:
        return {}
    return {k: info[k] for k in FUNDAMENTAL_KEYS if info.get(k) is not None}


def news(ticker: str, cfg: dict = CFG) -> list[dict]:
    """Recent headlines as dicts: title, publisher, link, published (datetime)."""
    if _offline(cfg):
        return synthetic.news(ticker)
    import yfinance as yf
    try:
        items = yf.Ticker(ticker).news or []
    except Exception:
        return []
    out = []
    for item in items:
        c = item.get("content", item)  # yfinance changed its news format in 2025
        title = c.get("title")
        if not title:
            continue
        published = c.get("pubDate") or c.get("providerPublishTime")
        if isinstance(published, (int, float)):
            published = datetime.fromtimestamp(published, tz=timezone.utc)
        elif published:
            published = pd.Timestamp(published).to_pydatetime()
        provider = c.get("provider") or {}
        link = (c.get("canonicalUrl") or {}).get("url") or c.get("link", "")
        out.append({"title": title,
                    "publisher": (provider.get("displayName") if isinstance(provider, dict) else None)
                                 or c.get("publisher", ""),
                    "link": link, "published": published})
    return out
