"""Live Analysis: one ticker, one strategy, any timeframe (live-charts plan, stages 2-5).

What the chart shows is computed here from the same engine as every backtest:
  * the strategy runs on completed DAILY bars (as tested); its indicators are drawn on any timeframe as the strategy
    knew them: on an intraday chart, each bar shows the value from the previous completed close, never a later one;
  * BUY/SELL markers are the strategy's own orders, placed at the bar where they would fill (the next open);
  * hover text explains each order with the rules, indicator values and sizing that produced it;
  * for a ticker outside the strategy's universe, the strategy's rules are applied to that ticker as RESEARCH ONLY
    (clearly labelled: not Fair-Tested on that ticker, never traded);
  * investigation indicators (SMA, EMA, Bollinger, RSI, MACD, ATR, ...) are computed on the chart's own timeframe.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import engine as E
from . import spec as SP
from .indicators import INDICATORS, compute, pivot_levels, session_vwap
from .livechart.payload import esc

NY = "America/New_York"
COMPANY = {
    "SPY": "SPDR S&P 500 ETF Trust",
    "QQQ": "Invesco QQQ Trust (Nasdaq-100)",
    "IWM": "iShares Russell 2000 ETF",
    "EFA": "iShares MSCI EAFE ETF",
    "TLT": "iShares 20+ Year Treasury Bond ETF",
    "IEF": "iShares 7-10 Year Treasury Bond ETF",
    "GLD": "SPDR Gold Shares",
    "SLV": "iShares Silver Trust",
    "GDX": "VanEck Gold Miners ETF",
    "DBC": "Invesco DB Commodity Index Tracking Fund",
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc. (Class A)",
    "META": "Meta Platforms, Inc.",
}
OVERLAY_COLOURS = ["#e87ba4", "#52514e", "#c98500", "#199e70", "#6250d6", "#2a78d6"]

# investigation indicators: label -> (indicator key, params, where)
EXTRA = {
    "SMA 20": ("sma", {"n": 20}, "price"),
    "SMA 50": ("sma", {"n": 50}, "price"),
    "SMA 200": ("sma", {"n": 200}, "price"),
    "EMA 20": ("ema", {"n": 20}, "price"),
    "EMA 50": ("ema", {"n": 50}, "price"),
    "Bollinger 20, 2": ("bollinger", {"n": 20, "k": 2.0}, "price"),
    "RSI 14": ("rsi", {"n": 14}, "panel"),
    "MACD 12/26/9": ("macd", {"fast": 12, "slow": 26, "signal": 9}, "panel"),
    "ATR 14 (% of price)": ("atr_pct", {"n": 14}, "panel"),
    "VWAP (session)": ("vwap", {}, "price"),
    "Stochastic 14, 3": ("stoch", {"n": 14, "smooth": 3}, "panel"),
    "ADX 14": ("adx", {"n": 14}, "panel"),
    "Support / resistance": ("levels", {"k": 5}, "price"),
}
PANEL_LEVELS = {"rsi": [30, 70], "macd": [0], "stoch": [20, 80], "adx": [25]}


def regular_hours(bars: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Keep bars that start in the regular session (09:30-16:00 New York; hourly bars from 09:00, because they start
    on the hour). Daily and weekly bars are returned unchanged."""
    if timeframe not in ("5m", "15m", "1h", "4h"):
        return bars
    ny = bars.index.tz_convert(NY)
    mins = ny.hour * 60 + ny.minute
    first = 540 if timeframe in ("1h", "4h") else 570
    return bars[(ny.day_of_week < 5) & (mins >= first) & (mins < 960)]


def daily_frame(bars: pd.DataFrame, now: pd.Timestamp | None = None) -> pd.DataFrame:
    """Provider daily bars -> the engine's convention (one row per New York trading date, no time zone).

    Only completed days are kept: while today's session is still running (before 16:00 New York) today's bar is a
    partial day, and a strategy deciding "at the close" must not treat it as a close."""
    d = bars.copy()
    d.index = pd.DatetimeIndex((d.index.tz_convert(NY) + pd.Timedelta(hours=12)).date)
    d.index.name = None
    t = pd.Timestamp(now) if now is not None else pd.Timestamp.now(tz="UTC")
    t = (t.tz_localize("UTC") if t.tzinfo is None else t).tz_convert(NY)
    if len(d) and d.index[-1].date() >= t.date() and t.hour < 16:
        d = d.iloc[:-1]
    return d[["Open", "High", "Low", "Close", "Volume"]]


def retarget(spec: dict, symbol: str) -> tuple[dict, bool]:
    """The strategy as defined if `symbol` is in its universe; otherwise its rules applied to `symbol` alone as a
    research-only variant (returns research=True)."""
    s = SP.normalise(spec)
    if symbol in s["universe"]:
        return s, False
    first = s["universe"][0]
    r = copy.deepcopy(s)
    r["id"] = f"{s['id']}-on-{symbol.lower()}"
    r["name"] = f"{s['name']} applied to {symbol} (research only)"
    r["universe"] = [symbol]
    r["base_weights"] = {symbol: round(min(1.0, sum(s["base_weights"].values())), 6)}
    r["execution"]["costs_bps"] = {symbol: SP.DEFAULT_COSTS.get(symbol, 5)}
    for g in r["signals"]:
        g["apply_to"] = [symbol]
        for c in g["conditions"]:
            for side in ("left", "right"):
                o = c[side]
                if isinstance(o, dict) and o["asset"] in (first, *s["universe"]):
                    o["asset"] = symbol
    r["benchmark"] = "SPY"
    return SP.validate(r), True


@dataclass
class StrategyView:
    spec: dict
    research_only: bool
    run: E.StrategyRun
    symbol: str
    notes: list[str] = field(default_factory=list)


def strategy_view(
    spec: dict, symbol: str, daily: dict[str, pd.DataFrame], rf=0.0, capital: float = 10_000.0
) -> StrategyView:
    s, research = retarget(spec, symbol)
    run = E.run_spec(s, daily, rf, capital=capital)
    notes = []
    if research:
        notes.append(
            f"{symbol} is not in this strategy. Its rules are applied to {symbol} for research only: "
            "not Fair-Tested on "
            f"{symbol}, not traded, and the markers are not recommendations."
        )
    return StrategyView(s, research, run, symbol, notes)


def as_known_on(daily_series: pd.Series, bar_index: pd.DatetimeIndex, timeframe: str) -> pd.Series:
    """Map a daily value onto chart bars as the strategy knew it. Intraday: the previous completed close's value.
    Daily: that day's close. Weekly: the last close of that week."""
    s = daily_series.dropna()
    if not len(s):
        return pd.Series(np.nan, index=bar_index)
    dates = pd.DatetimeIndex(bar_index.tz_convert(NY).date)
    if timeframe in ("5m", "15m", "1h", "4h"):
        pos = s.index.searchsorted(dates, side="left") - 1  # strictly before the bar's own date
    elif timeframe == "1w":
        pos = s.index.searchsorted(dates + pd.Timedelta(days=6), side="right") - 1
    else:
        pos = s.index.searchsorted(dates, side="right") - 1
    vals = np.where(pos >= 0, s.to_numpy()[np.clip(pos, 0, len(s) - 1)], np.nan)
    return pd.Series(vals, index=bar_index)


def extra_indicator(label: str, bars: pd.DataFrame) -> list[dict]:
    """[{name, series, kind, where}] for an investigation indicator on the chart's own timeframe."""
    key, params, where = EXTRA[label]
    p = bars[["Open", "High", "Low", "Close", "Volume"]]
    if key == "bollinger":
        return [
            {
                "name": f"Bollinger upper ({params['n']}, {params['k']:g})",
                "series": compute("bb_upper", p, params),
                "where": "price",
                "dashed": True,
            },
            {
                "name": f"Bollinger lower ({params['n']}, {params['k']:g})",
                "series": compute("bb_lower", p, params),
                "where": "price",
                "dashed": True,
            },
        ]
    if key == "vwap":
        if (
            not getattr(bars.index, "tz", None)
            or len(bars) < 2
            or (bars.index[1] - bars.index[0]) >= pd.Timedelta(days=1)
        ):
            return []  # VWAP restarts each session: only meaningful on intraday charts
        src = sorted(set(bars["source"].dropna())) if "source" in bars else []
        note = " (IEX volume only)" if src == ["IEX"] else (" (latest bars: IEX volume only)" if "IEX" in src else "")
        return [{"name": f"VWAP (session){note}", "series": session_vwap(p), "where": "price", "kind": "line"}]
    if key == "levels":
        lv = pivot_levels(p, params["k"])
        return [
            {"name": "Resistance (swing high)", "series": lv["resistance"], "where": "price", "dashed": True},
            {"name": "Support (swing low)", "series": lv["support"], "where": "price", "dashed": True},
        ]
    if key == "stoch":
        return [{"name": label, "series": compute("stoch_k", p, params), "where": "panel", "kind": "line"}]
    if key == "macd":
        c = p["Close"]
        line = (
            c.ewm(span=params["fast"], adjust=False, min_periods=params["fast"]).mean()
            - c.ewm(span=params["slow"], adjust=False, min_periods=params["slow"]).mean()
        )
        sig = line.ewm(span=params["signal"], adjust=False, min_periods=params["signal"]).mean()
        return [
            {"name": "MACD line", "series": line, "where": "panel", "kind": "line"},
            {"name": "MACD signal", "series": sig, "where": "panel", "kind": "line"},
            {"name": "MACD histogram", "series": line - sig, "where": "panel", "kind": "histogram"},
        ]
    s = compute(key, p, params)
    if key == "atr_pct":
        s = s * 100
    return [{"name": label, "series": s, "where": where, "kind": "line"}]


def apply_live(bars: pd.DataFrame, trade: dict | None, timeframe: str) -> tuple[pd.DataFrame, bool]:
    """Fold the latest IEX trade into the last bar (or start a new bar). Returns (bars, changed)."""
    from .providers.base import TIMEFRAMES

    if not trade or not len(bars):
        return bars, False
    t, price = pd.Timestamp(trade["time"]), float(trade["price"])
    t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    last = bars.index[-1]
    if timeframe in ("1d", "1w"):
        same = (
            t.tz_convert(NY).date() == last.tz_convert(NY).date()
            if timeframe == "1d"
            else t - last < pd.Timedelta(days=7)
        )
        period = None
    else:
        period = pd.Timedelta(TIMEFRAMES[timeframe][2])
        same = last <= t < last + period
    out = bars.copy()
    if t < last:
        return bars, False
    if same:
        out.iloc[-1, out.columns.get_loc("Close")] = price
        out.iloc[-1, out.columns.get_loc("High")] = max(out["High"].iloc[-1], price)
        out.iloc[-1, out.columns.get_loc("Low")] = min(out["Low"].iloc[-1], price)
        out.iloc[-1, out.columns.get_loc("source")] = "IEX"
        return out, True
    if period is None:
        return bars, False
    start = last + period * int((t - last) / period)
    row = pd.DataFrame(
        {"Open": price, "High": price, "Low": price, "Close": price, "Volume": 0.0, "source": "IEX"}, index=[start]
    )
    row.index.name = out.index.name
    return pd.concat([out, row]), True


def strategy_layers(sv: StrategyView, bars: pd.DataFrame, timeframe: str, capital_label: str = "$") -> dict:
    """Overlays, panels, markers, tips and the held/cash strip for the chart, from the strategy run."""
    s, run, sym = sv.spec, sv.run, sv.symbol
    comp = run.compiled
    overlays, panels, seen = [], {}, set()
    for g in s["signals"]:
        for c in g["conditions"]:
            for o in (c["left"], c["right"]):
                if not isinstance(o, dict) or o["ind"] == "close":
                    continue
                lab = SP.operand_label(o)
                if lab in seen:
                    continue
                seen.add(lab)
                ser = as_known_on(comp.operands[lab], bars.index, timeframe)
                ind = INDICATORS[o["ind"]]
                if ind.kind == "price" and o["asset"] == sym:
                    overlays.append(
                        {"name": f"{lab} (daily, strategy)", "series": ser, "color": OVERLAY_COLOURS[len(overlays) % 6]}
                    )
                elif ind.kind == "panel":
                    k = 100 if ind.unit == "%" else 1
                    other = c["right"] if c["left"] == o else c["left"]
                    levels = [other * k] if isinstance(other, float) else list(ind.levels)
                    panels[lab] = {
                        "title": f"{lab} (daily, strategy)",
                        "series": [{"name": lab, "series": ser * k, "color": OVERLAY_COLOURS[len(panels) % 6]}],
                        "levels": levels,
                    }
    if s["sizing"]["method"] != "fixed":
        v = as_known_on(comp.vol[sym] * 100, bars.index, timeframe)
        panels["vol"] = {
            "title": f"{sym} {s['sizing']['vol_window']}-day volatility % (strategy)",
            "series": [{"name": "volatility %", "series": v, "color": "#c98500"}],
            "levels": [s["sizing"]["target_vol"] * 100],
        }
    markers, tips = [], {}
    tr = run.trades[run.trades["ticker"] == sym] if len(run.trades) else run.trades
    for _, r in tr.iterrows():
        fill = pd.Timestamp(r["date"])
        when = (fill + pd.Timedelta(hours=9, minutes=30)).tz_localize(NY).tz_convert("UTC")
        if timeframe in ("1d", "1w"):
            when = fill.tz_localize(NY).tz_convert("UTC") + pd.Timedelta(hours=12)
        pct = r["pct_of_account"]
        markers.append(
            {
                "time": when,
                "side": r["side"],
                "text": f"{r['side']} {pct:.1%}" if pct < 0.01 else f"{r['side']} {pct:.0%}",
            }
        )
        ex = E.explain_day(run, r["decided"])
        lines = [
            f"<div class='head {'buy' if r['side'] == 'BUY' else 'sell'}'>{esc(r['side'])} {esc(sym)}: "
            f"{pct:.1%} of the account</div>"
        ]
        lines.append(
            f"<div class='line'>Decided at the close of {esc(ex['date'])}; fills at the open of "
            f"{esc(fill.date())}</div>"
        )
        a = ex["assets"][sym]
        lines.append(
            f"<div class='line'>Target {a['target_weight']:.0%} (base {a['base_weight']:.0%} x sizing "
            f"{a['sizing_multiplier']:.2f}"
            + (f", volatility {a['volatility']:.0%}" if a["volatility"] else "")
            + ")</div>"
        )
        for sg in ex["signals"]:
            state = "met" if sg["met"] else ("not yet known" if sg["met"] is None else "NOT met")
            lines.append(f"<div class='line'>Rule '{esc(sg['label'])}': {state}</div>")
            for cd in sg["conditions"]:
                lines.append(
                    f"<div class='note'>{esc(cd['rule'])}: {cd['values'][0]:,.4g} vs {cd['values'][1]:,.4g}</div>"
                )
        lines.append(f"<div class='note'>{esc(r['reason'])}</div>")
        if sv.research_only:
            lines.append("<div class='note'>Research only: these rules were not Fair-Tested on this ticker.</div>")
        tips[when] = "".join(lines)
    held = run.result.weights[sym] if sym in run.result.weights else pd.Series(dtype=float)
    state = pd.Series(np.where(held > 0.005, "held", "cash"), index=held.index)
    strip_daily = state.copy()
    strip = None
    if len(strip_daily):
        codes = strip_daily.map({"held": 1.0, "cash": 0.0})
        known = as_known_on(codes, bars.index, timeframe)
        strip = known.map({1.0: "held", 0.0: "cash"})
    return {"overlays": overlays, "panels": list(panels.values()), "markers": markers, "tips": tips, "strip": strip}


def trend_state(bars: pd.DataFrame) -> tuple[str, str]:
    """Simple trend on one timeframe from completed bars: up when close > EMA 20 > EMA 50, down when below both."""
    c = bars["Close"].dropna()
    if len(c) < 60:
        return "unknown", "not enough bars"
    e20 = c.ewm(span=20, adjust=False).mean().iloc[-1]
    e50 = c.ewm(span=50, adjust=False).mean().iloc[-1]
    x = c.iloc[-1]
    if x > e20 > e50:
        return "up", f"close {x:,.2f} > EMA 20 {e20:,.2f} > EMA 50 {e50:,.2f}"
    if x < e20 < e50:
        return "down", f"close {x:,.2f} < EMA 20 {e20:,.2f} < EMA 50 {e50:,.2f}"
    return "mixed", f"close {x:,.2f}, EMA 20 {e20:,.2f}, EMA 50 {e50:,.2f}"


def multi_timeframe(frames: dict[str, pd.DataFrame]) -> dict:
    """{rows: [(timeframe, state, detail)], verdict}: do the timeframes agree?"""
    rows = [(tf, *trend_state(b)) for tf, b in frames.items() if b is not None and len(b)]
    states = {s for _, s, _ in rows if s != "unknown"}
    if states == {"up"}:
        verdict = "All timeframes agree: up"
    elif states == {"down"}:
        verdict = "All timeframes agree: down"
    elif "up" in states and "down" in states:
        verdict = "Timeframes conflict: some up, some down"
    else:
        verdict = "No clear agreement (some timeframes mixed)"
    return {"rows": rows, "verdict": verdict}
