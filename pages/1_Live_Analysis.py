"""Live Analysis: a live chart for one ticker with the active strategy's indicators, orders and explanations.

Prices: Alpaca (IEX real-time + consolidated history) when keys are set, otherwise Yahoo (delayed) or synthetic
offline data, always labelled. Paper trading only: nothing on this page places an order.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from aurum import analysis as AN
from aurum import data
from aurum import recommendations as RC
from aurum import spec as SP
from aurum import spec_paper as SPP
from aurum import tradeplan as TP
from aurum.config import CFG
from aurum.livechart import build_payload, live_chart
from aurum.providers import TIMEFRAMES, data_label, get_provider

st.set_page_config(page_title="Aurum Live Analysis", page_icon="📈", layout="wide")

WATCH = list(CFG.get("watchlist", {}).get("etfs", [])) + list(CFG.get("watchlist", {}).get("stocks", []))
TF_NAMES = {"5m": "5 min", "15m": "15 min", "1h": "1 hour", "4h": "4 hours", "1d": "Daily", "1w": "Weekly"}


@st.cache_resource(show_spinner=False)
def provider():
    return get_provider()


@st.cache_resource(show_spinner=False)
def stream(symbols: tuple):
    p = provider()
    if p.name != "Alpaca":
        return None
    from aurum.providers.alpaca import IEXStream

    return IEXStream(list(symbols))


@st.cache_data(ttl=60, show_spinner="Loading prices...")
def bars_for(symbol: str, tf: str, minute: int):
    return provider().bars(symbol, tf)


@st.cache_data(ttl=900, show_spinner="Loading daily history for the strategy...")
def daily_for(symbols: tuple, quarter_hour: int):
    out = {}
    for s in symbols:
        out[s] = AN.daily_frame(provider().bars(s, "1d", start=pd.Timestamp("2016-01-01", tz="UTC")))
    return out


@st.cache_data(ttl=3600, show_spinner=False)
def cash_rate_for(first: str, last: str):
    try:
        idx = pd.bdate_range(first, last)
        return data.cash_rate(idx, CFG)
    except Exception:
        return 0.0


lib = SP.library()
main_ids = [i["spec"]["id"] for i in SPP.configured() if i["role"] == "main"]
order = main_ids + [k for k in lib if k not in main_ids]

with st.sidebar:
    st.subheader("Ticker")
    pick = st.selectbox("Watchlist", WATCH, index=0)
    typed = st.text_input("Or type any US ticker", "").strip().upper()
    symbol = typed or pick
    tf = st.radio("Timeframe", list(TIMEFRAMES), index=4, format_func=lambda k: TF_NAMES[k], horizontal=True)
    st.subheader("Strategy")
    sid = st.selectbox("Strategy shown on the chart", order, format_func=lambda k: lib[k]["name"])
    st.subheader("Extra indicators")
    extras = st.multiselect("Add for investigation", list(AN.EXTRA), default=[])
    ext_hours = st.toggle("Include pre- and after-market bars", value=False)
    live = st.toggle("Live updates (every 2 seconds)", value=True)

st.title(f"📈 {symbol}")
st.caption(AN.COMPANY.get(symbol, "") + " · Paper trading only: nothing here places an order.")

p = provider()
st_obj = stream(tuple(dict.fromkeys(WATCH + [symbol]))) if live else None
clock = p.clock()

spec = lib[sid]
s_used, research = AN.retarget(spec, symbol)
need = tuple(SP.assets_needed(s_used))
try:
    daily = daily_for(need, int(datetime.now().timestamp() // 900))
    idx = None
    for d in daily.values():
        idx = d.index if idx is None else idx.intersection(d.index)
    rf = cash_rate_for(str(idx[0].date()), str(idx[-1].date())) if idx is not None and len(idx) else 0.0
    sv = AN.strategy_view(spec, symbol, daily, rf)
except Exception as exc:
    sv = None
    st.error(f"Could not run the strategy on {symbol}: {exc}")

if sv and sv.notes:
    for n in sv.notes:
        st.warning(n)

plan = None
show_plan = st.sidebar.toggle("Show trade plan lines on the chart", value=True)
if sv is not None and symbol in daily:
    try:
        main_spec = lib[main_ids[0]] if main_ids else None
        hold = None
        if main_spec:
            mw = main_spec["base_weights"]
            hold = TP.holdings_returns(daily_for(tuple(mw), int(datetime.now().timestamp() // 900)), mw)
        plan = TP.build(symbol, daily[symbol], sv.run, research_only=sv.research_only, holdings_returns=hold)
    except Exception as exc:
        st.caption(f"Trade plan not available: {exc}")


def plan_lines() -> list[dict]:
    if plan is None or not show_plan:
        return []
    out = [{"price": plan.stop, "title": "stop", "color": "#d1495b"}]
    for lab, px, _ in plan.targets[:3]:
        short = "resistance" if "resistance" in lab else lab.replace("Target ", "target ").split(" (")[0]
        out.append({"price": px, "title": short, "color": "#199e70"})
    if plan.support:
        out.append({"price": plan.support, "title": "support", "color": "#8a8984", "style": 1})
    return out


def plan_block():
    if plan is None:
        return
    st.subheader("Trade plan")
    badge = {"BUY": "🟢", "HOLD": "🔵", "SELL": "🔴", "STAY OUT": "⚪"}[plan.action]
    st.markdown(f"**{badge} {plan.action}** · as of the close of {plan.as_of:%a %d %b %Y}")
    for n in plan.notes:
        st.warning(n)
    left, right = st.columns([3, 2])
    rows = [(k, v.replace("$", "\\$")) for k, v in plan.summary_rows()]  # "$" would start maths formatting
    left.table(pd.DataFrame(rows, columns=["", "Plan"]).set_index(""))
    with right:
        st.markdown("**What would prove it wrong**")
        st.markdown("\n".join(f"- {x}" for x in plan.invalidation))
        st.markdown("**Confidence checks**")
        st.markdown("\n".join(f"- {'✅' if ok else '⚠️'} {t}" for ok, t in plan.confidence_points))
    st.caption(
        "The plan is what the strategy says plus standard stop and size arithmetic, from completed daily closes. "
        "Confidence is an assessment from the checks shown, not a probability of profit. Paper trading only: "
        "you place any real trade yourself, and nothing here is financial advice."
    )


def chart_block():
    try:
        bars = bars_for(symbol, tf, int(datetime.now().timestamp() // 60))
    except Exception as exc:
        st.error(f"No {TF_NAMES[tf]} prices for {symbol}: {exc}")
        return
    if not ext_hours:
        bars = AN.regular_hours(bars, tf)
    snap = st_obj.snapshot(symbol) if st_obj else None
    trade = snap["trade"] if snap else None
    bars, _ = AN.apply_live(bars, trade, tf)
    label = data_label(bars, p.name, snap["age_s"] if snap else None)
    last = float(bars["Close"].iloc[-1])
    prev = None
    if sv is not None and symbol in daily:
        dser = daily[symbol]["Close"]
        today = pd.Timestamp(bars.index[-1].tz_convert(AN.NY).date())
        before = dser[dser.index < today]
        prev = float(before.iloc[-1]) if len(before) else None
    c = st.columns([1.2, 1, 1.2, 2.6])
    c[0].metric("Last price", f"${last:,.2f}", f"{last / prev - 1:+.2%} vs last close" if prev else None)
    c[1].metric("US market", "OPEN" if clock["is_open"] else "CLOSED")
    c[2].metric(
        "Data",
        "LIVE (IEX)"
        if label.live
        else ("Delayed" if "YAHOO" in label.sources else ("SYNTHETIC" if "SYNTHETIC" in label.sources else "Not live")),
    )
    c[3].caption(f"{label.text} Provider: {p.name}." + (f" Stream: {snap['status']}." if snap else ""))
    layers = (
        AN.strategy_layers(sv, bars, tf)
        if sv is not None
        else {"overlays": [], "panels": [], "markers": [], "tips": {}, "strip": None}
    )
    overlays, panels = list(layers["overlays"]), list(layers["panels"])
    for lab in extras:
        parts = AN.extra_indicator(lab, bars)
        if not parts:
            st.caption(f"{lab}: shown on intraday charts only (it restarts every session).")
        pr = [x for x in parts if x["where"] == "price"]
        pn = [x for x in parts if x["where"] == "panel"]
        for x in pr:
            overlays.append(
                {
                    "name": f"{x['name']} ({TF_NAMES[tf]})",
                    "series": x["series"],
                    "color": AN.OVERLAY_COLOURS[(len(overlays) + 2) % 6],
                    "dashed": x.get("dashed"),
                }
            )
        if pn:
            levels = AN.PANEL_LEVELS.get(AN.EXTRA[lab][0], [])
            panels.append(
                {
                    "title": f"{lab} ({TF_NAMES[tf]})",
                    "series": [
                        {
                            "name": x["name"],
                            "series": x["series"],
                            "color": AN.OVERLAY_COLOURS[i % 6],
                            "kind": x.get("kind", "line"),
                        }
                        for i, x in enumerate(pn)
                    ],
                    "levels": levels,
                }
            )
    payload = build_payload(
        bars,
        title=f"{symbol} · {TF_NAMES[tf]} · {lib[sid]['name']}",
        timeframe=tf,
        overlays=overlays,
        panels=panels,
        markers=layers["markers"],
        price_lines=plan_lines(),
        tips=layers["tips"],
        strip=layers["strip"],
        status=("LIVE IEX · " if label.live else "") + f"top band: blue = strategy holds {symbol}, grey = cash",
        height=640 + 120 * len(panels),
        layout_key=f"{symbol}|{tf}|{sid}|{','.join(extras)}|{ext_hours}",
    )
    live_chart(payload, key=f"chart-{symbol}-{tf}")
    st.caption(
        "Hover any bar for its prices and indicator values; hover an order arrow for the full reason. Strategy "
        "indicators are drawn as the strategy knew them (on intraday charts, the previous close's value). Orders are "
        "decided on daily closes and fill at the next open, exactly as backtested."
    )


refresh = "2s" if (live and clock["is_open"]) else None


def timeframes_block():
    st.subheader("Do the timeframes agree?")
    frames = {}
    for k in ("1h", "1d", "1w"):
        try:
            b = bars_for(symbol, k, int(datetime.now().timestamp() // 60))
            frames[TF_NAMES[k]] = AN.regular_hours(b, k).iloc[:-1]  # completed bars only
        except Exception:
            frames[TF_NAMES[k]] = None
    mt = AN.multi_timeframe(frames)
    icon = {"up": "🟢", "down": "🔴", "mixed": "🟡", "unknown": "⚪"}
    st.markdown(f"**{mt['verdict']}**")
    st.markdown("\n".join(f"- {icon[s_]} **{tf}**: {s_} ({d_})" for tf, s_, d_ in mt["rows"]))
    st.caption(
        "Trend = close vs its 20- and 50-bar exponential averages, on completed bars. Context only: the strategy "
        "decides on daily closes."
    )


def history_block():
    st.subheader("Decisions over time")
    recs = RC.load()
    ok, msg = RC.verify(recs)
    mine = [r for r in recs if r["symbol"] == symbol]
    if not mine:
        st.caption(
            f"No recorded recommendations for {symbol} yet. GitHub records the main strategy's view of every "
            "watchlist ticker after each US close."
        )
    else:
        rows = [
            {
                "Close of": r["as_of"],
                "Strategy": r["strategy_id"],
                "Says": r["recommendation"]["action"],
                "Target": f"{r['recommendation']['target_weight']:.0%}",
                "Stop": f"{r['recommendation']['stop']:,.2f}",
                "What changed": "; ".join(r["changed"]) or "-",
                "Confidence": r["recommendation"]["confidence"],
            }
            for r in reversed(mine[-60:])
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        closes = {t: daily[t]["Close"] for t in daily} if sv is not None else {}
        summ = RC.outcome_summary(RC.outcomes(mine, closes)) if "SPY" in closes else pd.DataFrame()
        if len(summ):
            st.markdown("**How these turned out** (after a round-trip cost, vs SPY)")
            st.dataframe(summ, hide_index=True)
    (st.caption if ok else st.error)(f"History check: {msg}.")


if refresh:
    st.fragment(chart_block, run_every=refresh)()
else:
    chart_block()
plan_block()
c_left, c_right = st.columns([2, 3])
with c_left:
    timeframes_block()
with c_right:
    history_block()
