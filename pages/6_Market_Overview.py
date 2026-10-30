"""Market overview: market mood, sector heatmap, scanner rankings and universe coverage (platform phase 8).

Prices: Alpaca daily bars when keys are set (else Yahoo, delayed; offline: synthetic), always labelled. Scanner
rankings are read from research/scanner/ (written on GitHub after each US close). Nothing here places an order.
"""

from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit.errors import StreamlitAPIException

from aurum import assessment as AS
from aurum import scanner as SC
from aurum import universe as U
from aurum.config import ROOT
from aurum.providers import get_provider

st.set_page_config(page_title="Aurum Market Overview", page_icon="🗺️", layout="wide")

SECTORS = {
    "XLK": "Technology",
    "XLC": "Communication",
    "XLY": "Consumer discretionary",
    "XLP": "Consumer staples",
    "XLE": "Energy",
    "XLF": "Financials",
    "XLV": "Health care",
    "XLI": "Industrials",
    "XLB": "Materials",
    "XLRE": "Real estate",
    "XLU": "Utilities",
}
ASSETS = {
    "SPY": "US shares",
    "QQQ": "Nasdaq 100",
    "IWM": "US small caps",
    "EFA": "Developed ex-US",
    "TLT": "Long Treasuries",
    "IEF": "7-10y Treasuries",
    "GLD": "Gold",
    "SLV": "Silver",
    "GDX": "Gold miners",
    "DBC": "Commodities",
}


@st.cache_resource(show_spinner=False)
def provider():
    return get_provider()


@st.cache_data(ttl=900, show_spinner="Loading prices...")
def daily(symbol: str, quarter_hour: int) -> pd.DataFrame:
    return provider().bars(symbol, "1d", start=pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=420))


def returns_table(symbols: dict[str, str]) -> pd.DataFrame:
    rows = []
    q = int(datetime.now().timestamp() // 900)
    for s, name in symbols.items():
        try:
            c = daily(s, q)["Close"].dropna()
        except Exception:
            continue
        if len(c) < 30:
            continue
        rows.append(
            {
                "symbol": s,
                "name": name,
                "1 day": c.iloc[-1] / c.iloc[-2] - 1,
                "1 week": c.iloc[-1] / c.iloc[-6] - 1,
                "1 month": c.iloc[-1] / c.iloc[-22] - 1,
                "1 year": c.iloc[-1] / c.iloc[0] - 1 if len(c) > 240 else None,
            }
        )
    return pd.DataFrame(rows)


st.title("🗺️ Market overview")
st.caption(f"Prices: {provider().name}. Daily closes; what the rules see, not advice. Paper trading only.")

# market mood
q = int(datetime.now().timestamp() // 900)
try:
    spy = daily("SPY", q)
    vix = None
    try:
        from aurum import data as D

        vix = float(D.daily_prices("^VIX")["Close"].dropna().iloc[-1])
    except Exception:
        pass
    reg = AS.market_regime(spy, vix)
    icon = {"risk-on": "🟢", "risk-off": "🔴", "mixed": "🟡"}[reg["state"]]
    st.subheader(f"{icon} Market mood: {reg['state']}")
    st.caption(reg["text"] + ". Risk-on = S&P 500 above its 200-day average and VIX under 25.")
except Exception as exc:
    st.warning(f"Market mood not available: {exc}")

period = st.radio("Heatmap period", ["1 day", "1 week", "1 month", "1 year"], index=2, horizontal=True)
left, right = st.columns(2)
for col, title, group in ((left, "Sectors (S&P 500 sector funds)", SECTORS), (right, "Asset classes", ASSETS)):
    t = returns_table(group)
    with col:
        st.markdown(f"**{title}**")
        if t.empty or t[period].isna().all():
            st.caption("No prices available.")
            continue
        t = t.dropna(subset=[period])
        t["label"] = t["name"] + "<br>" + t[period].map(lambda x: f"{x:+.1%}")
        t["size"] = 1
        fig = px.treemap(
            t,
            path=["label"],
            values="size",
            color=period,
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0,
            custom_data=["symbol"],
        )
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=320, coloraxis_showscale=False)
        fig.update_traces(hovertemplate="%{label}<extra></extra>")
        st.plotly_chart(fig, use_container_width=True, key=f"tree-{title}")

# scanner rankings
st.subheader("Scanner rankings")
tabs = st.tabs(["Long-term", "Swing", "Cross-asset"])
for tab, name in zip(tabs, SC.SCANNERS):
    with tab:
        f = SC.FOLDER / f"{name}-latest.csv"
        meta_f = SC.FOLDER / f"{name}-latest.json"
        if not f.is_file():
            st.info("No scan yet: the scanners run on GitHub after each US close.")
            continue
        meta = json.loads(meta_f.read_text()) if meta_f.is_file() else {}
        if meta.get("evidence") != "evidence":
            st.warning(
                "Not supported by evidence yet: no signal has passed its test (EXP-051), so all signals count "
                "equally. Treat this as a list to research, not a list to buy."
            )
        df = pd.read_csv(f, index_col="symbol")
        st.caption(
            f"Close of {meta.get('asof', '?')}. Stages: "
            + " → ".join(f"{s.split('. ')[-1]} {n:,}" for s, n, _ in meta.get("stages", []))
        )
        show = df[["score"] + [c for c in df.columns if c.startswith("rank_")]].head(30).copy()
        show.columns = ["Score"] + [c.replace("rank_", "").replace("_", " ") for c in show.columns[1:]]
        st.dataframe(
            show,
            use_container_width=True,
            column_config={
                c: st.column_config.ProgressColumn(c, min_value=0, max_value=1, format="%.0f%%")
                for c in show.columns[1:]
            },
        )
        pick = st.selectbox("Open in Live Analysis", list(df.index[:30]), key=f"open-{name}")
        try:
            st.page_link(
                "pages/1_Live_Analysis.py",
                label=f"Open {pick}: chart, plan and summary",
                icon="📈",
                query_params={"symbol": pick},
            )
        except StreamlitAPIException:  # page opened on its own (not through the app): plain link
            st.markdown(f"[📈 Open {pick}: chart, plan and summary](Live_Analysis?symbol={pick})")

# coverage
st.subheader("What the scanners cover")
snap = U.load()
if snap is None:
    st.caption("No universe snapshot yet (the data-foundation workflow builds it).")
else:
    c = snap.counts()
    k = st.columns(5)
    k[0].metric("Listed by Alpaca", f"{c['listed']:,}")
    k[1].metric("Eligible", f"{c['eligible']:,}")
    k[2].metric("Stocks", f"{c['stocks']:,}")
    k[3].metric("ETFs", f"{c['etfs']:,}")
    k[4].metric("Commodity ETFs", f"{c['commodity_etfs']:,}")
    st.caption(
        f"Snapshot {snap.taken:%d %b %Y}. Only these instruments are covered; see "
        f"research/universe/coverage.md for exclusion reasons."
    )
cov = ROOT / "research" / "universe" / "coverage.md"
if cov.is_file():
    with st.expander("Exclusion reasons"):
        st.markdown(cov.read_text().replace("$", "\\$"))
