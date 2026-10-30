"""Paper strategies: the approved strategy definitions being paper-traded (Option 3, D-034), refreshed live.

SIMULATED MONEY ONLY. The ledgers are written by `python run_bot.py --paper`; this page only reads them.
"""

from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from aurum import data, gates, safety
from aurum import designer_charts as DC
from aurum import fairtest as FT
from aurum import spec_paper as SPP
from aurum.config import CFG, ROOT

st.set_page_config(page_title="Aurum Paper Strategies", page_icon="📒", layout="wide")
st.title("📒 Paper strategies")
st.error("SIMULATED MONEY. Paper trading only: Aurum has no connection to any real-money account.", icon="⚠️")

killed = (not safety.live_cfg(CFG)["trading_enabled"]) or safety.KILL_FILE.exists()
st.caption(
    f"Off switch: **{'ON: all paper orders blocked' if killed else 'off (paper trading allowed)'}** · "
    f"engine `paper.engine: {CFG['paper'].get('engine', 'legacy')}` · "
    "the bot (`python run_bot.py --paper`) decides after each US close on completed daily bars "
    "and fills after the next open."
)


@st.fragment(run_every="60s")
def live_strip(tickers: list[str]):
    cols = st.columns(len(tickers) + 1)
    for c, t in zip(cols, tickers):
        try:
            intra = data.intraday_prices(t)
            daily = data.completed_bars(data.daily_prices(t))
            last, prev = float(intra["Close"].iloc[-1]), float(daily["Close"].iloc[-1])
            c.metric(f"{t} (delayed ~15 min)", f"${last:,.2f}", f"{last / prev - 1:+.2%} vs last close")
        except Exception as exc:
            c.metric(t, "–", f"unavailable: {exc}"[:40])
    label = "SYNTHETIC (offline)" if CFG.get("offline") else "Yahoo Finance, delayed about 15 minutes"
    cols[-1].caption(f"Prices: {label}. Refreshed {datetime.now():%H:%M:%S}; this strip updates every minute.")


items = SPP.configured()
tick = sorted({t for it in items for t in it["spec"]["universe"]})
if tick:
    live_strip(tick)

fts = FT.latest_results()
for it in items:
    s, role = it["spec"], it["role"]
    st.divider()
    badge = "MAIN" if role == "main" else "SHADOW (evidence only)"
    st.subheader(f"{s['name']}  ·  {badge}")
    el = gates.eligibility(s, role, fts)
    c1, c2 = st.columns([3, 2])
    with c2:
        st.markdown("**Eligibility gates**" + (" ✅" if el["eligible"] else " ❌ not traded"))
        st.dataframe(
            pd.DataFrame(
                [{"gate": g["gate"], "ok": "✅" if g["passed"] else "❌", "detail": g["detail"]} for g in el["gates"]]
            ),
            hide_index=True,
            width="stretch",
        )
    path = ROOT / it["ledger"]
    with c1:
        if not path.exists():
            st.info(f"No paper ledger yet ({it['ledger']}). It is created the first time the bot runs with --paper.")
            continue
        led = json.loads(path.read_text())
        pos = led.get("positions", {})
        eq = led["cash"] + sum(p["qty"] * p["last_price"] for p in pos.values())
        start = float(CFG["paper"]["starting_cash"])
        m = st.columns(5)
        m[0].metric("Equity", f"${eq:,.2f}", f"{eq / start - 1:+.2%} since start")
        m[1].metric("Cash", f"${led['cash']:,.2f}")
        m[2].metric("Fees paid", f"${led.get('fees', 0):,.2f}")
        m[3].metric("Realised P&L", f"${led.get('realised_pnl', 0):+,.2f}")
        peak = float(led.get("peak_equity", eq))
        m[4].metric("Below peak", f"{eq / peak - 1:.1%}" if peak else "–")
        rows = [
            {"asset": t, "held $": p["qty"] * p["last_price"], "weight": p["qty"] * p["last_price"] / eq if eq else 0}
            for t, p in pos.items()
        ]
        if rows:
            st.dataframe(
                pd.DataFrame(rows),
                hide_index=True,
                width="stretch",
                column_config={
                    "held $": st.column_config.NumberColumn(format="%.2f"),
                    "weight": st.column_config.NumberColumn(format="percent"),
                },
            )
        if led.get("pending"):
            p = led["pending"]
            st.warning(
                f"Pending decision from the close of {p['decided']}: targets "
                + ", ".join(f"{k} {v:.0%}" for k, v in p["targets"].items())
                + ". Orders go in after the next open."
            )
        st.caption(
            f"Strategy fingerprint {led.get('spec_hash')} · last decision {led.get('last_decided') or 'none yet'} · "
            f"last orders {led.get('last_executed') or 'none yet'}"
        )
        hist = pd.DataFrame(led.get("history", []))
        if len(hist):
            hist["time"] = pd.to_datetime(hist["time"])
            daily_eq = hist.set_index("time")["equity"].resample("D").last().dropna()
            fig = go.Figure(
                go.Scatter(x=daily_eq.index, y=daily_eq, name="paper equity", line={"color": DC.STRATEGY, "width": 2})
            )
            fig.update_layout(
                height=260,
                template="plotly_white",
                margin={"t": 20, "b": 20},
                yaxis_title="Equity ($)",
                hovermode="x unified",
            )
            st.plotly_chart(fig, width="stretch", theme="streamlit", key=f"equity_{it['ledger']}")
        tr = pd.DataFrame(led.get("trades", []))
        if len(tr):
            with st.expander(f"Orders ({len(tr)})"):
                st.dataframe(tr.iloc[::-1], hide_index=True, width="stretch")

st.divider()
st.markdown("#### Decision log (latest 30 records for these strategies)")
logp = ROOT / safety.live_cfg(CFG)["decision_log"]
if logp.exists():
    recs = [json.loads(x) for x in logp.read_text().splitlines()[-500:] if x.strip()]
    recs = [r for r in recs if r.get("strategy")][-30:]
    for r in reversed(recs):
        head = f"{r['time']} · {r['strategy']} ({r['role']}) · {r['kind']}"
        if r["kind"] == "order":
            o = r["planned_order"]
            verdict = "allowed" if r["allowed"] else "BLOCKED"
            head += f" · {o['side']} {o['ticker']} {o['from_weight']:.0%}→{o['to_weight']:.0%} · {verdict}"
        with st.expander(head):
            st.json(r)
else:
    st.caption("No decision records yet.")
