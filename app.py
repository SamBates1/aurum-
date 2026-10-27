"""Aurum dashboard.   Run:  python -m streamlit run app.py"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from aurum import benchmarks, data, model
from aurum.backtest import performance
from aurum.config import CFG, all_tickers, cost_bps, is_equity
from aurum.features import CROSS_ASSET, align
from aurum.features import atr as atr_fn
from aurum.paper import PaperPortfolio
from aurum.pipeline import decide, research

st.set_page_config(page_title="Aurum", page_icon="🪙", layout="wide")

GOLD, UP, DOWN, MUTED = "#C9A227", "#2E9E6A", "#D1495B", "#8A8F98"
SCFG = CFG["strategy"]


# ---------- cached data ----------
@st.cache_resource(ttl=3600, show_spinner=False)
def get_macro():
    return data.macro_daily()


@st.cache_resource(ttl=6 * 3600, show_spinner=False)
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
    return data.daily_prices(ticker, use_cache=False)


@st.cache_data(ttl=300, show_spinner=False)
def get_decision(ticker: str):
    """Fresh features from the latest completed bars + the latest live price."""
    intra = get_intraday(ticker)
    live_px = float(intra["Close"].iloc[-1]) if not intra.empty else None
    return decide(ticker, get_research(ticker), prices=get_live_daily(ticker), live_price=live_px)


def fmt_pct(x):
    return "–" if x is None or not np.isfinite(x) else f"{x:.0%}"


# ---------- sidebar ----------
st.sidebar.title("🪙 Aurum")
st.sidebar.caption("Gold, macro & miners research system")
ticker = st.sidebar.selectbox("Ticker", all_tickers())
auto_paper = st.sidebar.toggle(
    "Auto paper-trade signals",
    value=False,
    help="Each refresh, BUY/SELL signals are executed in the paper portfolio (simulated money)",
)
if CFG.get("offline"):
    st.sidebar.warning("Offline mode: SYNTHETIC data, not real markets")
st.sidebar.markdown("---")
st.sidebar.caption("Educational research project. Signals are not investment advice.")

with st.spinner("Running walk-forward research (first load takes a few minutes)..."):
    failed = []
    for t in all_tickers():
        try:
            get_research(t)
        except Exception as exc:
            failed.append(f"{t}: {exc}")
tickers = [t for t in all_tickers() if not any(f.startswith(t + ":") for f in failed)]
for f in failed:
    st.sidebar.error(f"Research failed – {f}")
if data.DATA_EVENTS:
    with st.sidebar.expander(f"Data warnings ({len(data.DATA_EVENTS)})"):
        for e in data.DATA_EVENTS[-30:]:
            st.caption(f"{e['level']} · {e['source']}: {e['message']}")
if ticker not in tickers:
    st.error(f"{ticker} is unavailable: research failed. See the sidebar.")
    st.stop()

tab_sig, tab_bt, tab_paper, tab_macro = st.tabs(["Live signals", "Backtest", "Paper portfolio", "Macro"])


# ---------- live signals ----------
@st.fragment(run_every=timedelta(seconds=CFG["live"]["refresh_seconds"]))
def live_panel():
    decs = {}
    for t in tickers:
        try:
            decs[t] = get_decision(t)
        except Exception as exc:
            st.warning(f"{t}: no decision ({exc})")
    rows = [
        {
            "Ticker": t,
            "Decision": d.decision,
            "Score": round(d.score, 2) if np.isfinite(d.score) else None,
            "P(up 5d)": fmt_pct(d.prob_up),
            "ML vote strength": fmt_pct(d.skill),
            "Price": round(d.last_price, 2),
            "Signal as of": d.as_of,
            "Tradeable": "yes" if d.tradeable else "NO",
        }
        for t, d in decs.items()
    ]
    st.subheader("Universe")
    st.dataframe(pd.DataFrame(rows).set_index("Ticker"), width="stretch")
    st.caption(
        "Signals use completed daily bars, exactly as backtested, so they change once per day after the US close. "
        "Prices update live for stops and paper fills."
    )

    if auto_paper:
        book = PaperPortfolio()
        px = {t: d.last_price for t, d in decs.items()}
        for t, d in decs.items():
            msg = book.apply(t, d.decision, d.last_price, d.ann_vol, d.atr, px, d.tradeable)
            if msg:
                st.toast(f"Paper trade: {msg}")
        book.mark(px)
        book.save()

    if ticker not in decs:
        return
    a = decs[ticker]
    st.subheader(f"{ticker}: {a.decision}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Price", f"{a.last_price:,.2f}")
    c2.metric(
        "Strategy score",
        f"{a.score:+.2f}" if np.isfinite(a.score) else "–",
        help=f"-1 … +1. BUY at ≥ {SCFG['buy_above']}, SELL at ≤ {SCFG['sell_below']}",
    )
    c3.metric("Model P(up, 5d)", fmt_pct(a.prob_up))
    c4.metric("21d volatility", fmt_pct(a.ann_vol))
    for n in a.notes:
        st.info(n)

    left, right = st.columns([3, 2])
    with left:
        p = a.bars.iloc[-250:]
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.04)
        fig.add_trace(
            go.Candlestick(
                x=p.index,
                open=p.Open,
                high=p.High,
                low=p.Low,
                close=p.Close,
                name=ticker,
                increasing_line_color=UP,
                decreasing_line_color=DOWN,
            ),
            1,
            1,
        )
        for n, col in ((50, GOLD), (200, MUTED)):
            fig.add_trace(
                go.Scatter(
                    x=p.index,
                    y=a.bars.Close.rolling(n).mean().iloc[-250:],
                    name=f"SMA {n}",
                    line=dict(color=col, width=1.5),
                ),
                1,
                1,
            )
        fig.add_trace(
            go.Scatter(x=p.index, y=a.features["rsi_14"].iloc[-250:], name="RSI", line=dict(color=GOLD, width=1)), 2, 1
        )
        fig.add_hline(y=70, line_dash="dot", line_color=MUTED, row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color=MUTED, row=2, col=1)
        fig.update_layout(
            height=480,
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", y=1.02),
        )
        st.plotly_chart(fig, width="stretch")
        intra = get_intraday(ticker)
        if not intra.empty:
            fig2 = go.Figure(go.Scatter(x=intra.index, y=intra.Close, line=dict(color=GOLD), name="Intraday"))
            fig2.update_layout(
                height=220, margin=dict(l=0, r=0, t=30, b=0), title=f"Intraday ({CFG['live']['interval']})"
            )
            st.plotly_chart(fig2, width="stretch")

    with right:
        st.markdown("**Why**")
        for name, comp in a.components.items():
            s = comp["score"]
            if s is None or not np.isfinite(s):
                st.markdown(f"■ **{name.title()}**  n/a")
            else:
                arrow = "▲" if s > 0.05 else "▼" if s < -0.05 else "■"
                tag = "" if comp["weight"] > 0 else " · context only, not traded"
                st.markdown(f"{arrow} **{name.title()}**  {s:+.2f} (weight {comp['weight']:.0%}{tag})")
            for r in comp["reasons"]:
                st.caption(f"• {r}")
        if a.sentiment["headlines"]:
            st.markdown("**Headlines**")
            for h in a.sentiment["headlines"][:6]:
                title = f"[{h['title']}]({h['link']})" if h.get("link") else h["title"]
                st.caption(f"{h['sentiment']:+.2f} · {title}")
        if is_equity(ticker) and a.fundamentals:
            st.markdown("**Fundamentals** (today's snapshot)")
            st.json({k: round(v, 3) for k, v in a.fundamentals.items()}, expanded=False)


with tab_sig:
    live_panel()

# ---------- backtest ----------
with tab_bt:
    r = get_research(ticker)
    st.subheader(f"Walk-forward backtest: {ticker}")
    st.caption(
        f"Out-of-sample from {r.eval_start:%Y-%m-%d}. Model retrained every {CFG['model']['retrain_every_days']} "
        f"days on past data only, {CFG['model']['horizon_days']}-day purge. Decisions at the close, filled at the "
        f"next open, {cost_bps(ticker):g} bps per trade. Same rules as the live signal."
    )
    sims = benchmarks.run_all(
        r.prices, r.X, r.score, r.wf.probs, None, atr_fn(r.prices), r.rf, SCFG, cost_bps(ticker), r.eval_start
    )
    fig = go.Figure()
    for name, color, w in (
        ("strategy", GOLD, 2.2),
        ("buy_hold", MUTED, 1.4),
        ("vol_sized_hold", "#8FA3BF", 1.2),
        ("sma_trend", UP, 1.2),
    ):
        eq = (1 + sims[name].daily["ret"]).cumprod()
        fig.add_trace(go.Scatter(x=eq.index, y=eq, name=name.replace("_", " "), line=dict(color=color, width=w)))
    hold = pd.Timestamp(CFG["research"]["holdout_start"])
    fig.add_vline(x=hold, line_dash="dash", line_color=MUTED)
    fig.update_layout(
        height=380,
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis_title="Growth of 1 (after costs)",
        legend=dict(orientation="h", y=1.05),
    )
    st.plotly_chart(fig, width="stretch")
    tbl = pd.DataFrame({k: performance(v, r.rf) for k, v in sims.items()}).T
    show = [
        "cagr",
        "volatility",
        "sharpe",
        "sortino",
        "max_drawdown",
        "calmar",
        "time_in_market",
        "trades",
        "win_rate",
        "costs_per_year",
    ]
    st.dataframe(tbl[show].astype(float).style.format("{:.3f}"), width="stretch")
    m = model.classification_metrics(r.wf.probs, r.y)
    if "auc" in m:
        c1, c2, c3 = st.columns(3)
        c1.metric("Out-of-sample AUC", f"{m['auc']:.3f}", help="0.5 = coin flip")
        c2.metric("Accuracy", f"{m['accuracy']:.1%}", f"{m['accuracy'] - m['base_rate']:+.1%} vs always-up")
        c3.metric(
            "Brier score",
            f"{m['brier']:.4f}",
            f"{m['brier'] - m['brier_baseline']:+.4f} vs constant forecast",
            delta_color="inverse",
        )
    st.caption(
        "Full study with holdout, uncertainty intervals and cost sensitivity: run `python run_research.py` "
        "and open reports/latest/report.md."
    )

# ---------- paper portfolio ----------
with tab_paper:
    st.caption("Simulated money only. Fills at the latest price seen; real fills would differ.")
    book = PaperPortfolio()
    px = {t: float(get_live_daily(t)["Close"].iloc[-1]) for t in tickers}
    eq = book.equity(px)
    start = CFG["paper"]["starting_cash"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Equity", f"${eq:,.2f}", f"{eq / start - 1:+.2%}")
    c2.metric("Cash", f"${book.state['cash']:,.2f}")
    c3.metric("Realised P&L", f"${book.state['realised_pnl']:+,.2f}")
    c4.metric("Fees paid", f"${book.state['fees']:,.2f}")
    if book.state["positions"]:
        pos = pd.DataFrame(
            [
                {
                    "Ticker": t,
                    "Qty": p["qty"],
                    "Entry": p["entry_price"],
                    "Price": p["last_price"],
                    "Unrealised P&L %": p["last_price"] / p["entry_price"] - 1,
                    "Stop": p["stop"],
                }
                for t, p in book.state["positions"].items()
            ]
        ).set_index("Ticker")
        st.dataframe(
            pos.style.format(
                {"Qty": "{:.4f}", "Entry": "{:.2f}", "Price": "{:.2f}", "Unrealised P&L %": "{:+.2%}", "Stop": "{:.2f}"}
            ),
            width="stretch",
        )
    if len(book.state["history"]) > 1:
        h = pd.DataFrame(book.state["history"])
        st.line_chart(h.set_index("time")["equity"])
    st.markdown("**Manual trade from current signal**")
    if st.button(f"Execute {ticker} signal now"):
        a = get_decision(ticker)
        msg = book.apply(ticker, a.decision, a.last_price, a.ann_vol, a.atr, px, a.tradeable)
        book.mark(px)
        book.save()
        st.success(msg or f"No trade: signal is {a.decision} and the position already matches it")
    if book.state["trades"]:
        st.markdown("**Trade log**")
        st.dataframe(pd.DataFrame(book.state["trades"]).iloc[::-1], width="stretch")
    if st.button("Reset paper portfolio", type="secondary"):
        book.reset()
        st.rerun()

# ---------- macro ----------
with tab_macro:
    m = get_macro().loc["2018":]
    core = CFG["universe"]["core"][0]
    st.subheader("Gold's macro drivers")
    st.caption(
        "Hypotheses, not guarantees: gold has tended to rise when real yields fall, the dollar weakens or fear "
        "(VIX) spikes. FRED series are shown on the date they were (conservatively) available."
    )
    gld = get_live_daily(core)["Close"].loc["2018":]
    for col in m.columns:
        s = align(m[[col]], gld.index)[col]
        chg = s.pct_change(fill_method=None) if col in CROSS_ASSET or col == "dxy" else s.diff()
        corr = gld.pct_change().corr(chg)
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=gld.index, y=gld, name=core, line=dict(color=GOLD)), secondary_y=False)
        fig.add_trace(go.Scatter(x=m.index, y=m[col], name=col, line=dict(color=MUTED)), secondary_y=True)
        fig.update_layout(
            height=260,
            margin=dict(l=0, r=0, t=30, b=0),
            showlegend=False,
            title=f"{col}  (daily-change correlation with {core}: {corr:+.2f})",
        )
        st.plotly_chart(fig, width="stretch")
