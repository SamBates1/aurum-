"""Aurum dashboard.   Run:  streamlit run app.py"""
from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from aurum import data
from aurum.config import CFG, all_tickers, is_equity
from aurum.paper import PaperPortfolio
from aurum.pipeline import decide, research

st.set_page_config(page_title="Aurum", page_icon="🪙", layout="wide")

GOLD, UP, DOWN, MUTED = "#C9A227", "#2E9E6A", "#D1495B", "#8A8F98"
DECISION_COLOR = {"BUY": UP, "SELL": DOWN, "HOLD": MUTED}


# ---------- cached data ----------
@st.cache_data(ttl=3600, show_spinner=False)
def get_macro():
    return data.macro_daily()


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def get_research(ticker: str):
    return research(ticker, get_macro())


@st.cache_data(ttl=60, show_spinner=False)
def get_intraday(ticker: str):
    try:
        return data.intraday_prices(ticker)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def get_live_daily(ticker: str):
    return data.daily_prices(ticker)


def live_analysis(ticker: str):
    res = dict(get_research(ticker))
    res["prices"] = get_live_daily(ticker)  # today's partial bar
    intra = get_intraday(ticker)
    live_px = float(intra["Close"].iloc[-1]) if not intra.empty else None
    return decide(ticker, res, live_price=live_px), intra


# ---------- sidebar ----------
st.sidebar.title("🪙 Aurum")
st.sidebar.caption("Gold, macro & miners signal bot")
ticker = st.sidebar.selectbox("Ticker", all_tickers())
auto_paper = st.sidebar.toggle("Auto paper-trade signals", value=False,
                               help="Each refresh, BUY/SELL signals are executed in the paper portfolio")
if CFG.get("offline"):
    st.sidebar.warning("Offline mode: synthetic data")
st.sidebar.markdown("---")
st.sidebar.caption("Educational project. Signals are not investment advice.")

with st.spinner("Running walk-forward research (first load takes a minute)..."):
    for t in all_tickers():
        get_research(t)

tab_sig, tab_bt, tab_paper, tab_macro = st.tabs(["Live signals", "Backtest", "Paper portfolio", "Macro"])


# ---------- live signals ----------
@st.fragment(run_every=timedelta(seconds=CFG["live"]["refresh_seconds"]))
def live_panel():
    analyses, intra = {}, pd.DataFrame()
    for t in all_tickers():
        analyses[t], i = live_analysis(t)
        if t == ticker:
            intra = i
    a = analyses[ticker]

    rows = [{"Ticker": t, "Decision": x.signal["decision"], "Score": round(x.signal["score"], 2),
             "P(up 5d)": f"{x.prob_up:.0%}", "Price": round(x.last_price, 2),
             "Model AUC": round(x.oos_metrics.get("auc", float("nan")), 3)} for t, x in analyses.items()]
    st.subheader("Universe")
    st.dataframe(pd.DataFrame(rows).set_index("Ticker"), width="stretch")

    if auto_paper:
        book = PaperPortfolio()
        px = {t: x.last_price for t, x in analyses.items()}
        for t, x in analyses.items():
            msg = book.apply(t, x.signal["decision"], x.last_price, x.ann_vol, x.atr, px)
            if msg:
                st.toast(f"Paper trade: {msg}")
        book.mark(px); book.save()

    sig = a.signal
    st.subheader(f"{ticker}: {sig['decision']}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Price", f"{a.last_price:,.2f}")
    c2.metric("Combined score", f"{sig['score']:+.2f}", help="-1 strong sell … +1 strong buy")
    c3.metric("Model P(up, 5d)", f"{a.prob_up:.0%}")
    c4.metric("21d volatility", f"{a.ann_vol:.0%}")
    for n in a.notes:
        st.info(n)

    left, right = st.columns([3, 2])
    with left:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.04)
        p = a.prices.iloc[-250:]
        fig.add_trace(go.Candlestick(x=p.index, open=p.Open, high=p.High, low=p.Low, close=p.Close,
                                     name=ticker, increasing_line_color=UP, decreasing_line_color=DOWN), 1, 1)
        for n, col in ((50, GOLD), (200, MUTED)):
            fig.add_trace(go.Scatter(x=p.index, y=a.prices.Close.rolling(n).mean().iloc[-250:],
                                     name=f"SMA {n}", line=dict(color=col, width=1.5)), 1, 1)
        fig.add_trace(go.Scatter(x=p.index, y=a.features["rsi_14"].iloc[-250:], name="RSI",
                                 line=dict(color=GOLD, width=1)), 2, 1)
        fig.add_hline(y=70, line_dash="dot", line_color=MUTED, row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color=MUTED, row=2, col=1)
        fig.update_layout(height=480, margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False,
                          legend=dict(orientation="h", y=1.02))
        st.plotly_chart(fig, width="stretch")
        if not intra.empty:
            fig2 = go.Figure(go.Scatter(x=intra.index, y=intra.Close, line=dict(color=GOLD), name="Intraday"))
            fig2.update_layout(height=220, margin=dict(l=0, r=0, t=30, b=0), title=f"Intraday ({CFG['live']['interval']})")
            st.plotly_chart(fig2, width="stretch")

    with right:
        st.markdown("**Why**")
        for name, comp in sig["components"].items():
            arrow = "▲" if comp["score"] > 0.05 else "▼" if comp["score"] < -0.05 else "■"
            st.markdown(f"{arrow} **{name.title()}**  {comp['score']:+.2f} (weight {comp['weight']:.0%})")
            for r in comp["reasons"]:
                st.caption(f"• {r}")
        if a.sentiment["headlines"]:
            st.markdown("**Headlines**")
            for h in a.sentiment["headlines"][:6]:
                title = f"[{h['title']}]({h['link']})" if h.get("link") else h["title"]
                st.caption(f"{h['sentiment']:+.2f} · {title}")
        if is_equity(ticker) and a.fundamentals:
            st.markdown("**Fundamentals**")
            st.json({k: round(v, 3) if isinstance(v, float) else v for k, v in a.fundamentals.items()}, expanded=False)


with tab_sig:
    live_panel()

# ---------- backtest ----------
with tab_bt:
    r = get_research(ticker)
    st.subheader(f"Walk-forward backtest: {ticker}")
    st.caption(f"Model retrained every {CFG['model']['retrain_every_days']} days on past data only, with a "
               f"{CFG['model']['horizon_days']}-day purge gap. Long above P(up) {CFG['model']['buy_prob']}, "
               f"flat below {CFG['model']['sell_prob']}. {CFG['backtest']['cost_bps']} bps costs per trade.")
    bt = r["bt"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=bt.index, y=bt.strategy_equity, name="Strategy", line=dict(color=GOLD, width=2)))
    fig.add_trace(go.Scatter(x=bt.index, y=bt.benchmark_equity, name="Buy & hold", line=dict(color=MUTED, width=1.5)))
    fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="Growth of $1",
                      legend=dict(orientation="h", y=1.05))
    st.plotly_chart(fig, width="stretch")
    c1, c2 = st.columns(2)
    fmt = r["summary"].copy()
    c1.dataframe(fmt.style.format("{:.3f}"), width="stretch")
    if r["oos"]:
        o = r["oos"]
        c2.metric("Out-of-sample accuracy", f"{o['accuracy']:.1%}", f"{o['accuracy'] - o['base_rate']:+.1%} vs always-up")
        c2.metric("AUC (0.5 = coin flip)", f"{o['auc']:.3f}")
        c2.caption(f"{o['oos_days']:,} out-of-sample days")

# ---------- paper portfolio ----------
with tab_paper:
    book = PaperPortfolio()
    px = {t: float(get_live_daily(t)["Close"].iloc[-1]) for t in all_tickers()}
    eq = book.equity(px)
    start = CFG["paper"]["starting_cash"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Equity", f"${eq:,.2f}", f"{eq / start - 1:+.2%}")
    c2.metric("Cash", f"${book.state['cash']:,.2f}")
    c3.metric("Open positions", len(book.state["positions"]))
    if book.state["positions"]:
        pos = pd.DataFrame([{"Ticker": t, "Qty": p["qty"], "Avg price": p["avg_price"], "Price": px[t],
                             "P&L %": px[t] / p["avg_price"] - 1, "Stop": p["stop"]}
                            for t, p in book.state["positions"].items()]).set_index("Ticker")
        st.dataframe(pos.style.format({"Qty": "{:.4f}", "Avg price": "{:.2f}", "Price": "{:.2f}",
                                       "P&L %": "{:+.2%}", "Stop": "{:.2f}"}), width="stretch")
    if len(book.state["history"]) > 1:
        h = pd.DataFrame(book.state["history"])
        st.line_chart(h.set_index("time")["equity"])
    st.markdown("**Manual trade from current signal**")
    if st.button(f"Execute {ticker} signal now"):
        a, _ = live_analysis(ticker)
        msg = book.apply(ticker, a.signal["decision"], a.last_price, a.ann_vol, a.atr, px)
        book.mark(px); book.save()
        st.success(msg or f"No trade: signal is {a.signal['decision']} and nothing to do")
    if book.state["trades"]:
        st.markdown("**Trade log**")
        st.dataframe(pd.DataFrame(book.state["trades"]).iloc[::-1], width="stretch")
    if st.button("Reset paper portfolio", type="secondary"):
        book.reset(); st.rerun()

# ---------- macro ----------
with tab_macro:
    m = get_macro().loc["2018":]
    st.subheader("Gold's macro drivers")
    st.caption("Gold tends to rise when real yields fall, the dollar weakens, or fear (VIX) spikes.")
    gld = get_live_daily(CFG["universe"]["core"][0])["Close"].loc["2018":]
    for col in m.columns:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=gld.index, y=gld, name=CFG["universe"]["core"][0], line=dict(color=GOLD)), secondary_y=False)
        fig.add_trace(go.Scatter(x=m.index, y=m[col], name=col, line=dict(color=MUTED)), secondary_y=True)
        corr = gld.pct_change().corr(m[col].reindex(gld.index).ffill().diff())
        fig.update_layout(height=260, margin=dict(l=0, r=0, t=30, b=0),
                          title=f"{col}  (daily-change correlation with gold: {corr:+.2f})", showlegend=False)
        st.plotly_chart(fig, width="stretch")
