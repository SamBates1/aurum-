"""Data layer: prices, macro, cash rate, fundamentals and news.

Sources: Yahoo Finance (via yfinance) and FRED (public CSV endpoint, no key).
Set `offline: true` in config.yaml, or AURUM_OFFLINE=1, to use synthetic data.

Design rules
  * Every download is validated (sorted unique dates, positive prices, no
    empty frames). Problems are logged loudly in DATA_EVENTS, never hidden.
  * Downloads are cached on disk with a metadata file recording source and
    retrieval time. A failed download falls back to the cache only with a
    visible warning; nothing is ever fabricated in live mode.
  * FRED values are shifted forward by `fred_lag_days` business days, because a
    value for date d is published after d's close. Using it on d is lookahead.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay

from . import synthetic
from .config import CFG, ROOT

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
OHLCV = ["Open", "High", "Low", "Close", "Volume"]
CACHE_DIR = ROOT / "data" / "cache"

DATA_EVENTS: list[dict] = []  # warnings and failures from this process, for reports and the dashboard


class DataError(RuntimeError):
    """Raised when required data is missing or unusable."""


def log_event(level: str, source: str, message: str) -> None:
    DATA_EVENTS.append(
        {
            "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "level": level,
            "source": source,
            "message": message,
        }
    )
    print(f"[aurum:{level}] {source}: {message}")


def _offline(cfg: dict) -> bool:
    return bool(cfg.get("offline"))


# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------
def validate_ohlcv(df: pd.DataFrame, name: str, min_rows: int = 1) -> pd.DataFrame:
    """Clean and sanity-check an OHLCV frame. Raises DataError if unusable."""
    if df is None or df.empty:
        raise DataError(f"{name}: no rows returned")
    df = df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)  # keep exchange-local wall time
    df = df.sort_index()
    dupes = df.index.duplicated(keep="last")
    if dupes.any():
        log_event("warning", name, f"dropped {int(dupes.sum())} duplicate dates")
        df = df[~dupes]
    missing_cols = [c for c in OHLCV if c not in df.columns]
    if missing_cols:
        raise DataError(f"{name}: missing columns {missing_cols}")
    df = df[OHLCV].apply(pd.to_numeric, errors="coerce")
    bad = df["Close"].isna() | (df["Close"] <= 0)
    if bad.any():
        log_event("warning", name, f"dropped {int(bad.sum())} rows with missing/non-positive close")
        df = df[~bad]
    # a missing open/high/low is filled from the close so execution has a price
    for col in ("Open", "High", "Low"):
        df[col] = df[col].where(df[col] > 0, df["Close"])
    inverted = (df["High"] < df["Low"]).sum()
    if inverted:
        log_event("warning", name, f"{int(inverted)} rows with high < low")
    if len(df) < min_rows:
        raise DataError(f"{name}: only {len(df)} rows, need {min_rows}")
    return df


# ---------------------------------------------------------------------------
# disk cache
# ---------------------------------------------------------------------------
def _cache_paths(name: str) -> tuple[Path, Path]:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    return CACHE_DIR / f"{safe}.csv", CACHE_DIR / f"{safe}.meta.json"


def cache_info(name: str) -> dict | None:
    _, meta_path = _cache_paths(name)
    return json.loads(meta_path.read_text()) if meta_path.exists() else None


def _cached(name: str, source: str, fetch, max_age_hours: float, kind: str = "frame"):
    """Return fetch() output, using a disk cache younger than max_age_hours.
    On fetch failure, fall back to any cache with a loud warning."""
    data_path, meta_path = _cache_paths(name)
    meta = cache_info(name)
    if meta and max_age_hours > 0:
        age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(meta["retrieved_at"])).total_seconds() / 3600
        if age_h < max_age_hours:
            return _read_cache(data_path, kind)
    try:
        obj = fetch()
    except Exception as exc:
        if data_path.exists():
            log_event("error", name, f"download failed ({exc}); using cache from {meta['retrieved_at']} (STALE)")
            return _read_cache(data_path, kind)
        raise DataError(f"{name}: download failed and no cache exists ({exc})") from exc
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    obj.to_csv(data_path)
    meta_path.write_text(
        json.dumps(
            {
                "name": name,
                "source": source,
                "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "rows": int(len(obj)),
                "first": str(obj.index.min().date()),
                "last": str(obj.index.max().date()),
            },
            indent=2,
        )
    )
    return obj


def _read_cache(path: Path, kind: str):
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    return df.iloc[:, 0] if kind == "series" else df


# ---------------------------------------------------------------------------
# prices
# ---------------------------------------------------------------------------
def _retry(fn, name: str, attempts: int = 4, wait: float = 5.0):
    """Call fn(); on an exception or an empty result, wait (5s, 10s, 20s) and try again.
    Free data sources occasionally rate-limit cloud machines; failures stay visible."""
    import time

    for i in range(attempts):
        try:
            out = fn()
            if out is not None and len(out):
                return out
            err = "empty response"
        except Exception as exc:  # noqa: BLE001 - re-raised after the last attempt
            err = exc
            if i == attempts - 1:
                raise
        if i < attempts - 1:
            log_event("warning", name, f"attempt {i + 1} failed ({err}); retrying")
            time.sleep(wait * 2**i)
    return out


def _yf_download(ticker: str, **kwargs) -> pd.DataFrame:
    import yfinance as yf

    def once():
        df = yf.download(ticker, auto_adjust=True, progress=False, **kwargs)
        if df is not None and isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df

    return _retry(once, f"yahoo:{ticker}")


def daily_prices(ticker: str, cfg: dict = CFG, use_cache: bool = True) -> pd.DataFrame:
    """Daily split/dividend-adjusted OHLCV. May include today's partial bar;
    see `completed_bars`."""
    start = cfg["data"]["start"]
    if _offline(cfg):
        return synthetic.daily_prices(ticker, start)

    def fetch():
        return validate_ohlcv(_yf_download(ticker, start=start), ticker)

    hours = cfg["data"]["cache_hours"] if use_cache else 0
    return validate_ohlcv(_cached(ticker, f"yahoo:{ticker}", fetch, hours), ticker)


def intraday_prices(ticker: str, interval: str | None = None, cfg: dict = CFG) -> pd.DataFrame:
    interval = interval or cfg["live"]["interval"]
    if _offline(cfg):
        return synthetic.intraday_prices(ticker, interval)
    return validate_ohlcv(_yf_download(ticker, period="5d", interval=interval), f"{ticker} {interval}")


def completed_bars(prices: pd.DataFrame, now: datetime | None = None) -> pd.DataFrame:
    """Drop today's bar if the US market hasn't closed yet (16:00 New York),
    so live signals use exactly the information the backtest assumes."""
    now_ny = pd.Timestamp(now or datetime.now(timezone.utc)).tz_convert("America/New_York")
    last = prices.index[-1]
    if last.date() == now_ny.date() and now_ny.hour < 16:
        return prices.iloc[:-1]
    return prices


def staleness_days(prices: pd.DataFrame, now: datetime | None = None) -> int:
    today = pd.Timestamp(now or datetime.now(timezone.utc)).tz_convert("America/New_York").normalize().tz_localize(None)
    return int((today - prices.index[-1].normalize()).days)


# ---------------------------------------------------------------------------
# macro and cash rate
# ---------------------------------------------------------------------------
def _fred_series(series_id: str) -> pd.Series:
    raw = _retry(lambda: pd.read_csv(FRED_CSV.format(series=series_id)), f"fred:{series_id}")
    date_col, value_col = raw.columns[0], raw.columns[-1]  # handles old and new FRED headers
    s = pd.to_numeric(raw[value_col], errors="coerce")
    s.index = pd.to_datetime(raw[date_col])
    s = s.dropna()
    if s.empty:
        raise DataError(f"FRED {series_id}: no data")
    return s


def publication_lag(s: pd.Series, lag_days: int) -> pd.Series:
    """Re-index a series to the date its value was (conservatively) known."""
    out = s.copy()
    out.index = out.index + BDay(lag_days)
    return out


def fred(series_id: str, cfg: dict = CFG, use_cache: bool = True) -> pd.Series:
    hours = cfg["data"]["cache_hours"] if use_cache else 0
    s = _cached(f"FRED_{series_id}", f"fred:{series_id}", lambda: _fred_series(series_id), hours, kind="series")
    return s.astype(float)


def macro_daily(cfg: dict = CFG) -> pd.DataFrame:
    """Macro and cross-asset drivers, indexed by the date each value was known."""
    yahoo_map, fred_map = cfg["macro"]["yahoo"], cfg["macro"]["fred"]
    lag = int(cfg["macro"].get("fred_lag_days", 2))
    if _offline(cfg):
        df = synthetic.macro(list(yahoo_map) + list(fred_map))
        for col in fred_map:
            df[col] = publication_lag(df[col], lag)
        return df
    frames = {}
    for name, ticker in yahoo_map.items():
        try:
            frames[name] = daily_prices(ticker, cfg=cfg)["Close"]
        except Exception as exc:  # one missing driver shouldn't stop the bot, but it must be visible
            log_event("error", f"macro:{name}", f"{ticker} unavailable, feature dropped ({exc})")
    for name, series_id in fred_map.items():
        try:
            frames[name] = publication_lag(fred(series_id, cfg), lag)
        except Exception as exc:
            log_event("error", f"macro:{name}", f"FRED {series_id} unavailable, feature dropped ({exc})")
    if not frames:
        raise DataError("no macro series could be loaded")
    df = pd.DataFrame(frames).sort_index()
    return df.loc[cfg["data"]["start"] :]


def cash_rate(index: pd.DatetimeIndex, cfg: dict = CFG) -> pd.Series:
    """Annualised cash rate (decimal) known at each date in `index`."""
    ccfg = cfg["macro"]["cash_rate"]
    lag = int(cfg["macro"].get("fred_lag_days", 2))
    if _offline(cfg):
        s = synthetic.macro(["tbill_3m"])["tbill_3m"]
    else:
        try:
            s = publication_lag(fred(ccfg["fred"], cfg), lag)
        except Exception as exc:
            log_event("error", "cash_rate", f"using fallback {ccfg['fallback_annual']:.2%} ({exc})")
            return pd.Series(float(ccfg["fallback_annual"]), index=index)
    s = s / 100.0
    union = s.index.union(index)
    out = s.reindex(union).ffill().reindex(index)
    return out.fillna(float(ccfg["fallback_annual"]))


# ---------------------------------------------------------------------------
# live-only context (no point-in-time history: never used in backtests)
# ---------------------------------------------------------------------------
FUNDAMENTAL_KEYS = [
    "forwardPE",
    "trailingPE",
    "priceToBook",
    "profitMargins",
    "debtToEquity",
    "freeCashflow",
    "marketCap",
    "dividendYield",
]


def fundamentals(ticker: str, cfg: dict = CFG) -> dict:
    """Today's fundamentals snapshot. Not point-in-time: live display only."""
    if _offline(cfg):
        return synthetic.fundamentals(ticker)
    import yfinance as yf

    try:
        info = yf.Ticker(ticker).info or {}
    except Exception as exc:
        log_event("warning", f"fundamentals:{ticker}", str(exc))
        return {}
    out = {}
    for k in FUNDAMENTAL_KEYS:
        v = info.get(k)
        if isinstance(v, (int, float)) and np.isfinite(v):
            out[k] = float(v)
    return out


def news(ticker: str, cfg: dict = CFG) -> list[dict]:
    """Recent headlines for the ticker plus any aliases, de-duplicated.
    Items without a timestamp are dropped: we can't prove they aren't from the future."""
    if _offline(cfg):
        return synthetic.news(ticker)
    aliases = cfg["signals"].get("news_aliases", {}).get(ticker, [])
    out, seen = [], set()
    for t in [ticker, *aliases]:
        for item in _yahoo_news(t):
            if item["title"] not in seen and item["published"] is not None:
                seen.add(item["title"])
                out.append(item)
    return out


def _yahoo_news(ticker: str) -> list[dict]:
    import yfinance as yf

    try:
        items = yf.Ticker(ticker).news or []
    except Exception as exc:
        log_event("warning", f"news:{ticker}", str(exc))
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
        else:
            published = None
        provider = c.get("provider") or {}
        link = (c.get("canonicalUrl") or {}).get("url") or c.get("link", "")
        out.append(
            {
                "title": title,
                "publisher": (provider.get("displayName") if isinstance(provider, dict) else None)
                or c.get("publisher", ""),
                "link": link,
                "published": published,
            }
        )
    return out
