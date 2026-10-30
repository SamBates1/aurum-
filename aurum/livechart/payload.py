"""Turn bars, indicators and decisions into the JSON the chart draws.

Times: intraday bars are shown in New York wall-clock time (the exchange's clock), daily and weekly bars as dates.
Lightweight Charts has no time zones, so New York times are passed as if they were UTC (the usual convention).
"""

from __future__ import annotations

import html
import math

import numpy as np
import pandas as pd

NY = "America/New_York"
UP, DOWN = "#1baf7a", "#e34948"
BUY, SELL = "#008300", "#d1495b"


def chart_time(ts: pd.Timestamp, intraday: bool):
    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    ny = ts.tz_convert(NY)
    if not intraday:  # daily/weekly bars are stamped at New York midnight (Alpaca) or UTC midnight: +12h finds the day
        return (ny + pd.Timedelta(hours=12)).strftime("%Y-%m-%d")
    wall = ny.tz_localize(None)
    return int((wall - pd.Timestamp("1970-01-01")).total_seconds())


def _key(t) -> str:
    return str(t)


def _series(s: pd.Series, intraday: bool) -> list[dict]:
    out = []
    for t, v in s.items():
        if v is None or not np.isfinite(v):
            continue
        out.append({"time": chart_time(t, intraday), "value": round(float(v), 6)})
    return out


def esc(x) -> str:
    return html.escape(str(x), quote=True)


def build_payload(
    bars: pd.DataFrame,
    *,
    title: str,
    timeframe: str,
    overlays: list[dict] | None = None,
    panels: list[dict] | None = None,
    markers: list[dict] | None = None,
    price_lines: list[dict] | None = None,
    tips: dict | None = None,
    strip: pd.Series | None = None,
    status: str = "",
    height: int = 620,
    visible_bars: int = 150,
    layout_key: str = "",
) -> dict:
    """overlays: [{name, series, color, dashed?}] drawn on the price pane.
    panels: [{title, series: [{name, series, color, kind: line|histogram}], levels: [..]}] drawn underneath.
    markers: [{time, side: BUY|SELL|INFO, text}] placed on the bar containing `time`.
    price_lines: [{price, title, color, style?}]; tips: {timestamp: html} shown when hovering that bar.
    strip: per-bar state (e.g. 'held', 'cash', 'rule met') drawn as a coloured band at the bottom."""
    intraday = timeframe in ("5m", "15m", "1h", "4h")
    b = bars.dropna(subset=["Open", "High", "Low", "Close"])
    times = [chart_time(t, intraday) for t in b.index]
    bar_rows = [
        {
            "time": t,
            "open": round(float(o), 4),
            "high": round(float(h), 4),
            "low": round(float(lo), 4),
            "close": round(float(c), 4),
        }
        for t, o, h, lo, c in zip(times, b["Open"], b["High"], b["Low"], b["Close"])
    ]
    vol = [
        {
            "time": t,
            "value": float(v) if np.isfinite(v) else 0.0,
            "color": "rgba(27,175,122,0.35)" if c >= o else "rgba(227,73,72,0.35)",
        }
        for t, v, o, c in zip(times, b["Volume"].fillna(0), b["Open"], b["Close"])
    ]
    # each marker is snapped to the bar that contains its time (no marker before its own decision time)
    idx = b.index
    mk = []
    for m in markers or []:
        t = pd.Timestamp(m["time"])
        t = t.tz_localize("UTC") if t.tzinfo is None else t
        pos = idx.searchsorted(t, side="right") - 1
        if pos < 0 or pos >= len(idx):
            continue
        side = m.get("side", "INFO")
        mk.append(
            {
                "time": times[pos],
                "position": "belowBar" if side == "BUY" else "aboveBar",
                "shape": "arrowUp" if side == "BUY" else ("arrowDown" if side == "SELL" else "circle"),
                "color": BUY if side == "BUY" else (SELL if side == "SELL" else "#6250d6"),
                "text": m.get("text", side)[:40],
            }
        )
    mk.sort(key=lambda m: (m["time"] if isinstance(m["time"], int) else 0, str(m["time"])))
    tip_map = {}
    for t, h in (tips or {}).items():
        t = pd.Timestamp(t)
        t = t.tz_localize("UTC") if t.tzinfo is None else t
        pos = idx.searchsorted(t, side="right") - 1
        if 0 <= pos < len(idx):
            k = _key(times[pos])
            tip_map[k] = (tip_map.get(k, "") + h) if k in tip_map else h
    strip_rows = []
    if strip is not None and len(strip):
        colours = {
            "held": "rgba(42,120,214,0.55)",
            "cash": "rgba(150,150,150,0.25)",
            "rule met": "rgba(27,175,122,0.55)",
            "rule not met": "rgba(227,73,72,0.35)",
        }
        s = strip.reindex(idx, method="ffill")
        strip_rows = [
            {"time": t, "value": 1, "color": colours.get(v, "rgba(150,150,150,0.25)")}
            for t, v in zip(times, s)
            if isinstance(v, str)
        ]
    return {
        "title": title,
        "intraday": intraday,
        "height": height,
        "visible_bars": visible_bars,
        "layout_key": layout_key or f"{title}|{timeframe}|{len(overlays or [])}|{len(panels or [])}|{bool(strip_rows)}",
        "bars": bar_rows,
        "volume": vol,
        "overlays": [
            {
                "name": o["name"],
                "color": o["color"],
                "dashed": bool(o.get("dashed")),
                "data": _series(o["series"].reindex(idx), intraday),
            }
            for o in overlays or []
        ],
        "panels": [
            {
                "title": p["title"],
                "levels": list(p.get("levels", [])),
                "series": [
                    {
                        "name": s["name"],
                        "color": s["color"],
                        "kind": s.get("kind", "line"),
                        "data": _series(s["series"].reindex(idx), intraday),
                    }
                    for s in p["series"]
                ],
            }
            for p in panels or []
        ],
        "markers": mk,
        "price_lines": [
            {"price": float(p["price"]), "title": p["title"], "color": p["color"], "style": p.get("style", 2)}
            for p in price_lines or []
            if p.get("price") is not None and math.isfinite(float(p["price"]))
        ],
        "tips": tip_map,
        "strip": strip_rows,
        "status": status,
    }
