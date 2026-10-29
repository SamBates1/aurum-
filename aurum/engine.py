"""Strategy engine: turns a strategy definition (aurum/spec.py) into daily target weights, runs them through the
one-account simulator (portfolio.simulate_portfolio, the same engine as EXP-032 onwards) and keeps every
intermediate step so each decision can be drawn and explained.

Timing (identical to every Aurum backtest):
  * every indicator, condition and target for day t uses data up to the close of t;
  * orders decided at the close of t fill at the next open (or next close if execution.fill = close);
  * costs are charged per asset in basis points on traded value; cash earns the 3-month T-bill rate;
  * no borrowing: if targets add up to more than 100% they are scaled down.

The same `compile_targets` is used by the designer, the Fair Test, run_designer.py and the paper trader
(aurum/spec_paper.py), so the strategy that is charted is the strategy that is tested and paper-traded.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import spec as SP
from . import strategy as S
from .backtest import performance, risk_free_daily
from .indicators import INDICATORS, compute
from .portfolio import PortfolioResult, drawdown_breaker, simulate_portfolio
from .volatility import realised_21d

TRADING_DAYS = 252


@dataclass
class Compiled:
    index: pd.DatetimeIndex
    raw_target: pd.DataFrame  # every day: the target the rules imply (share of account per asset)
    target: pd.DataFrame  # decision rows only (NaN = no order that day), what the simulator receives
    rebalance: pd.Series  # bool: an order may be decided at this close
    base: pd.Series  # base weight per asset
    sizing: pd.DataFrame  # sizing multiplier per asset per day
    signal_mult: dict[str, pd.DataFrame]  # signal id -> multiplier per asset per day
    signal_state: pd.DataFrame  # signal id -> True / False / NaN (unknown)
    conditions: pd.DataFrame  # "signal id:condition number" -> True / False / NaN
    operands: dict[str, pd.Series]  # operand label -> values used by the conditions
    exit_mult: pd.DataFrame  # trailing-stop multiplier per asset
    vol: pd.DataFrame  # volatility used by sizing (NaN for fixed sizing)


@dataclass
class StrategyRun:
    spec: dict
    compiled: Compiled
    result: PortfolioResult
    trades: pd.DataFrame
    capital: float
    rf: pd.Series | float
    meta: dict = field(default_factory=dict)

    @property
    def daily(self) -> pd.DataFrame:
        return self.result.daily

    @property
    def equity(self) -> pd.Series:
        return self.result.daily["value"]


# ---------------------------------------------------------------------------------------------------------------
# rules
# ---------------------------------------------------------------------------------------------------------------
def schedule_days(index: pd.DatetimeIndex, rule: str) -> pd.Series:
    s = pd.Series(False, index=index)
    if not len(index):
        return s
    if rule == "daily":
        return pd.Series(True, index=index)
    if rule == "weekly":
        return S.rebalance_days(index, "weekly")
    if rule == "once":
        s.iloc[0] = True
        return s
    ser = index.to_series()
    first = ser.groupby([index.year, index.month]).transform("min") == ser
    months = {"monthly": 1, "quarterly": 3, "yearly": 12}[rule]
    return pd.Series(first.to_numpy() & ((index.month - 1) % months == 0), index=index)


def operand_series(o, prices: dict[str, pd.DataFrame], index) -> pd.Series:
    if isinstance(o, float):
        return pd.Series(o, index=index)
    params = {k: v for k, v in o.items() if k not in ("ind", "asset")}
    return compute(o["ind"], prices[o["asset"]], params).reindex(index)


def evaluate_condition(left: pd.Series, op: str, right: pd.Series) -> pd.Series:
    """True / False, or NaN where either side is not yet known."""
    known = left.notna() & right.notna()
    if op == ">":
        v = left > right
    elif op == "<":
        v = left < right
    elif op == ">=":
        v = left >= right
    elif op == "<=":
        v = left <= right
    elif op in ("crosses_above", "crosses_below"):
        above = left > right
        prev = above.shift(1)
        known &= left.shift(1).notna() & right.shift(1).notna()
        v = (above & (prev == False)) if op == "crosses_above" else (~above & (prev == True))  # noqa: E712
    else:
        raise SP.SpecError(f"unknown comparison {op!r}")
    return v.astype(float).where(known)


def combine_states(states: list[pd.Series], how: str, k: int) -> pd.Series:
    df = pd.concat(states, axis=1)
    known = df.notna().all(axis=1)
    t = (df == 1).sum(axis=1)
    if how == "all":
        v = t == df.shape[1]
    elif how == "any":
        v = t >= 1
        known = known | (df == 1).any(axis=1)  # one true condition is enough even if another is unknown
    else:
        v = t >= k
        known = known | (t >= k)
    return v.astype(float).where(known)


def trailing_stop_mult(close: pd.Series, pct: float, cooldown: int) -> pd.Series:
    """1 while held; 0 for `cooldown` days after the close falls more than `pct` below its highest close since the
    position was (re)entered; then re-enters and the peak restarts. Uses closes up to each day only."""
    c = close.to_numpy(float)
    out = np.ones(len(c))
    peak, wait = np.nan, 0
    for i, x in enumerate(c):
        if not np.isfinite(x):
            out[i] = 0.0 if wait else 1.0
            continue
        if wait:
            wait -= 1
            out[i] = 0.0
            if wait == 0:
                peak = x
            continue
        peak = x if not np.isfinite(peak) else max(peak, x)
        if x < peak * (1 - pct):
            wait = int(cooldown)
            out[i] = 0.0
            if wait == 0:
                peak = x
    return pd.Series(out, index=close.index)


def compile_targets(spec: dict, prices: dict[str, pd.DataFrame], index: pd.DatetimeIndex | None = None) -> Compiled:
    s = SP.validate(spec)
    uni = s["universe"]
    need = SP.assets_needed(s)
    missing = [t for t in need if t not in prices]
    if missing:
        raise SP.SpecError(f"no price data for {', '.join(missing)}")
    if index is None:
        index = None
        for t in need:
            index = prices[t].index if index is None else index.intersection(prices[t].index)
        index = index.sort_values()
    close = pd.DataFrame({t: prices[t]["Close"].reindex(index) for t in need})
    base = pd.Series({t: s["base_weights"].get(t, 0.0) for t in uni})

    sz = s["sizing"]
    vol = pd.DataFrame(np.nan, index=index, columns=uni)
    if sz["method"] == "fixed":
        sizing = pd.DataFrame(1.0, index=index, columns=uni)
    else:
        for t in uni:
            c = close[t]
            vol[t] = (
                realised_21d(c)
                if sz["vol_window"] == 21
                else compute("volatility", prices[t], {"n": sz["vol_window"]}).reindex(index)
            )
        if sz["method"] == "vol_cap":
            sizing = pd.DataFrame({t: S.vol_target_weight(vol[t], sz["target_vol"], 1.0) for t in uni}, index=index)
        else:  # inverse_vol: same total as the base weights, split in proportion to 1 / volatility
            inv = 1.0 / vol.where(vol > 0)
            share = inv.div(inv.sum(axis=1), axis=0)
            total = float(base.sum())
            sizing = (share * total).div(base.where(base > 0), axis=1).fillna(0.0)

    conds, sig_state, sig_mult, operands = {}, {}, {}, {}
    for g in s["signals"]:
        states = []
        for j, c in enumerate(g["conditions"]):
            left = operand_series(c["left"], prices, index)
            right = operand_series(c["right"], prices, index)
            for o, ser in ((c["left"], left), (c["right"], right)):
                if isinstance(o, dict):
                    operands[SP.operand_label(o)] = ser
            st = evaluate_condition(left, c["op"], right)
            conds[f"{g['id']}:{j + 1}"] = st
            states.append(st)
        state = combine_states(states, g["combine"], g["k"])
        sig_state[g["id"]] = state
        eff = state.fillna(1.0 if g["assume_when_unknown"] else 0.0)
        m = pd.DataFrame(1.0, index=index, columns=uni)
        for t in g["apply_to"]:
            m[t] = np.where(eff == 1.0, g["when_true"], g["when_false"])
        sig_mult[g["id"]] = m

    exit_mult = pd.DataFrame(1.0, index=index, columns=uni)
    ts = s["exits"].get("trailing_stop")
    if ts:
        for t in uni:
            exit_mult[t] = trailing_stop_mult(close[t], float(ts["pct"]), int(ts.get("cooldown_days", 21)))

    raw = sizing.mul(base, axis=1)
    for m in sig_mult.values():
        raw = raw * m
    raw = (raw * exit_mult).clip(lower=0.0, upper=sz["max_weight"])
    gross = raw.sum(axis=1)
    raw = raw.div(gross.where(gross > 1.0, 1.0), axis=0)  # never borrow

    reb = schedule_days(index, s["schedule"]["rebalance"])
    if s["schedule"]["act_on_signal_change"] and sig_state:
        flips = pd.concat([v.fillna(-1) for v in sig_state.values()], axis=1).diff().abs().sum(axis=1) > 0
        reb = reb | flips
    target = raw.where(reb, np.nan)
    return Compiled(
        index=index,
        raw_target=raw,
        target=target,
        rebalance=reb,
        base=base,
        sizing=sizing,
        signal_mult=sig_mult,
        signal_state=pd.DataFrame(sig_state, index=index),
        conditions=pd.DataFrame(conds, index=index),
        operands=operands,
        exit_mult=exit_mult,
        vol=vol,
    )


# ---------------------------------------------------------------------------------------------------------------
# running
# ---------------------------------------------------------------------------------------------------------------
def run_spec(
    spec: dict,
    prices: dict[str, pd.DataFrame],
    rf: pd.Series | float = 0.0,
    *,
    capital: float = 10_000.0,
    index: pd.DatetimeIndex | None = None,
    cost_mult: float | None = None,
    fill: str | None = None,
    delay_days: int = 0,
) -> StrategyRun:
    """Backtest a strategy definition. `delay_days` postpones every decision (execution-delay stress test)."""
    s = SP.validate(spec)
    comp = compile_targets(s, prices, index)
    exe = s["execution"]
    mult = exe["cost_mult"] if cost_mult is None else cost_mult
    costs = {t: exe["costs_bps"][t] * mult for t in s["universe"]}
    tgt = comp.target.shift(delay_days) if delay_days else comp.target
    overlay = None
    ad = s["exits"].get("account_drawdown")
    if ad:
        overlay = drawdown_breaker(float(ad["trigger"]), float(ad["release"]), float(ad["scale"]))
    res = simulate_portfolio(
        {t: prices[t] for t in s["universe"]},
        tgt,
        cost_bps=costs,
        cash_rate=rf,
        band=s["schedule"]["band"],
        fill=fill or exe["fill"],
        initial=capital,
        overlay=overlay,
    )
    trades = res.trades.copy()
    if len(trades):
        pos = comp.index.get_indexer(pd.DatetimeIndex(trades["date"]))
        trades["decided"] = comp.index[np.maximum(pos - 1 - delay_days, 0)]
        eq_before = res.daily["value"].shift(1).reindex(trades["date"]).to_numpy()
        trades["pct_of_account"] = trades["notional"].to_numpy() / eq_before
        trades["reason"] = [
            explain_trade(s, comp, d, t, side)
            for d, t, side in zip(trades["decided"], trades["ticker"], trades["side"])
        ]
    else:
        trades = trades.assign(decided=pd.Series(dtype="datetime64[ns]"), pct_of_account=[], reason=[])
    return StrategyRun(
        s,
        comp,
        res,
        trades,
        capital,
        rf,
        {"spec_hash": SP.spec_hash(s), "cost_mult": mult, "delay_days": delay_days, "prices": prices},
    )


def explain_trade(s: dict, comp: Compiled, d, ticker: str, side: str) -> str:
    parts = [f"{'Raise' if side == 'BUY' else 'Cut'} {ticker} to {comp.raw_target.at[d, ticker]:.0%} of the account"]
    reasons = []
    sch = s["schedule"]["rebalance"]
    if sch != "daily":
        reasons.append(f"{sch} rebalance day")
    if s["sizing"]["method"] == "vol_cap":
        v = comp.vol.at[d, ticker]
        reasons.append(
            f"{ticker} volatility {v:.0%} -> size x{comp.sizing.at[d, ticker]:.2f}"
            if np.isfinite(v)
            else "volatility not yet known"
        )
    for g in s["signals"]:
        if ticker in g["apply_to"]:
            st = comp.signal_state.at[d, g["id"]]
            word = "unknown" if not np.isfinite(st) else ("met" if st == 1 else "not met")
            reasons.append(f"{g['label']}: {word}")
    if comp.exit_mult.at[d, ticker] == 0:
        reasons.append("trailing stop: out")
    if s["schedule"]["band"] > 0:
        reasons.append(f"more than {s['schedule']['band']:.0%} away from target")
    return parts[0] + (" (" + "; ".join(reasons) + ")" if reasons else "")


def explain_day(run: StrategyRun, d) -> dict:
    """Everything the strategy knew and decided at the close of day d (shown on hover and in the decision panel)."""
    s, comp = run.spec, run.compiled
    d = pd.Timestamp(d)
    if d not in comp.index:
        d = comp.index[comp.index.get_indexer([d], method="pad")[0]]
    out = {
        "date": d.date(),
        "data_used": f"completed daily bars up to the close of {d.date()}",
        "rebalance_day": bool(comp.rebalance.at[d]),
        "assets": {},
        "signals": [],
        "orders_next_session": [],
    }
    for g in s["signals"]:
        st = comp.signal_state.at[d, g["id"]]
        conds = []
        for j, c in enumerate(g["conditions"]):
            cs = comp.conditions.at[d, f"{g['id']}:{j + 1}"]
            vals = []
            for o in (c["left"], c["right"]):
                vals.append(o if isinstance(o, float) else float(comp.operands[SP.operand_label(o)].at[d]))
            conds.append(
                {
                    "rule": SP.condition_label(c),
                    "values": vals,
                    "met": None if not np.isfinite(cs) else bool(cs),
                }
            )
        out["signals"].append(
            {"id": g["id"], "label": g["label"], "met": None if not np.isfinite(st) else bool(st), "conditions": conds}
        )
    actual = run.result.weights.reindex(comp.index).ffill()
    for t in s["universe"]:
        out["assets"][t] = {
            "base_weight": float(comp.base[t]),
            "sizing_multiplier": float(comp.sizing.at[d, t]),
            "volatility": None if not np.isfinite(comp.vol.at[d, t]) else float(comp.vol.at[d, t]),
            "signal_multipliers": {k: float(v.at[d, t]) for k, v in comp.signal_mult.items()},
            "exit_multiplier": float(comp.exit_mult.at[d, t]),
            "target_weight": float(comp.raw_target.at[d, t]),
            "actual_weight_at_close": float(actual.at[d, t]) if d in actual.index else None,
        }
    tr = run.trades[run.trades["decided"] == d] if len(run.trades) else run.trades
    for _, r in tr.iterrows():
        out["orders_next_session"].append(
            {
                "ticker": r["ticker"],
                "side": r["side"],
                "amount": float(r["notional"]),
                "pct_of_account": float(r["pct_of_account"]),
                "fill_date": pd.Timestamp(r["date"]).date(),
                "fee": float(r["cost"]),
            }
        )
    return out


# ---------------------------------------------------------------------------------------------------------------
# results
# ---------------------------------------------------------------------------------------------------------------
def as_sim(daily: pd.DataFrame) -> S.SimResult:
    d = daily.copy()
    d["invested"] = (d["exposure"] > 1e-9).astype(float)
    return S.SimResult(d, pd.DataFrame(columns=["entry_date", "exit_reason", "pnl", "ret", "days", "entry_value"]))


def slice_daily(daily: pd.DataFrame, lo=None, hi=None) -> pd.DataFrame:
    d = daily.loc[lo:hi].copy()
    if len(d) and lo is not None:
        d.iloc[0, d.columns.get_loc("ret")] = 0.0
    return d


def summary(run: StrategyRun, lo=None, hi=None) -> dict:
    """The results box: return, risk, costs and activity over [lo, hi]."""
    d = slice_daily(run.daily, lo, hi)
    if len(d) < 2:
        return {"days": len(d)}
    p = performance(as_sim(d), run.rf)
    eq = (1 + d["ret"]).cumprod()
    dd = eq / eq.cummax() - 1
    trough = dd.idxmin()
    peak = eq.loc[:trough].idxmax()
    rec = eq.loc[trough:]
    back = rec[rec >= eq.loc[peak]]
    tr = run.trades
    if len(tr):
        tr = tr[(tr["date"] >= (pd.Timestamp(lo) if lo is not None else tr["date"].min()))]
        if hi is not None:
            tr = tr[tr["date"] <= pd.Timestamp(hi)]
    ex = d["ret"] - risk_free_daily(run.rf, d.index)
    yearly = (1 + d["ret"]).groupby(d.index.year).prod() - 1
    return {
        "start": d.index[0].date(),
        "end": d.index[-1].date(),
        "years": len(d) / TRADING_DAYS,
        "final_value": float(run.capital * eq.iloc[-1]),
        "total_return": p.get("total_return"),
        "cagr": p.get("cagr"),
        "volatility": p.get("volatility"),
        "sharpe": p.get("sharpe"),
        "sortino": p.get("sortino"),
        "max_drawdown": p.get("max_drawdown"),
        "max_drawdown_peak": peak.date(),
        "max_drawdown_trough": trough.date(),
        "recovered_on": back.index[0].date() if len(back) else None,
        "calmar": p.get("calmar"),
        "avg_exposure": p.get("avg_exposure"),
        "turnover_per_year": p.get("turnover_per_year"),
        "costs_per_year": p.get("costs_per_year"),
        "costs_paid": float(d["cost"].sum()),
        "orders": int(len(tr)),
        "orders_per_year": len(tr) / max(len(d) / TRADING_DAYS, 1e-9),
        "best_year": float(yearly.max()) if len(yearly) else None,
        "worst_year": float(yearly.min()) if len(yearly) else None,
        "worst_day": float(d["ret"].min()),
        "var_95_daily": float(np.nanpercentile(d["ret"], 5)),
        "excess_mean_ann": float(ex.mean() * TRADING_DAYS),
    }


def window_return(run: StrategyRun, lo, hi) -> tuple[float, float]:
    d = run.daily.loc[lo:hi]
    if len(d) < 5:
        return np.nan, np.nan
    eq = d["value"] / d["value"].iloc[0]
    return float(eq.iloc[-1] - 1), float((eq / eq.cummax() - 1).min())


def indicator_kind(o) -> str:
    return "number" if isinstance(o, float) else INDICATORS[o["ind"]].kind
