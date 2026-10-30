"""Decision Board: open it any time, press Check now, and see what the strategy says to do with your money (D-036).

What the strategy says, based on historical testing; not personal financial advice. Aurum never places real-money
orders: you place any trade yourself on your own platform.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from aurum import data, gates
from aurum import decision_board as DB
from aurum import designer as D
from aurum import designer_charts as DC
from aurum import fairtest as FT
from aurum import spec as SP
from aurum import spec_paper as SPP
from aurum.config import CFG
from aurum.indicators import INDICATORS, compute

st.set_page_config(page_title="Aurum Decision Board", page_icon="🎯", layout="wide")
st.title("🎯 Decision Board")
st.caption(
    "What your chosen strategy says to do right now, in pounds. It is what the strategy says based on historical "
    "testing, not personal financial advice; past results do not guarantee future returns. You place any trade "
    "yourself: Aurum never touches real money."
)

lib = SP.library()
main = [i["spec"]["id"] for i in SPP.configured() if i["role"] == "main"]
order = main + [k for k in lib if k not in main]

with st.sidebar:
    st.subheader("Strategy")
    sid = st.selectbox("Follow this strategy", order, format_func=lambda k: lib[k]["name"])
    st.subheader("Your money (£)")
    mode = st.radio("Where are you starting from?", ["Starting from cash", "I already hold some"], key="db_mode")
    spec = lib[sid]
    holdings = {}
    if mode == "Starting from cash":
        cash = st.number_input("Amount to invest (£)", min_value=0.0, value=1000.0, step=100.0, key="db_cash0")
    else:
        for t in spec["universe"]:
            holdings[t] = st.number_input(
                f"Value of your {t}-type fund now (£)", min_value=0.0, value=0.0, step=50.0, key=f"db_h_{t}"
            )
        cash = st.number_input("Cash waiting to invest (£)", min_value=0.0, value=0.0, step=50.0, key="db_cash1")
    st.caption("Enter today's values from your platform. Amounts are worked out from these.")
    st.subheader("Updates")
    auto = st.toggle(
        "Refresh every minute", value=False, help="Re-downloads prices every 60 seconds while this page is open."
    )

if st.button("🔄 Check now", type="primary"):
    st.session_state.db_token = st.session_state.get("db_token", 0) + 1
token = st.session_state.get("db_token", 0)


@st.cache_data(ttl=60, show_spinner="Getting the latest prices...")
def latest(tickers: tuple, token: int):
    daily, live, errors = {}, {}, {}
    for t in tickers:
        try:
            daily[t] = data.daily_prices(t, use_cache=False)
            intra = data.intraday_prices(t)
            live[t] = float(intra["Close"].iloc[-1]) if len(intra) else None
        except Exception as exc:
            errors[t] = str(exc)
    return daily, live, errors, datetime.now()


def board_view():
    tickers = tuple(sorted(set(SP.assets_needed(spec))))
    daily, live, errors, fetched = latest(tickers, token if not auto else int(datetime.now().timestamp() // 60))
    if errors:
        st.error(
            "Could not get prices for " + "; ".join(f"{t}: {e}" for t, e in errors.items()) + ". No decision shown."
        )
        return
    completed = {t: data.completed_bars(p) for t, p in daily.items()}
    ms = DB.market_status()
    h = SP.spec_hash(spec)
    ft = FT.latest_results().get(h)
    appr = gates.approval_for(h)
    b = DB.build(spec, completed, holdings, cash, live=live, fair_test=ft, approval=appr)

    c = st.columns(4)
    c[0].metric("US market", "OPEN" if ms["open"] else "CLOSED")
    c[0].caption(f"New York {ms['ny_time']} · UK {ms['uk_time']}")
    c[1].metric("Decision from the close of", b.official_date.strftime("%d %b %Y"))
    c[1].caption("completed daily prices, as tested")
    c[2].metric("Your money", f"£{b.money:,.0f}")
    c[3].metric("Next decision day", b.next_check.strftime("%d %b %Y") if b.next_check is not None else "none")
    c[3].caption("after the US close (about 21:00 UK)")
    label = (
        "SYNTHETIC test data (offline): not real prices"
        if CFG.get("offline")
        else "Yahoo Finance; latest prices about 15 minutes delayed"
    )
    st.caption(f"Prices: {label}. Checked {fetched:%H:%M:%S}.")
    if CFG.get("offline"):
        st.warning("OFFLINE MODE: synthetic prices. Do not act on this.")

    box = st.success if any(r["action"] != "HOLD" for r in b.rows) else st.info
    box(f"### Decision: {b.headline}")
    if not appr:
        st.warning(
            "You have not approved this strategy (Strategy Designer → Fair Test & approval). Its evidence: "
            + (ft["status"].upper() if ft else "no Fair Test saved")
            + "."
        )

    for r in b.rows:
        icon = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"}[r["action"]]
        with st.container(border=True):
            cc = st.columns([1.2, 1, 1, 1, 2.2])
            cc[0].markdown(f"#### {icon} {r['action']} {r['asset']}")
            cc[1].metric("Trade", f"£{abs(r['trade_amount']):,.0f}" if r["action"] != "HOLD" else "–")
            cc[2].metric("Target", f"{r['target_share']:.0%} = £{r['target_amount']:,.0f}")
            cc[3].metric("You hold", f"£{r['current_amount']:,.0f}")
            cc[4].markdown(f"**When:** {r['when']}  \n**UK fund:** {r['uk_fund']}")
            st.markdown(
                f"**Why:** {r['reason']}.  \n**When to sell:** {r['exit_rule']}.  \n**Evidence:** {r['evidence']}."
            )
    if b.cash_after > 0.5:
        st.caption(f"Cash left after these trades: about £{b.cash_after:,.0f} (the strategy keeps it in cash).")

    if ms["open"]:
        st.markdown("#### Live preview (if today ended at the latest price)")
        if b.preview_changes:
            for x in b.preview_changes:
                st.warning(x)
            st.caption(
                "A preview, not a decision: the strategy decides on the closing price. Check again after "
                "the close (21:00 UK time)."
            )
        else:
            st.caption("At today's prices so far, the decision would not change.")

    st.download_button(
        "Download this decision (text)", DB.board_text(b), file_name=f"aurum-decision-{b.official_date.date()}.txt"
    )

    st.markdown("#### Charts (indicators the strategy uses, plus 50/200-day averages and RSI)")
    cols = st.columns(min(2, len(spec["universe"])))
    for k, t in enumerate(spec["universe"]):
        ov = {}
        for g in spec["signals"]:
            for cnd in g["conditions"]:
                for o in (cnd["left"], cnd["right"]):
                    if (
                        isinstance(o, dict)
                        and o["asset"] == t
                        and INDICATORS[o["ind"]].kind == "price"
                        and o["ind"] not in ("close", "sma")
                    ):
                        params = {kk: v for kk, v in o.items() if kk not in ("ind", "asset")}
                        ov[SP.operand_label(o)] = compute(o["ind"], completed[t], params)
        with cols[k % len(cols)]:
            st.plotly_chart(
                DC.mini_chart(
                    completed[t], t, overlays=ov, live=live.get(t), title=f"{t} · {DB.uk_fund(t).split(' or ')[0]}"
                ),
                width="stretch",
                theme="streamlit",
                key=f"mini_{t}",
            )


if auto:
    st.fragment(board_view, run_every="60s")()
else:
    board_view()

st.divider()
st.markdown("#### Watchlist: the other tickers today")
st.caption(
    "Readings for the ten research ETFs and whether this strategy's rules would be met for each. A description of "
    "today, not a forecast: no indicator has shown reliable predictive power in Aurum's experiments (EXP-038 to 043)."
)
if st.button("Scan the watchlist"):
    prices, errs = D.load_prices(list(D.UNIVERSE), "2018-01-01")
    st.session_state.db_scan = (D.scanner(spec, prices), prices, errs)
if st.session_state.get("db_scan"):
    tab, prices, errs = st.session_state.db_scan
    st.dataframe(
        tab,
        hide_index=True,
        width="stretch",
        column_config={
            k: st.column_config.NumberColumn(format="percent")
            for k in ("1-month return", "6-month return", "21-day volatility", "fall from 1-year high")
        },
    )
    pick = st.selectbox("Chart", list(prices))
    st.plotly_chart(
        DC.mini_chart(prices[pick], pick, title=f"{pick} · {DB.uk_fund(pick).split(' or ')[0]}"),
        width="stretch",
        theme="streamlit",
        key="mini_watch",
    )
    if errs:
        st.warning("Unavailable: " + "; ".join(errs))
