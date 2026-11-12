"""Portfolio: the Alpaca PAPER account plus anything held elsewhere, analysed as one portfolio (platform phase 8).

Read-only towards Alpaca: this page never places an order. Paper orders are switched off until the owner approves
(config `paper_orders.enabled`). Holdings entered by hand are kept in holdings.yaml on this computer (git-ignored;
on the free online server they last until it restarts).
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
import yaml

from aurum import broker as BR
from aurum import fx
from aurum import portfolio_opt as PO
from aurum.config import CFG, ROOT
from aurum.providers import alpaca_keys, get_provider

st.set_page_config(page_title="Aurum Portfolio", page_icon="💼", layout="wide")
HOLDINGS = ROOT / "holdings.yaml"
COLS = ["symbol", "quantity", "avg_price", "currency", "asset_class", "sector"]


@st.cache_resource(show_spinner=False)
def provider():
    return get_provider()


@st.cache_data(ttl=900, show_spinner="Loading prices...")
def closes(symbols: tuple, quarter_hour: int) -> pd.DataFrame:
    out = {}
    for s in symbols:
        try:
            out[s] = provider().bars(s, "1d", start=pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=420))["Close"]
        except Exception:
            pass
    df = pd.DataFrame(out)
    df.index = pd.DatetimeIndex(df.index.tz_convert("America/New_York").date) if len(df) else df.index
    return df


def load_manual() -> pd.DataFrame:
    try:
        rows = yaml.safe_load(HOLDINGS.read_text()) or []
    except FileNotFoundError:
        rows = []
    return pd.DataFrame(rows, columns=COLS)


st.title("💼 Portfolio")
st.markdown("**PAPER TRADING** · simulated money only. Nothing on this page places an order.")
po = BR.settings()
if not po["enabled"]:
    st.info(
        "Paper orders are **switched off** until you review everything and say OK. Aurum only reads the Alpaca "
        "paper account here."
    )

# ---- Alpaca paper account -----------------------------------------------------------------------------------
st.subheader("Alpaca paper account")
alp_rows, cash = [], 0.0
if alpaca_keys():
    try:
        b = BR.PaperBroker()
        acct = b.account()
        k = st.columns(4)
        k[0].metric("Status", f"{acct['status']} (paper)")
        k[1].metric("Equity", f"${float(acct['equity'] or 0):,.0f}")
        k[2].metric("Cash", f"${float(acct['cash'] or 0):,.0f}")
        k[3].metric("Buying power", f"${float(acct['buying_power'] or 0):,.0f}")
        cash = float(acct["cash"] or 0)
        for p in b.positions():
            alp_rows.append(
                {
                    "symbol": p["symbol"],
                    "quantity": float(p["qty"]),
                    "avg_price": float(p["avg_entry_price"]),
                    "currency": "USD",
                    "asset_class": p.get("asset_class", "us_equity").replace("us_equity", "stock"),
                    "sector": None,
                    "source": "alpaca",
                }
            )
        st.caption(f"{len(alp_rows)} positions. Open orders: {len(b.orders('open'))}.")
    except Exception as exc:
        st.warning(f"Could not read the Alpaca paper account: {exc}")
else:
    st.caption("No Alpaca keys on this computer: add them to .env (or the online app's Secrets) to see the account.")

# ---- holdings elsewhere ---------------------------------------------------------------------------------------
# ---- orders waiting for approval (the 50/50 experiment) --------------------------------------------------------
st.subheader("Orders yet to be approved")
from aurum import experiment as EX  # noqa: E402

props = EX.load()
proposed = [p for p in props.get("proposals", []) if p.get("status") == "proposed"]
# what Alpaca already has: an approved order must not show as "waiting" again after the page is refreshed (audit G3)
sent_status: dict[str, str] = {}
alpaca_orders: list[dict] = []
if alpaca_keys():
    try:
        alpaca_orders = BR.PaperBroker().orders("all", 500)
        sent_status = {o.get("client_order_id"): str(o.get("status")) for o in alpaca_orders}
    except Exception as exc:
        st.warning(f"Could not read Alpaca's orders, so already-sent orders may show as waiting: {exc}")


def _cid(p: dict) -> str:
    return EX.Proposal(**{k: p[k] for k in EX.Proposal.__dataclass_fields__}).request(
        EX.plan_id(props["asof"], p)
    ).client_id()  # fmt: skip


already = [(p, sent_status[_cid(p)]) for p in proposed if _cid(p) in sent_status]
waiting = [p for p in proposed if _cid(p) not in sent_status]
if not props:
    st.caption("No proposals yet: they are prepared on GitHub each weekday evening after the US close.")
elif not proposed:
    st.caption(f"Nothing waiting from the close of {props.get('asof')}.")
    for n in props.get("notes", []):
        if n.startswith("ACTION NEEDED"):
            st.error(n)
else:
    st.caption(
        f"Prepared from the close of {props['asof']} ({len(waiting)} waiting, {len(already)} already sent). Limit "
        "orders for the next session; swing buys carry their own stop and target at Alpaca. PAPER account only. "
        "Notes: " + " · ".join(props.get("notes", []))
    )
    for n in props.get("notes", []):
        if n.startswith("ACTION NEEDED"):
            st.error(n)
    if not waiting:
        st.success("Nothing left to approve: every order from this set has been sent (see below).")
    can_send = bool(alpaca_keys()) and po["enabled"]
    if not can_send:
        st.warning("Approving needs the Alpaca keys and paper orders switched on.")
    done = st.session_state.setdefault("approved_ids", set())

    def send(p: dict) -> str:
        if _cid(p) in done:
            return "already sent from this page"
        prov = provider()
        msg = EX.approve(p, props["asof"], BR.PaperBroker(), getattr(prov, "latest_trade", None))
        if msg.startswith("sent"):
            done.add(_cid(p))
        return msg

    def log(p: dict, msg: str) -> None:
        st.session_state.setdefault("approval_log", []).append(
            {
                "time (UK)": f"{pd.Timestamp.now(tz='Europe/London'):%H:%M:%S}",
                "symbol": p["symbol"],
                "side": p["side"],
                "result": msg,
            }
        )

    for i, p in enumerate(waiting):
        c = st.columns([1.1, 0.8, 1, 0.9, 1, 1, 4, 1.2])
        c[0].markdown(f"**{p['pot']}**")
        c[1].markdown("🟢 BUY" if p["side"] == "buy" else "🔴 SELL")
        c[2].markdown(f"**{p['symbol']}**")
        c[3].markdown(f"{p['qty']:g} sh")
        c[4].markdown(f"limit ${p['limit_price']:,.2f}" if p.get("limit_price") else "market")
        c[5].markdown(f"stop ${p['stop_loss']:,.2f}" if p.get("stop_loss") else "-")
        c[6].caption(p["reason"][:220].replace("$", "\\$"))
        if c[7].button("Approve", key=f"ap-{i}", disabled=not can_send):
            msg = send(p)
            log(p, msg)
            st.toast(f"{p['symbol']}: {msg}")
    if waiting and st.button(f"Approve all {len(waiting)}", type="primary", disabled=not can_send):
        for p in waiting:
            log(p, send(p))
    if st.session_state.get("approval_log"):
        st.markdown("**What happened to your approvals** (this session; newest last)")
        st.dataframe(pd.DataFrame(st.session_state["approval_log"]), use_container_width=True, hide_index=True)

st.subheader("Orders already sent")
STATUS_WORDS = {
    "new": "working at Alpaca", "accepted": "working at Alpaca", "pending_new": "working at Alpaca",
    "held": "working at Alpaca (waits for its partner order)", "partially_filled": "partly filled",
    "filled": "filled", "canceled": "cancelled", "expired": "expired unfilled", "rejected": "rejected by Alpaca",
    "replaced": "replaced", "done_for_day": "done for the day", "pending_cancel": "being cancelled",
}  # fmt: skip
if already:
    st.caption(f"From the set prepared at the close of {props['asof']}. These need nothing more from you.")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Pot": p["pot"],
                    "Side": p["side"].upper(),
                    "Symbol": p["symbol"],
                    "Shares": p["qty"],
                    "Limit $": p.get("limit_price"),
                    "Stop $": p.get("stop_loss"),
                    "Target $": p.get("take_profit"),
                    "At Alpaca": STATUS_WORDS.get(status, status),
                    "Why": p["reason"][:120],
                }
                for p, status in already
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.caption("None of the latest set has been sent yet.")
if alpaca_orders:
    with st.expander("Everything sent to Alpaca recently (newest first)"):
        recent = [
            {
                "Sent (UK)": f"{pd.Timestamp(o['submitted_at']).tz_convert('Europe/London'):%d %b %H:%M}"
                if o.get("submitted_at")
                else "",
                "Pot": BR.pot_of(o.get("client_order_id")) or "not Aurum",
                "Side": str(o.get("side", "")).upper(),
                "Symbol": o.get("symbol"),
                "Shares": o.get("qty"),
                "Type": o.get("order_class") or o.get("type"),
                "Status": STATUS_WORDS.get(str(o.get("status")), str(o.get("status"))),
                "Filled at $": o.get("filled_avg_price"),
            }
            for o in alpaca_orders[:40]
        ]
        st.dataframe(pd.DataFrame(recent), use_container_width=True, hide_index=True)

with st.expander("Emergency stop"):
    st.caption(
        "Blocks every new order (at Alpaca itself, so GitHub's nightly run and this page both see it) and cancels "
        "unfilled BUY orders. The stops and targets protecting positions you already hold are kept working."
    )
    if alpaca_keys():
        try:
            _b = BR.PaperBroker()
            _paused = _b.paused()
        except Exception:
            _b, _paused = None, False
        if _paused:
            st.error("Trading is PAUSED: no new orders can be sent.")
            if st.button("Resume trading") and _b is not None:
                ok = _b.resume()
                st.success("Resumed." if ok else "Resumed on this machine, but Alpaca did not confirm: check Alpaca.")
        elif st.button("Stop everything") and _b is not None:
            r = _b.cancel_all_and_pause("owner pressed Stop everything on the Portfolio page")
            st.error(
                f"Paused. {r['buys_cancelled']} unfilled buy orders cancelled; {r['protective_sells_kept']} "
                "protective stop/target orders kept. "
                + ("" if r["paused_at_alpaca"] else "Alpaca did NOT confirm the pause: it is set on this machine only.")
            )

st.subheader("Holdings elsewhere (entered by you)")
st.caption(
    "For anything not in the Alpaca paper account, e.g. a UK fund on another platform. Currency USD or GBP; "
    "asset class stock, etf, commodity etf, bond etf or other."
)
manual = st.data_editor(load_manual(), num_rows="dynamic", use_container_width=True, key="holdings")
c1, c2 = st.columns([1, 4])
if c1.button("Save holdings"):
    HOLDINGS.write_text(yaml.safe_dump(manual.dropna(subset=["symbol"]).to_dict("records")))
    st.success("Saved on this computer.")
extra_cash = c2.number_input("Cash held elsewhere (USD)", min_value=0.0, value=0.0, step=100.0)

holdings = [
    PO.Holding(r["symbol"], r["quantity"], r["avg_price"], "USD", r["asset_class"], None, "alpaca") for r in alp_rows
]
for _, r in manual.dropna(subset=["symbol", "quantity"]).iterrows():
    holdings.append(
        PO.Holding(
            str(r["symbol"]).upper(),
            float(r["quantity"]),
            float(r["avg_price"] or 0),
            str(r["currency"] or "USD").upper(),
            str(r["asset_class"] or "stock"),
            r["sector"] if isinstance(r["sector"], str) else None,
        )
    )
cash += extra_cash
if not holdings and cash == 0:
    st.info("No holdings yet. Once the experiment starts, the Alpaca paper positions appear here automatically.")
    st.stop()

# ---- analysis -------------------------------------------------------------------------------------------------
syms = tuple(sorted({h.symbol for h in holdings}))
px_df = closes(syms + ("SPY",), int(datetime.now().timestamp() // 900))
rets = px_df.pct_change(fill_method=None)
prices = {s: float(px_df[s].dropna().iloc[-1]) for s in px_df.columns if px_df[s].notna().any()}
try:
    rate = fx.rate()
except Exception:
    rate = fx.Rate(fx.SYNTHETIC_RATE, "-", "assumed")
pv = PO.view(holdings, prices, cash, rets, rate.usd_per_gbp)
k = st.columns(4)
k[0].metric("Total value", f"${pv.value:,.0f}", f"£{rate.to_gbp(pv.value):,.0f}")
k[1].metric("Volatility (yearly)", f"{pv.volatility:.1%}" if pv.volatility else "-")
k[2].metric("Effective number of holdings", f"{pv.concentration:.1f}")
k[3].metric("Cash", f"{cash / pv.value:.0%}" if pv.value else "-")
st.caption(f"Currency: {rate.label}. Volatility uses a year of daily returns with shrunk correlations.")
for n in pv.notes:
    st.warning(n)

a, b2 = st.columns(2)
with a:
    st.markdown("**By asset class**")
    st.plotly_chart(
        px.pie(values=pv.by_asset_class.values, names=pv.by_asset_class.index, hole=0.5).update_layout(
            height=300, margin=dict(l=0, r=0, t=0, b=0)
        ),
        use_container_width=True,
        key="ac",
    )
with b2:
    st.markdown("**Risk contribution** (share of the portfolio's swings each holding causes)")
    if len(pv.risk_contribution):
        rc = pv.risk_contribution.sort_values()
        st.plotly_chart(
            px.bar(x=rc.values, y=rc.index, orientation="h").update_layout(
                height=300, margin=dict(l=0, r=0, t=0, b=0), xaxis_tickformat=".0%", xaxis_title=None, yaxis_title=None
            ),
            use_container_width=True,
            key="rc",
        )
if len(pv.correlations) > 1:
    st.markdown("**How holdings move together** (1 = identically, 0 = unrelated)")
    st.plotly_chart(
        px.imshow(
            pv.correlations.round(2), text_auto=True, color_continuous_scale="RdBu_r", zmin=-1, zmax=1
        ).update_layout(height=360, margin=dict(l=0, r=0, t=0, b=0)),
        use_container_width=True,
        key="corr",
    )

# ---- try a candidate ------------------------------------------------------------------------------------------
st.subheader("Would a new idea fit?")
cc = st.columns([1, 1, 1, 2])
cand = cc[0].text_input("Ticker", "GLD").upper().strip()
w_add = cc[1].slider("Share of the portfolio", 0.01, 0.25, 0.05, 0.01)
kind = cc[2].selectbox("Kind", ["stock", "etf", "commodity etf"], index=2)
if cand:
    more = closes((cand,) + syms, int(datetime.now().timestamp() // 900)).pct_change(fill_method=None)
    chk = PO.check_candidate(pv, cand, more, w_add, kind)
    (cc[3].success if chk["verdict"] == "ok" else cc[3].error)(
        f"{cand}: {chk['verdict'].upper()}. " + " ".join(chk["problems"] + chk["notes"])
    )

# ---- allocation methods ----------------------------------------------------------------------------------------
st.subheader("Four ways to split the money")
pick = st.multiselect("Instruments", sorted(set(syms) | {"SPY", "GLD", "TLT"}), default=sorted(set(syms))[:6])
if len(pick) >= 2:
    data = closes(tuple(pick), int(datetime.now().timestamp() // 900)).pct_change(fill_method=None).dropna(how="all")
    kinds = {h.symbol: ("stock" if h.asset_class == "stock" else "etf") for h in holdings}
    t = PO.compare(data, [p for p in pick if p in data.columns], kinds)
    show = t.copy()
    st.dataframe(
        show.style.format(lambda v: f"{v:.1%}" if isinstance(v, float) and abs(v) <= 1.5 else f"{v:.2f}"),
        use_container_width=True,
    )
    st.caption(
        "Each method rests on different assumptions; none is best in general. Mean-variance is tilted only "
        "weakly by scanner scores (a guess, not a forecast). Caps: 10% per company, 25% per fund; anything "
        "the caps leave over stays in cash."
    )

# ---- experiment pots ------------------------------------------------------------------------------------------
st.subheader("Experiment pots (long-term vs swing)")
exp = CFG.get("experiment", {})
if not alpaca_keys():
    st.caption("Needs the Alpaca keys.")
else:
    try:
        b = BR.PaperBroker()
        pots = BR.ledgers_from_orders(b.orders_all(), exp.get("pots", {"long-term": 50_000, "swing": 50_000}))
        rows = []
        for name, led in pots.items():
            mv = sum(p["qty"] * prices.get(s, p["cost"] / max(p["qty"], 1e-9)) for s, p in led["positions"].items())
            rows.append(
                {
                    "pot": name,
                    "cash": led["cash"],
                    "invested": mv,
                    "value": led["cash"] + mv,
                    "realised P&L": led["realised"],
                    "fills": led["fills"],
                }
            )
        st.dataframe(pd.DataFrame(rows).set_index("pot").style.format("{:,.2f}"), use_container_width=True)
        diff = BR.reconcile(pots, b.positions())
        (st.success if not diff else st.error)("Aurum's records match Alpaca." if not diff else "; ".join(diff))
    except Exception as exc:
        st.warning(f"Pots not available: {exc}")
eq = ROOT / "research" / "orders" / "equity.csv"
if eq.is_file():
    e = pd.read_csv(eq, index_col=0, parse_dates=True)
    st.plotly_chart(px.line(e, title="Value over time").update_layout(height=320), use_container_width=True, key="eq")
    dd = e / e.cummax() - 1
    st.plotly_chart(
        px.area(dd, title="Fall from peak").update_layout(height=240, yaxis_tickformat=".0%"),
        use_container_width=True,
        key="dd",
    )
else:
    st.caption("The value-over-time and drawdown charts start once the experiment begins (recorded daily on GitHub).")
