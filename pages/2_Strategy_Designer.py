"""Strategy Designer: build a strategy from parts, see every decision on linked charts, compare it, research it and
send it for a Fair Test.   Run the dashboard with:  python -m streamlit run app.py

Everything here is a historical backtest or simulated paper trading. No real-money orders exist anywhere in Aurum.
"""

from __future__ import annotations

import copy
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from aurum import designer as D
from aurum import designer_charts as DC
from aurum import engine as E
from aurum import fairtest as FT
from aurum import gates
from aurum import registry as R
from aurum import spec as SP
from aurum.config import CFG, code_fingerprint
from aurum.indicators import INDICATORS

IND_NAMES = {
    "close": "Price (close)",
    "sma": "Simple moving average",
    "ema": "Exponential moving average",
    "bb_upper": "Bollinger band, upper",
    "bb_lower": "Bollinger band, lower",
    "donchian_high": "n-day high",
    "donchian_low": "n-day low",
    "rsi": "RSI",
    "momentum": "n-day return",
    "volatility": "Volatility",
    "drawdown": "Fall from n-day high",
    "zscore": "Z-score",
    "macd_hist": "MACD histogram",
    "atr_pct": "ATR % of price",
}

st.set_page_config(page_title="Aurum Strategy Designer", page_icon="🧭", layout="wide")


# ---------------------------------------------------------------------------------------------------------------
# state and data
# ---------------------------------------------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def registry():
    return R.Registry()


@st.cache_data(ttl=600, show_spinner="Loading daily prices...")
def prices_for(tickers: tuple, start: str):
    return D.load_prices(list(tickers), start)


def cash_rate(idx: pd.DatetimeIndex) -> pd.Series:
    from aurum import data

    return data.cash_rate(idx, CFG)


@st.cache_data(ttl=3600, show_spinner=False)
def fx_series(start: str):
    return D.gbp_usd(start)


def library() -> dict:
    return SP.library()


def working() -> dict:
    if "spec" not in st.session_state:
        st.session_state.spec = copy.deepcopy(library().get("spy-gld-70-30-monthly"))
        st.session_state.edits = 0
    return st.session_state.spec


WIDGET_PREFIXES = (
    "bw_",
    "lab_",
    "cmb_",
    "k_",
    "app_",
    "wt_",
    "wf_",
    "unk_",
    "li_",
    "la_",
    "lp_",
    "op_",
    "rt_",
    "rv_",
    "ri_",
    "rp_",
    "cost_",
    "w_",
)


def reset_widgets():
    """Forget the builder's widget values so a newly loaded strategy shows its own settings."""
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and k.startswith(WIDGET_PREFIXES):
            del st.session_state[k]


def set_working(s: dict, count_edit: bool = True):
    st.session_state.spec = s
    if count_edit:
        st.session_state.edits = st.session_state.get("edits", 0) + 1


def run_for(spec: dict, start: str, capital: float):
    """Backtest (cached on the definition, start date and capital)."""
    key = (SP.spec_hash(spec), start, capital)
    cache = st.session_state.setdefault("runs", {})
    if key in cache:
        return cache[key]
    tickers = tuple(sorted(set(SP.assets_needed(spec)) | {"SPY", "GLD"}))
    prices, errors = prices_for(tickers, start)
    if errors:
        raise RuntimeError("; ".join(f"{t}: {e}" for t, e in errors.items()))
    idx = None
    for t in SP.assets_needed(spec):
        idx = prices[t].index if idx is None else idx.intersection(prices[t].index)
    idx = idx[idx >= pd.Timestamp(start)].sort_values()
    rf = cash_rate(idx)
    run = E.run_spec(spec, prices, rf, capital=capital, index=idx)
    cache[key] = (run, prices, rf, idx)
    reg = registry()
    h = reg.register(spec)
    dev = E.slice_daily(run.daily, *D.DEV)["ret"]
    ex = dev - E.risk_free_daily(rf, dev.index)
    reg.log_run(
        h,
        "designer",
        period="dev",
        data_label=D.data_label(prices),
        code_fp=code_fingerprint(),
        sharpe_daily=float(ex.mean() / ex.std(ddof=1)) if len(ex) > 2 and ex.std(ddof=1) > 0 else None,
        metrics={
            k: (str(v) if not isinstance(v, (int, float)) or v is None else v)
            for k, v in E.summary(run, *D.DEV).items()
        },
    )
    return cache[key]


STATE_WORD = {True: "met", False: "not met", None: "not yet known"}


def money(x, cur):
    return ("£" if cur == "GBP" else "$") + f"{x:,.0f}"


def fmt(x, kind="pct"):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "–"
    return {"pct": f"{x:.1%}", "num": f"{x:.2f}", "int": f"{x:,.0f}"}[kind]


# ---------------------------------------------------------------------------------------------------------------
# sidebar
# ---------------------------------------------------------------------------------------------------------------
st.title("🧭 Strategy Designer")
st.caption(
    "Build a strategy from indicators and rules, see exactly when it would buy and sell, and test it fairly. "
    "Every number is a historical backtest net of costs (or simulated paper trading); nothing here places a real order."
)
lib = library()
with st.sidebar:
    st.subheader("Strategy")
    names = {s["name"]: k for k, s in lib.items()}
    pick = st.selectbox("Load a saved strategy or template", ["(keep working copy)"] + list(names))
    if st.button("Load", disabled=pick == "(keep working copy)"):
        reset_widgets()
        set_working(copy.deepcopy(lib[names[pick]]), count_edit=False)
        st.session_state.edits = 0
        st.rerun()
    st.subheader("Backtest settings")
    start = st.text_input(
        "First date of data", value=SP.DEFAULT_START, help="Earliest date downloaded (ETFs from mid-2006)."
    )
    capital = float(
        st.number_input("Starting money ($)", value=float(CFG["paper"]["starting_cash"]), min_value=100.0, step=1000.0)
    )
    currency = st.radio(
        "Show amounts in",
        ["USD", "GBP"],
        horizontal=True,
        help="The assets trade in US dollars. Pounds use each day's GBP/USD rate, so they include currency moves.",
    )
    if st.button("Refresh data"):
        st.cache_data.clear()
        st.session_state.pop("runs", None)
        st.rerun()

spec = working()

try:
    spec_ok = SP.validate(spec)
    spec_err = None
except SP.SpecError as exc:
    spec_ok, spec_err = None, str(exc)

fx = fx_series(start) if currency == "GBP" else None
if currency == "GBP" and fx is None:
    st.sidebar.warning("GBP/USD rate unavailable (offline or download failed): amounts shown in USD.")
    currency = "USD"

tabs = st.tabs(
    ["1 · Design", "2 · Charts & results", "3 · Compare", "4 · Fair Test & approval", "5 · Research lab", "6 · Scanner"]
)

# ---------------------------------------------------------------------------------------------------------------
# 1 design
# ---------------------------------------------------------------------------------------------------------------
with tabs[0]:
    s = copy.deepcopy(SP.normalise(spec))
    c1, c2, c3 = st.columns([2, 2, 1])
    s["name"] = c1.text_input("Name", s.get("name", ""))
    s["id"] = c2.text_input("Id (file name)", s.get("id", ""))
    c3.metric("Version", s["version"])
    s["description"] = st.text_area("Description", s.get("description", ""), height=70)

    st.markdown("#### Assets and starting weights")
    uni = st.multiselect(
        "Assets the strategy may hold",
        key="w_universe",
        options=list(D.UNIVERSE),
        default=[t for t in s["universe"] if t in D.UNIVERSE],
        format_func=lambda t: f"{t} · {D.UNIVERSE[t]}",
    )
    cols = st.columns(max(1, len(uni)) + 1)
    bw = {}
    for i, t in enumerate(uni):
        bw[t] = round(
            cols[i].number_input(
                f"{t} %", 0.0, 100.0, round(float(s["base_weights"].get(t, 0.0) * 100), 4), 5.0, key=f"bw_{t}"
            )
            / 100,
            6,
        )
    cols[-1].metric("Cash", f"{max(0.0, 1 - sum(bw.values())):.0%}")
    s["universe"], s["base_weights"] = uni, bw

    st.markdown("#### When it trades")
    c1, c2, c3 = st.columns(3)
    s["schedule"]["rebalance"] = c1.selectbox(
        "Rebalance", SP.SCHEDULES, index=SP.SCHEDULES.index(s["schedule"]["rebalance"])
    )
    s["schedule"]["band"] = c2.slider(
        "No-trade band (share of account)",
        0.0,
        0.20,
        float(s["schedule"]["band"]),
        0.01,
        help="Only trade an asset when it is more than this far from its target.",
    )
    s["schedule"]["act_on_signal_change"] = c3.checkbox(
        "Also trade the day a rule flips", s["schedule"]["act_on_signal_change"]
    )

    st.markdown("#### Position sizing")
    c1, c2, c3, c4 = st.columns(4)
    s["sizing"]["method"] = c1.selectbox(
        "Method",
        SP.SIZING,
        index=SP.SIZING.index(s["sizing"]["method"]),
        format_func=lambda m: {
            "fixed": "Fixed weights",
            "vol_cap": "Risk cap (cut when volatile)",
            "inverse_vol": "Risk balance (1/volatility)",
        }[m],
    )
    s["sizing"]["target_vol"] = round(
        c2.number_input("Target volatility %", 1.0, 100.0, round(s["sizing"]["target_vol"] * 100, 4), 1.0) / 100, 6
    )
    s["sizing"]["vol_window"] = int(c3.number_input("Volatility window (days)", 2, 504, s["sizing"]["vol_window"], 1))
    s["sizing"]["max_weight"] = round(
        c4.number_input("Max per asset %", 1.0, 100.0, round(s["sizing"]["max_weight"] * 100, 4), 5.0) / 100, 6
    )

    st.markdown("#### Rules (indicators that change how much is invested)")
    st.caption(
        "Each rule multiplies the normal share of the assets it applies to: e.g. 100% when the "
        "condition is met, 0% (cash) when not."
    )
    ind_keys = list(INDICATORS)
    new_sigs = []
    for gi, g in enumerate(s["signals"]):
        with st.expander(f"Rule {gi + 1}: {g['label']}", expanded=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            g["label"] = c1.text_input("Label", g["label"], key=f"lab_{gi}")
            g["combine"] = c2.selectbox(
                "Combine conditions",
                SP.COMBINE,
                index=SP.COMBINE.index(g["combine"]),
                key=f"cmb_{gi}",
                format_func=lambda x: {"all": "ALL (and)", "any": "ANY (or)", "k_of_n": "at least k"}[x],
            )
            g["k"] = int(
                c3.number_input(
                    "k", 1, max(1, len(g["conditions"])), min(g["k"], max(1, len(g["conditions"]))), key=f"k_{gi}"
                )
            )
            c1, c2, c3, c4 = st.columns(4)
            g["apply_to"] = c1.multiselect(
                "Applies to", uni, default=[t for t in g["apply_to"] if t in uni], key=f"app_{gi}"
            )
            g["when_true"] = round(
                c2.number_input(
                    "Hold % of normal when met", 0.0, 100.0, round(g["when_true"] * 100, 4), 10.0, key=f"wt_{gi}"
                )
                / 100,
                6,
            )
            g["when_false"] = round(
                c3.number_input(
                    "Hold % of normal when not met", 0.0, 100.0, round(g["when_false"] * 100, 4), 10.0, key=f"wf_{gi}"
                )
                / 100,
                6,
            )
            g["assume_when_unknown"] = c4.checkbox(
                "Assume met before enough history", g["assume_when_unknown"], key=f"unk_{gi}"
            )
            new_conds = []
            for ci, c in enumerate(g["conditions"]):
                cc = st.columns([2, 1.2, 2.2, 1.2, 1.2, 2, 1.2, 0.6])
                left = c["left"] if isinstance(c["left"], dict) else {"ind": "close", "asset": uni[0] if uni else "SPY"}
                li = cc[0].selectbox(
                    "Indicator",
                    ind_keys,
                    index=ind_keys.index(left["ind"]),
                    key=f"li_{gi}_{ci}",
                    format_func=lambda k: IND_NAMES.get(k, k),
                )
                la = cc[1].selectbox(
                    "of",
                    list(D.UNIVERSE),
                    index=list(D.UNIVERSE).index(left["asset"]) if left["asset"] in D.UNIVERSE else 0,
                    key=f"la_{gi}_{ci}",
                )
                lop = {"ind": li, "asset": la}
                for p in INDICATORS[li].params:
                    cur = left.get(p.name, p.default) if left["ind"] == li else p.default
                    lop[p.name] = cc[2].number_input(
                        f"{p.name}", float(p.lo), float(p.hi), float(cur), float(p.step), key=f"lp_{gi}_{ci}_{p.name}"
                    )
                    if p.integer:
                        lop[p.name] = int(lop[p.name])
                op = cc[3].selectbox("is", SP.OPS, index=SP.OPS.index(c["op"]), key=f"op_{gi}_{ci}")
                rtype = cc[4].selectbox(
                    "than",
                    ["number", "indicator"],
                    index=0 if isinstance(c["right"], float) else 1,
                    key=f"rt_{gi}_{ci}",
                )
                if rtype == "number":
                    unit = INDICATORS[li].unit
                    rv = float(c["right"]) if isinstance(c["right"], float) else 0.0
                    shown = cc[5].number_input(
                        "value" + (" (%)" if unit == "%" else ""),
                        value=rv * (100 if unit == "%" else 1),
                        key=f"rv_{gi}_{ci}",
                    )
                    right = round(shown / (100 if unit == "%" else 1), 10)
                else:
                    r0 = c["right"] if isinstance(c["right"], dict) else {"ind": "sma", "asset": la, "n": 200}
                    ri = cc[5].selectbox(
                        "indicator (same asset)",
                        ind_keys,
                        index=ind_keys.index(r0["ind"]),
                        key=f"ri_{gi}_{ci}",
                        format_func=lambda k: IND_NAMES.get(k, k),
                    )
                    right = {"ind": ri, "asset": la}
                    for p in INDICATORS[ri].params:
                        cur = r0.get(p.name, p.default) if r0["ind"] == ri else p.default
                        v = cc[6].number_input(
                            f"{p.name} ",
                            float(p.lo),
                            float(p.hi),
                            float(cur),
                            float(p.step),
                            key=f"rp_{gi}_{ci}_{p.name}",
                        )
                        right[p.name] = int(v) if p.integer else v
                keep = not cc[7].button("✕", key=f"del_{gi}_{ci}", help="Remove condition")
                if keep:
                    new_conds.append({"left": lop, "op": op, "right": right})
            g["conditions"] = new_conds
            b1, b2 = st.columns(2)
            if b1.button("+ condition", key=f"addc_{gi}"):
                g["conditions"].append(
                    {"left": {"ind": "rsi", "asset": uni[0] if uni else "SPY", "n": 14}, "op": "<", "right": 70.0}
                )
            if not b2.button("Remove rule", key=f"delg_{gi}"):
                new_sigs.append(g)
    s["signals"] = new_sigs
    if st.button("+ rule"):
        a0 = uni[0] if uni else "SPY"
        used = {g["id"] for g in s["signals"]}
        nid = next(f"rule_{i}" for i in range(1, 100) if f"rule_{i}" not in used)
        s["signals"].append(
            {
                "id": nid,
                "label": f"{a0} above its 200-day average",
                "conditions": [
                    {"left": {"ind": "close", "asset": a0}, "op": ">", "right": {"ind": "sma", "asset": a0, "n": 200}}
                ],
                "combine": "all",
                "apply_to": [a0],
                "when_true": 1.0,
                "when_false": 0.0,
            }
        )

    st.markdown("#### Exits and brakes")
    c1, c2 = st.columns(2)
    ts_on = c1.checkbox("Trailing stop per asset", "trailing_stop" in s["exits"])
    if ts_on:
        ts = s["exits"].get("trailing_stop", {"pct": 0.15, "cooldown_days": 21})
        s["exits"]["trailing_stop"] = {
            "pct": round(
                c1.number_input(
                    "Sell after a fall from the peak of (%)", 1.0, 90.0, round(float(ts["pct"]) * 100, 4), 1.0
                )
                / 100,
                6,
            ),
            "cooldown_days": int(
                c1.number_input("Days out before re-entering", 0, 252, int(ts.get("cooldown_days", 21)))
            ),
        }
    else:
        s["exits"].pop("trailing_stop", None)
    ad_on = c2.checkbox("Account drawdown brake", "account_drawdown" in s["exits"])
    if ad_on:
        ad = s["exits"].get("account_drawdown", {"trigger": 0.2, "release": 0.1, "scale": 0.5})
        s["exits"]["account_drawdown"] = {
            "trigger": round(
                c2.number_input("Brake when the account is down (%)", 1.0, 90.0, round(float(ad["trigger"]) * 100, 4))
                / 100,
                6,
            ),
            "release": round(
                c2.number_input("Release when back within (%)", 1.0, 90.0, round(float(ad["release"]) * 100, 4)) / 100,
                6,
            ),
            "scale": c2.number_input("Multiply targets by", 0.0, 1.0, float(ad["scale"]), 0.1),
        }
    else:
        s["exits"].pop("account_drawdown", None)

    st.markdown("#### Execution and benchmark")
    c1, c2, c3 = st.columns(3)
    s["execution"]["fill"] = c1.selectbox(
        "Orders fill at the next day's", ["open", "close"], index=["open", "close"].index(s["execution"]["fill"])
    )
    s["execution"]["costs_bps"] = {
        t: c2.number_input(
            f"{t} cost per trade (bps)",
            0.0,
            100.0,
            float(s["execution"]["costs_bps"].get(t, SP.DEFAULT_COSTS.get(t, 10))),
            1.0,
            key=f"cost_{t}",
        )
        for t in uni
    }
    bopts = ["SPY"] + [k for k in lib if k != s["id"]]
    s["benchmark"] = c3.selectbox(
        "Fair Test benchmark",
        bopts,
        index=bopts.index(s["benchmark"]) if s["benchmark"] in bopts else 0,
        format_func=lambda k: lib[k]["name"] if k in lib else f"{k} buy and hold",
    )

    if SP.normalise(s) != SP.normalise(spec):
        set_working(s)
        st.rerun()

    st.divider()
    if spec_err:
        st.error(f"This strategy can't run yet: {spec_err}")
    else:
        st.markdown("#### What this strategy does")
        for line in D.describe(spec_ok):
            st.markdown(f"- {line}")
        h = SP.spec_hash(spec_ok)
        reg = registry()
        st.caption(
            f"Definition fingerprint (spec hash) `{h}` · registry status **{reg.status(h)}** · edits "
            f"this session: {st.session_state.get('edits', 0)}"
        )
        c1, c2, c3 = st.columns(3)
        saved = lib.get(spec_ok["id"])
        changed = saved is not None and SP.spec_hash(saved) != h
        if c1.button("Save to strategy library" + (" (new version)" if changed else "")):
            to_save = copy.deepcopy(spec_ok)
            if changed:
                to_save["version"] = int(saved["version"]) + 1
            path = SP.save(to_save)
            reset_widgets()
            set_working(SP.load(path), count_edit=False)
            st.success(f"Saved {path.name} (version {to_save['version']}).")
        c2.download_button("Download definition (YAML)", SP.dump(spec_ok), file_name=f"{spec_ok['id']}.yaml")
        c3.download_button(
            "Download definition (JSON)", json.dumps(spec_ok, indent=1), file_name=f"{spec_ok['id']}.json"
        )
        if saved is not None and changed and saved["id"] in ("spy-gld-70-30-monthly", "spy-gld-70-30-risk-cap"):
            st.warning(
                "You have changed a strategy that is approved for paper trading. Saving creates a new "
                "version with a new fingerprint; the paper trader keeps trading the approved version until "
                "you approve the new one."
            )

# ---------------------------------------------------------------------------------------------------------------
# 2 charts and results
# ---------------------------------------------------------------------------------------------------------------
with tabs[1]:
    if spec_err:
        st.error(spec_err)
    else:
        try:
            run, prices, rf, idx = run_for(spec_ok, start, capital)
            spy, _, _, _ = (
                run_for(lib["spy-buy-and-hold"], start, capital) if "spy-buy-and-hold" in lib else (None,) * 4
            )
            mix, _, _, _ = (
                run_for(lib["spy-gld-70-30-monthly"], start, capital) if "spy-gld-70-30-monthly" in lib else (None,) * 4
            )
        except Exception as exc:
            st.error(f"Backtest failed: {exc}")
            st.stop()
        label = D.data_label(prices)
        if CFG.get("offline"):
            st.warning("OFFLINE MODE: synthetic test data, not real prices. Results mean nothing about markets.")
        st.caption(f"{label} · definition `{run.meta['spec_hash']}` · code `{code_fingerprint()}`")

        show_hold = st.toggle(
            "Include the 2024+ holdout period",
            value=False,
            help="The holdout is kept for confirming results. Looking at it while designing weakens it; "
            "each look is counted.",
        )
        if show_hold and not st.session_state.get(f"hv_{run.meta['spec_hash']}"):
            registry().view_holdout(run.meta["spec_hash"], "designer")
            st.session_state[f"hv_{run.meta['spec_hash']}"] = True
        end_default = idx[-1] if show_hold else min(idx[-1], D.DEV[1])
        c1, c2 = st.columns([1, 3])
        focus = c1.selectbox("Price chart asset", spec_ok["universe"])
        rng = c2.slider(
            "Dates shown",
            min_value=idx[0].date(),
            max_value=end_default.date(),
            value=(max(idx[0], end_default - pd.DateOffset(years=3)).date(), end_default.date()),
        )

        # results box
        lo, hi = pd.Timestamp(rng[0]), pd.Timestamp(rng[1])
        sm = E.summary(run, lo, hi)
        bench = {n: r for n, r in (("SPY buy & hold", spy), ("70/30 monthly", mix)) if r is not None and r is not run}
        st.markdown(f"#### Results, {rng[0]} to {rng[1]} (historical backtest, net of costs)")
        conv = 1.0
        if currency == "GBP":
            conv = float(fx.reindex(run.daily.index).ffill().bfill().loc[:hi].iloc[-1])
        m = st.columns(8)
        m[0].metric(
            "Final value",
            money(sm["final_value"] / conv, currency),
            help=f"{money(capital / conv, currency)} invested at the start of the dates shown",
        )
        m[1].metric("Return a year (CAGR)", fmt(sm["cagr"]))
        m[2].metric("Sharpe ratio", fmt(sm["sharpe"], "num"), help="Return above cash per unit of risk")
        m[3].metric(
            "Worst fall",
            fmt(sm["max_drawdown"]),
            help=f"{sm['max_drawdown_peak']} to {sm['max_drawdown_trough']}; "
            f"recovered {sm['recovered_on'] or 'not yet'}",
        )
        m[4].metric("Volatility", fmt(sm["volatility"]))
        m[5].metric("Costs a year", fmt(sm["costs_per_year"]))
        m[6].metric("Orders a year", f"{sm['orders_per_year']:.1f}")
        m[7].metric("Average invested", fmt(sm["avg_exposure"]))
        rows = []
        for n, r in {spec_ok["name"]: run, **bench}.items():
            x = E.summary(r, lo, hi)
            rows.append(
                {
                    "strategy": n,
                    "CAGR": fmt(x["cagr"]),
                    "Sharpe": fmt(x["sharpe"], "num"),
                    "Sortino": fmt(x["sortino"], "num"),
                    "worst fall": fmt(x["max_drawdown"]),
                    "volatility": fmt(x["volatility"]),
                    "best year": fmt(x["best_year"]),
                    "worst year": fmt(x["worst_year"]),
                    "costs/yr": fmt(x["costs_per_year"]),
                    "orders": x["orders"],
                }
            )
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        per = {"pre-2013": (idx[0], pd.Timestamp("2013-10-17")), "development 2013-2023": D.DEV}
        if show_hold:
            per["holdout 2024+"] = (D.HOLDOUT_START, idx[-1])
        prow = []
        for pn, (a, b) in per.items():
            for n, r in {spec_ok["name"]: run, **bench}.items():
                x = E.summary(r, a, b)
                if x.get("days", 0) and x.get("days", 0) < 2:
                    continue
                prow.append(
                    {
                        "period": pn,
                        "strategy": n,
                        "CAGR": fmt(x.get("cagr")),
                        "Sharpe": fmt(x.get("sharpe"), "num"),
                        "worst fall": fmt(x.get("max_drawdown")),
                    }
                )
        with st.expander("By period", expanded=False):
            st.dataframe(pd.DataFrame(prow), hide_index=True, width="stretch")

        warns = R.overfitting_warnings(registry(), run.meta["spec_hash"], st.session_state.get("edits", 0))
        with st.expander("⚠️ Luck and overfitting check", expanded=st.session_state.get("edits", 0) >= 10):
            for w in warns:
                st.markdown(f"- {w}")

        fig = DC.decision_chart(run, focus, bench, currency=currency, fx=fx, start=lo, end=hi, data_label=label)
        st.plotly_chart(fig, width="stretch", theme="streamlit", config={"scrollZoom": True, "displaylogo": False})
        st.caption(
            "All panels share one time axis: zoom or drag on any panel and the others follow; hover a "
            "date to see what the strategy knew at that close "
            "and what it did. Triangles are orders (size = share of the account). Blue shading = the "
            "rule's condition was met."
        )

        st.markdown("#### Explain a day")
        day = st.date_input("Date", value=hi.date(), min_value=idx[0].date(), max_value=hi.date())
        ex = E.explain_day(run, day)

        def fx_on(d):
            """US dollars per pound on date d (1 when showing dollars)."""
            if currency != "GBP":
                return 1.0
            return float(fx.reindex([pd.Timestamp(d)], method="pad").iloc[0])

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                f"**Close of {ex['date']}** · {ex['data_used']} · "
                f"rebalance day: **{'yes' if ex['rebalance_day'] else 'no'}**"
            )
            for sg in ex["signals"]:
                st.markdown(f"- Rule *{sg['label']}*: **{STATE_WORD[sg['met']]}**")
                for cd in sg["conditions"]:
                    st.markdown(
                        f"  - {cd['rule']}: {cd['values'][0]:,.4g} vs {cd['values'][1]:,.4g} → {STATE_WORD[cd['met']]}"
                    )
            if ex["orders_next_session"]:
                for o in ex["orders_next_session"]:
                    st.markdown(
                        f"- **{o['side']} {o['ticker']} {money(o['amount'] / fx_on(o['fill_date']), currency)}** "
                        f"({o['pct_of_account']:.1%} of the account), filled {o['fill_date']}, "
                        f"fee {money(o['fee'], 'USD')}"
                    )
            else:
                st.markdown("- No order decided at this close.")
        with c2:
            st.dataframe(
                pd.DataFrame(ex["assets"]).T.rename(
                    columns={
                        "base_weight": "base",
                        "sizing_multiplier": "sizing ×",
                        "exit_multiplier": "exit ×",
                        "target_weight": "target",
                        "actual_weight_at_close": "held",
                    }
                ),
                width="stretch",
            )

        st.markdown("#### Orders")
        tr = run.trades.copy()
        if len(tr):
            tr = tr[(tr["date"] >= lo) & (tr["date"] <= hi)]
            f = 1.0 if currency == "USD" else fx.reindex(pd.DatetimeIndex(tr["date"])).ffill().to_numpy()
            tr["amount"] = tr["notional"] / f
            show = tr[
                [
                    "decided",
                    "date",
                    "ticker",
                    "side",
                    "amount",
                    "pct_of_account",
                    "cost",
                    "from_weight",
                    "to_weight",
                    "reason",
                ]
            ].rename(columns={"decided": "decided at close", "date": "filled", "cost": "fee ($)"})
            st.dataframe(
                show,
                hide_index=True,
                width="stretch",
                column_config={
                    "amount": st.column_config.NumberColumn(f"amount ({currency})", format="%.0f"),
                    "pct_of_account": st.column_config.NumberColumn("% of account", format="percent"),
                    "from_weight": st.column_config.NumberColumn(format="percent"),
                    "to_weight": st.column_config.NumberColumn(format="percent"),
                },
            )
        c1, c2, c3 = st.columns(3)
        c1.download_button(
            "Download daily results (CSV)",
            run.daily.join(run.result.weights.add_suffix(" weight")).to_csv(),
            file_name=f"{spec_ok['id']}-daily.csv",
        )
        c2.download_button(
            "Download orders (CSV)", run.trades.to_csv(index=False), file_name=f"{spec_ok['id']}-orders.csv"
        )
        c3.download_button(
            "Download chart (HTML)", fig.to_html(include_plotlyjs="cdn"), file_name=f"{spec_ok['id']}-chart.html"
        )

# ---------------------------------------------------------------------------------------------------------------
# 3 compare
# ---------------------------------------------------------------------------------------------------------------
with tabs[2]:
    st.markdown("Compare saved strategies (and your working copy) on the same dates and the same starting money.")
    opts = {s["name"]: s for s in lib.values()}
    if (
        spec_ok
        and spec_ok["id"] not in lib
        or (spec_ok and SP.spec_hash(spec_ok) != SP.spec_hash(lib.get(spec_ok["id"], spec_ok)))
    ):
        opts[f"Working copy: {spec_ok['name']}"] = spec_ok
    chosen = st.multiselect("Strategies", list(opts), default=[n for n in opts if "70/30" in n][:3])
    if chosen:
        runs = {}
        for n in chosen:
            try:
                runs[n] = run_for(opts[n], start, capital)[0]
            except Exception as exc:
                st.error(f"{n}: {exc}")
        if runs:
            st.plotly_chart(DC.comparison_chart(runs, currency, fx), width="stretch", theme="streamlit")
            idxc = None
            for r in runs.values():
                idxc = r.daily.index if idxc is None else idxc.intersection(r.daily.index)
            rows = []
            for n, r in runs.items():
                x = E.summary(r, idxc[0], idxc[-1])
                rows.append(
                    {
                        "strategy": n,
                        "CAGR": fmt(x["cagr"]),
                        "Sharpe": fmt(x["sharpe"], "num"),
                        "worst fall": fmt(x["max_drawdown"]),
                        "volatility": fmt(x["volatility"]),
                        "costs/yr": fmt(x["costs_per_year"]),
                        "orders/yr": f"{x['orders_per_year']:.1f}",
                    }
                )
                for w, (a, b) in {
                    "2008-09 recession": ("2007-12-01", "2009-06-30"),
                    "2020 Covid crash": ("2020-02-01", "2020-04-30"),
                    "2022 rate rises": ("2022-01-01", "2022-10-31"),
                }.items():
                    ret, mdd = E.window_return(r, a, b)
                    rows[-1][w] = fmt(ret)
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
            st.caption(
                f"Common dates {idxc[0].date()} to {idxc[-1].date()} (includes the 2024+ holdout). "
                "Historical backtests, net of costs."
            )
            st.download_button(
                "Download comparison (CSV)", pd.DataFrame(rows).to_csv(index=False), file_name="comparison.csv"
            )

# ---------------------------------------------------------------------------------------------------------------
# 4 fair test and approval
# ---------------------------------------------------------------------------------------------------------------
with tabs[3]:
    if spec_err:
        st.error(spec_err)
    else:
        reg = registry()
        h = SP.spec_hash(spec_ok)
        reg.register(spec_ok)
        saved = FT.latest_results()
        st.markdown(f"**{spec_ok['name']}** · fingerprint `{h}` · status **{reg.status(h)}**")
        st.caption(
            "The Fair Test checks data, look-ahead and accounting, then compares the strategy with its "
            "benchmark using the same pre-registered rules "
            "as every Aurum experiment: development period first, then 2x costs, execution delay, "
            "sensitivity to its own numbers, luck (deflated Sharpe) "
            "and finally confirmation on both the 2024+ holdout and pre-2013. A pass is evidence, not permission."
        )
        if st.button("🧪 Send for Fair Test", type="primary"):
            bar = st.progress(0.0, text="starting")
            try:
                if reg.status(h) not in ("draft", "testing"):
                    reg.set_status(h, "testing", note="re-test from designer")
                elif reg.status(h) == "draft":
                    reg.set_status(h, "testing", note="sent from designer")
                tickers = tuple(
                    sorted(set(SP.assets_needed(spec_ok)) | set(SP.assets_needed(FT.benchmark_spec(spec_ok, lib))))
                )
                prices, errors = prices_for(tickers, start)
                idx = None
                for p in prices.values():
                    idx = p.index if idx is None else idx.union(p.index)
                from aurum import data as _data

                rf = _data.cash_rate(idx, CFG)
                res = FT.run_fair_test(
                    spec_ok,
                    prices,
                    rf,
                    registry=reg,
                    library=lib,
                    data_label=D.data_label(prices),
                    progress=lambda m, f: bar.progress(min(1.0, f), text=m),
                )
                reg.set_status(h, res["status"], note=res["explanation"][:200])
                path = FT.save_report(res)
                st.session_state.last_ft = res
                st.success(f"Fair Test finished: {res['status'].upper()}. Report saved to {path.name}.")
                saved = FT.latest_results()
            except Exception as exc:
                st.error(f"Fair Test failed to run: {exc}")
        res = (
            st.session_state.get("last_ft")
            if st.session_state.get("last_ft", {}).get("spec_hash") == h
            else saved.get(h)
        )
        if res:
            colour = {"passed": "green", "failed": "red", "inconclusive": "orange"}[res["status"]]
            st.markdown(f"### Verdict: :{colour}[{res['status'].upper()}]")
            st.markdown(res["explanation"])
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "check": c["name"],
                            "result": "info" if c["passed"] is None else ("✅ pass" if c["passed"] else "❌ fail"),
                            "detail": c["detail"],
                        }
                        for c in res["checks"]
                    ]
                ),
                hide_index=True,
                width="stretch",
            )
            with st.expander("Full report"):
                st.markdown(FT.report_markdown(res))
            st.caption(f"Data: {res['data_label']} · run {res['run_at']} · code {res['code_fingerprint']}")
        else:
            st.info("No Fair Test saved for this exact version yet.")

        st.markdown("### Paper-trading eligibility")
        role = st.radio(
            "Role",
            gates.ROLES,
            horizontal=True,
            format_func=lambda r: {
                "main": "Main (the paper account is judged on it)",
                "shadow": "Shadow (tracked for evidence only)",
            }[r],
        )
        el = gates.eligibility(spec_ok, role, saved)
        st.dataframe(
            pd.DataFrame(
                [
                    {"gate": g["gate"], "result": "✅" if g["passed"] else "❌", "detail": g["detail"]}
                    for g in el["gates"]
                ]
            ),
            hide_index=True,
            width="stretch",
        )
        if el["eligible"]:
            st.success(
                f"Eligible for paper trading as {role}. The bot trades it only if it is listed under "
                "paper.strategies in config.yaml."
            )
        others = [g for g in el["gates"] if g["gate"] != "Owner approval"]
        if all(g["passed"] for g in others) and not el["eligible"]:
            with st.form("approve"):
                st.markdown("**Owner approval** (paper trading only; simulated money)")
                ev = st.text_area(
                    "Why you approve it (evidence)",
                    value=f"Fair Test {saved.get(h, {}).get('status', 'n/a')}; reviewed charts and report.",
                )
                ok = st.checkbox(
                    "I am the owner and I approve this exact version for PAPER trading. I understand no real "
                    "money is involved and that changing the strategy will need a new approval."
                )
                if st.form_submit_button("Approve") and ok:
                    gates.add_approval(spec_ok, role, approved_by="owner (dashboard)", evidence=ev)
                    try:
                        reg.set_status(h, "approved_paper" if role == "main" else "shadow", by="owner", note=ev[:200])
                    except R.StatusError as exc:
                        st.warning(f"Registry status not changed: {exc}")
                    st.success("Approved. Restart the bot to pick it up.")

        with st.expander("Status history"):
            st.dataframe(pd.DataFrame(reg.history(h)), hide_index=True, width="stretch")

# ---------------------------------------------------------------------------------------------------------------
# 5 research lab
# ---------------------------------------------------------------------------------------------------------------
with tabs[4]:
    if spec_err:
        st.error(spec_err)
    else:
        st.markdown(
            "Vary one number and see how the strategy changes. Scored on the **development period "
            "only** (2013-10-18 to 2023-12-31), so the holdout stays "
            "unseen. Every value you try is recorded as a separate attempt and counted in the luck check."
        )
        sw = D.sweepable(spec_ok)
        name = st.selectbox("Number to vary", list(sw))
        path, cur, lo_, hi_, integer = sw[name]
        c1, c2, c3 = st.columns(3)
        a = c1.number_input("From", value=float(max(lo_, cur * 0.5 if cur else lo_)))
        b = c2.number_input("To", value=float(min(hi_, cur * 1.5 if cur else hi_)))
        n = int(c3.number_input("Steps", 2, 15, 7))
        vals = list(np.linspace(a, b, n))
        vals = sorted({int(round(v)) for v in vals}) if integer else [round(v, 4) for v in vals]
        if st.button(f"Run {len(vals)} versions"):
            tickers = tuple(sorted(set(SP.assets_needed(spec_ok)) | {"SPY", "GLD"}))
            prices, _ = prices_for(tickers, start)
            idx = None
            for p in prices.values():
                idx = p.index if idx is None else idx.union(p.index)
            from aurum import data as _data

            rf = _data.cash_rate(idx, CFG)
            bar = st.progress(0.0)
            out, rets = D.sweep(
                spec_ok, path, vals, prices, rf, registry=registry(), progress=lambda k, nn: bar.progress(k / nn)
            )
            st.session_state.sweep = (name, cur, out, rets)
        if st.session_state.get("sweep") and st.session_state.sweep[0] == name:
            _, cur0, out, rets = st.session_state.sweep
            ok_rows = out.dropna(subset=["sharpe"]) if "sharpe" in out else out
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=ok_rows["value"],
                    y=ok_rows["sharpe"],
                    mode="lines+markers",
                    name="Sharpe (development)",
                    line={"color": DC.STRATEGY, "width": 2},
                    marker={"size": 8},
                )
            )
            fig.add_vline(x=cur0, line_dash="dash", line_color=DC.MUTED, annotation_text="current")
            fig.update_layout(
                height=320,
                template="plotly_white",
                xaxis_title=name,
                yaxis_title="Sharpe ratio, development period",
                hovermode="x unified",
                margin={"t": 30},
            )
            st.plotly_chart(fig, width="stretch", theme="streamlit")
            st.dataframe(
                out.drop(columns=[c for c in out.columns if c == "error" and out[c].isna().all()]),
                hide_index=True,
                width="stretch",
                column_config={
                    "cagr": st.column_config.NumberColumn(format="percent"),
                    "max_drawdown": st.column_config.NumberColumn(format="percent"),
                    "costs_per_year": st.column_config.NumberColumn(format="percent"),
                },
            )
            if rets.shape[1] >= 4:
                from aurum import stats

                pbo = stats.probability_of_backtest_overfitting(rets)
                st.markdown(
                    f"**Probability of backtest overfitting** across these versions: {pbo['pbo']:.0%} (above "
                    "50% means the best-looking value usually does worse out of sample)."
                )
            spread = ok_rows["sharpe"].max() - ok_rows["sharpe"].min() if len(ok_rows) else 0
            st.info(
                f"Picking the best of these {len(ok_rows)} values is itself a choice made on the data. The "
                f"spread here is {spread:.2f} Sharpe; "
                f"{R.overfitting_warnings(registry(), SP.spec_hash(spec_ok))[0]}"
            )

# ---------------------------------------------------------------------------------------------------------------
# 6 scanner
# ---------------------------------------------------------------------------------------------------------------
with tabs[5]:
    st.markdown(
        "Latest readings for the research universe on completed daily bars, and whether each of "
        "this strategy's rules would be met for each asset today."
    )
    if st.button("Scan now"):
        prices, errors = prices_for(tuple(D.UNIVERSE), start)
        st.session_state.scan = (
            D.scanner(spec_ok or {"signals": [], "universe": ["SPY"], "base_weights": {"SPY": 1.0}}, prices),
            D.freshness(prices),
            errors,
        )
    if st.session_state.get("scan"):
        tab, fr, errors = st.session_state.scan
        st.dataframe(
            tab,
            hide_index=True,
            width="stretch",
            column_config={
                k: st.column_config.NumberColumn(format="percent")
                for k in ("1-month return", "6-month return", "21-day volatility", "fall from 1-year high")
            },
        )
        with st.expander("Data freshness"):
            st.dataframe(fr, hide_index=True, width="stretch")
        if errors:
            st.warning("Unavailable: " + "; ".join(f"{t}: {e}" for t, e in errors.items()))
        st.caption(
            "A scan is a description of today, not a forecast: none of these readings has shown "
            "reliable predictive power in Aurum's experiments (EXP-038 to EXP-043)."
        )
