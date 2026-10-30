"""Alpaca market data (free Basic plan): historical bars, news, market clock and the IEX real-time stream.

Free-plan rules this module follows (docs.alpaca.markets/docs/about-market-data-api):
  * consolidated (SIP) history is available except the latest 15 minutes, so history is requested from SIP up to
    16 minutes ago and the rest from IEX; every bar records which feed it came from;
  * real-time streaming is IEX only, up to 30 symbols;
  * 200 historical requests a minute: requests are paged and the caller caches results.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.parse
import urllib.request
from collections import deque
from datetime import datetime, timezone

import pandas as pd

from .base import TIMEFRAMES, Provider, finish
from .keys import alpaca_keys, redact

DATA = "https://data.alpaca.markets"
TRADING = "https://paper-api.alpaca.markets"  # paper endpoint: used only for the market clock, never for orders
STREAM = "wss://stream.data.alpaca.markets/v2/iex"
MAX_STREAM_SYMBOLS = 30


class AlpacaError(RuntimeError):
    pass


def _get(url: str, params: dict | None = None, timeout: float = 30) -> dict:
    keys = alpaca_keys()
    if not keys:
        raise AlpacaError("Alpaca keys not set (ALPACA_API_KEY / ALPACA_SECRET_KEY)")
    q = ("?" + urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None})) if params else ""
    req = urllib.request.Request(url + q, headers={"APCA-API-KEY-ID": keys[0], "APCA-API-SECRET-KEY": keys[1]})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:300]
            if e.code == 429 and attempt < 3:  # rate limit: wait and retry
                time.sleep(2 * (attempt + 1))
                continue
            raise AlpacaError(redact(f"HTTP {e.code} from {url}: {body}")) from None
        except urllib.error.URLError as e:
            if attempt < 3:
                time.sleep(1 + attempt)
                continue
            raise AlpacaError(redact(f"cannot reach {url}: {e.reason}")) from None
    raise AlpacaError("unreachable")


def _iso(t) -> str:
    return pd.Timestamp(t).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


class AlpacaProvider(Provider):
    name = "Alpaca"

    def _bars(self, symbol: str, tf: str, start, end, feed: str) -> pd.DataFrame:
        rows, token = [], None
        while True:
            d = _get(
                f"{DATA}/v2/stocks/bars",
                {
                    "symbols": symbol,
                    "timeframe": tf,
                    "start": _iso(start),
                    "end": _iso(end),
                    "limit": 10000,
                    "adjustment": "all",
                    "feed": feed,
                    "page_token": token,
                },
            )
            rows += (d.get("bars") or {}).get(symbol, [])
            token = d.get("next_page_token")
            if not token:
                break
        if not rows:
            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        df = pd.DataFrame(rows)
        df.index = pd.to_datetime(df["t"], utc=True)
        return df.rename(columns={"o": "Open", "h": "High", "l": "Low", "c": "Close", "v": "Volume"})

    def bars(self, symbol, timeframe, start=None, end=None) -> pd.DataFrame:
        tf, lookback, _ = TIMEFRAMES[timeframe]
        now = pd.Timestamp(datetime.now(timezone.utc))
        end = pd.Timestamp(end or now)
        end = end.tz_localize("UTC") if end.tzinfo is None else end
        start = pd.Timestamp(start) if start is not None else end - lookback
        start = start.tz_localize("UTC") if start.tzinfo is None else start
        cut = now - pd.Timedelta(minutes=16)
        parts = []
        if start < cut:
            sip = self._bars(symbol, tf, start, min(end, cut), "sip")
            if len(sip):
                parts.append(finish(sip, "SIP"))
        if end > cut:
            iex = self._bars(
                symbol, tf, max(start, cut - pd.Timedelta(days=7 if timeframe in ("1d", "1w") else 1)), end, "iex"
            )
            if len(iex):
                f = finish(iex, "IEX")
                if parts:
                    f = f[f.index > parts[0].index[-1]] if len(parts[0]) else f
                parts.append(f)
        if not parts:
            raise AlpacaError(f"no bars for {symbol} {timeframe}")
        return pd.concat(parts).sort_index()

    def news(self, symbols, limit=20) -> list[dict]:
        d = _get(f"{DATA}/v1beta1/news", {"symbols": ",".join(symbols), "limit": limit, "sort": "desc"})
        return [
            {
                "time": n.get("created_at"),
                "headline": n.get("headline"),
                "summary": n.get("summary"),
                "source": n.get("source"),
                "url": n.get("url"),
                "symbols": n.get("symbols", []),
            }
            for n in d.get("news", [])
        ]

    def clock(self) -> dict:
        try:
            c = _get(f"{TRADING}/v2/clock")
            return {
                "is_open": bool(c.get("is_open")),
                "timestamp": c.get("timestamp"),
                "next_open": c.get("next_open"),
                "next_close": c.get("next_close"),
                "estimated": False,
            }
        except AlpacaError:
            return super().clock()


class IEXStream:
    """Real-time IEX trades and minute bars for up to 30 symbols, in a background thread. Reconnects on failure.
    The browser never sees the keys: pages read `snapshot(symbol)` from this object."""

    def __init__(self, symbols: list[str]):
        self.symbols = list(dict.fromkeys(s.upper() for s in symbols))[:MAX_STREAM_SYMBOLS]
        self.trades: dict[str, dict] = {}
        self.minute_bars: dict[str, deque] = {s: deque(maxlen=600) for s in self.symbols}
        self.status = "starting"
        self.error = ""
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        import websocket  # websocket-client

        backoff = 2
        while not self._stop.is_set():
            keys = alpaca_keys()
            if not keys:
                self.status, self.error = "no keys", "Alpaca keys not set"
                return
            try:
                ws = websocket.create_connection(STREAM, timeout=30)
                ws.recv()  # welcome
                ws.send(json.dumps({"action": "auth", "key": keys[0], "secret": keys[1]}))
                auth = json.loads(ws.recv())
                if not any(m.get("msg") == "authenticated" for m in auth):
                    self.status, self.error = "auth failed", redact(str(auth))[:200]
                    return
                ws.send(json.dumps({"action": "subscribe", "trades": self.symbols, "bars": self.symbols}))
                self.status, self.error, backoff = "connected", "", 2
                while not self._stop.is_set():
                    for m in json.loads(ws.recv()):
                        self._handle(m)
            except Exception as exc:  # network drop, timeout: reconnect with backoff
                self.status, self.error = "reconnecting", redact(str(exc))[:200]
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)

    def _handle(self, m: dict):
        kind, s = m.get("T"), m.get("S")
        if kind == "t" and s:
            self.trades[s] = {"price": float(m["p"]), "size": float(m.get("s", 0)), "time": pd.Timestamp(m["t"])}
        elif kind == "b" and s:
            self.minute_bars.setdefault(s, deque(maxlen=600)).append(
                {
                    "time": pd.Timestamp(m["t"]),
                    "Open": m["o"],
                    "High": m["h"],
                    "Low": m["l"],
                    "Close": m["c"],
                    "Volume": m["v"],
                }
            )
        elif kind == "error":
            self.error = redact(str(m))[:200]

    def snapshot(self, symbol: str) -> dict:
        t = self.trades.get(symbol.upper())
        age = (pd.Timestamp(datetime.now(timezone.utc)) - t["time"]).total_seconds() if t else None
        return {
            "status": self.status,
            "error": self.error,
            "trade": t,
            "age_s": age,
            "minute_bars": list(self.minute_bars.get(symbol.upper(), [])),
        }

    def stop(self):
        self._stop.set()
