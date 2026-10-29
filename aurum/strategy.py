"""The trading strategy, defined once.

The backtest, the live dashboard, run_bot.py and the paper portfolio all call
these functions, so what is tested is exactly what is traded.

Timeline for one decision (daily bars):
    close of day t   features and score computed from data known at t's close
    open of day t+1  orders filled at the open (backtest) / first live price (paper)
    close of t+1..   position marked to market; stop checked on each close

Rules
    score   = weighted average of component scores in [-1, 1]:
                ml        (P(up) - 0.5) * 4, clipped; weight scaled by the model's
                          proven out-of-sample skill (point-in-time AUC)
                technical trend (50/200-day averages), MACD momentum, RSI extremes
    BUY     score >= buy_above, flat, and not stopped out on this same signal
    SELL    score <= sell_below while long -> exit
    HOLD    otherwise keep the current position
    size    sleeve * min(1, target_vol / volatility), fixed at entry (no averaging in)
    stop    entry - stop_atr_mult * ATR, fixed at entry (never loosened). Filled intrabar:
            at the stop price when the day's low touches it, or at the open after a gap.
            After a stop, wait for the score to leave BUY territory before re-entering.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

BUY, SELL, HOLD = "BUY", "SELL", "HOLD"


# ---------------------------------------------------------------------------
# component scores (vectorised: work on a whole history or a single row)
# ---------------------------------------------------------------------------
def ml_score(prob_up):
    """Map P(up) to [-1, 1]: 0.625 -> +0.5, 0.75 -> +1. Invalid probabilities -> NaN."""
    p = pd.Series(prob_up, dtype=float) if not np.isscalar(prob_up) else pd.Series([prob_up], dtype=float)
    p = p.where((p >= 0) & (p <= 1))
    out = ((p - 0.5) * 4).clip(-1, 1)
    return float(out.iloc[0]) if np.isscalar(prob_up) else out.set_axis(prob_up.index)


def technical_components(F: pd.DataFrame) -> pd.DataFrame:
    """Trend (+1/0/-1), momentum (+/-0.5), RSI extreme (+/-0.5 or NaN when not extreme)."""
    s50, s200, macd, rsi = F["sma50_gap"], F["sma200_gap"], F["macd_hist"], F["rsi_14"]
    trend = pd.Series(np.select([(s50 > 0) & (s200 > 0), (s50 < 0) & (s200 < 0)], [1.0, -1.0], 0.0), F.index)
    trend[s50.isna() | s200.isna()] = np.nan
    momentum = pd.Series(np.where(macd > 0, 0.5, -0.5), F.index).where(macd.notna())
    rsi_x = pd.Series(np.select([rsi > 70, rsi < 30], [-0.5, 0.5], np.nan), F.index)
    return pd.DataFrame({"trend": trend, "momentum": momentum, "rsi": rsi_x})


def technical_score(F: pd.DataFrame) -> pd.Series:
    c = technical_components(F)
    score = c.mean(axis=1, skipna=True).clip(-1, 1)
    return score.where(c["trend"].notna() & c["momentum"].notna())


# ---------------------------------------------------------------------------
# point-in-time model skill
# ---------------------------------------------------------------------------
def skill_from_auc(auc, floor: float, full: float):
    if full <= floor:
        return 1.0
    return np.clip((np.asarray(auc, dtype=float) - floor) / (full - floor), 0.0, 1.0)


def rolling_auc(probs: pd.Series, y: pd.Series, horizon: int, min_obs: int = 252, every: int = 21) -> pd.Series:
    """AUC of all out-of-sample predictions whose outcome was known by each date.

    A prediction made on day s has its label revealed on day s + horizon, so on
    day t only predictions with s <= t - horizon count. NaN until min_obs exist.
    """
    p = probs.to_numpy(dtype=float)
    lab = y.reindex(probs.index).to_numpy(dtype=float)
    ok = np.isfinite(p) & np.isfinite(lab)
    out = np.full(len(p), np.nan)
    last = np.nan
    for i in range(len(p)):
        if i % every == 0 or i == len(p) - 1:
            known = ok[: max(0, i - horizon + 1)]
            n = int(known.sum())
            if n >= min_obs:
                yy, pp = lab[: len(known)][known], p[: len(known)][known]
                last = roc_auc_score(yy, pp) if len(np.unique(yy)) == 2 else np.nan
            else:
                last = np.nan
        out[i] = last
    return pd.Series(out, index=probs.index, name="auc_pit")


# ---------------------------------------------------------------------------
# combining
# ---------------------------------------------------------------------------
def combine(scores: dict, weights: dict):
    """Weighted average of component scores, skipping missing components.

    scores/weights may be scalars or aligned Series. Returns NaN if no component
    with positive weight is available.
    """
    num, den = 0.0, 0.0
    for name, s in scores.items():
        w = weights.get(name, 0.0)
        if isinstance(s, pd.Series) or isinstance(w, pd.Series):
            s_ = s if isinstance(s, pd.Series) else pd.Series(s, index=w.index)
            avail = s_.notna()
            num = num + (w * s_.fillna(0.0))
            den = den + (w * avail.astype(float))
        elif s is not None and np.isfinite(s) and np.isfinite(w):
            num, den = num + w * s, den + w
    if isinstance(den, pd.Series):
        return (num / den.where(den > 0)).clip(-1, 1)
    return float(np.clip(num / den, -1, 1)) if den > 0 else float("nan")


def strategy_score(
    features: pd.DataFrame, prob_up: pd.Series | None, auc_pit: pd.Series | None, scfg: dict
) -> pd.Series:
    """The traded score for every date: ML (skill-weighted) + technical."""
    w = scfg["weights"]
    scores, weights = {"technical": technical_score(features)}, {"technical": float(w["technical"])}
    if prob_up is not None and w.get("ml", 0) > 0:
        skill = pd.Series(
            skill_from_auc(auc_pit.fillna(scfg["ml_auc_floor"]), scfg["ml_auc_floor"], scfg["ml_auc_full"]),
            index=auc_pit.index,
        )
        scores["ml"] = ml_score(prob_up.reindex(features.index))
        weights["ml"] = float(w["ml"]) * skill.reindex(features.index).fillna(0.0)
    return combine(scores, weights).rename("score")


def decisions(score: pd.Series, buy_above: float, sell_below: float) -> pd.Series:
    d = pd.Series(HOLD, index=score.index, dtype=object)
    d[score >= buy_above] = BUY
    d[score <= sell_below] = SELL
    return d  # NaN scores compare False -> HOLD (no new information, no action)


def decision_for(score: float, buy_above: float, sell_below: float) -> str:
    if score is None or not np.isfinite(score):
        return HOLD
    return BUY if score >= buy_above else SELL if score <= sell_below else HOLD


# ---------------------------------------------------------------------------
# sizing and stops (shared with paper trading)
# ---------------------------------------------------------------------------
def sleeve_weight(n_assets: int, max_position_pct: float) -> float:
    return min(max_position_pct, 1.0 / max(1, n_assets))


def target_exposure(ann_vol: float, target_vol: float) -> float:
    """Fraction of the sleeve to invest. 0 if volatility is unknown."""
    if ann_vol is None or not np.isfinite(ann_vol) or ann_vol <= 0:
        return 0.0
    return float(min(1.0, target_vol / ann_vol))


def initial_stop(entry_price: float, atr: float, mult: float) -> float:
    if not np.isfinite(atr) or atr <= 0:
        return 0.0  # no valid ATR -> no stop rather than a wrong one
    return entry_price - mult * atr


# ---------------------------------------------------------------------------
# simulation with explicit cash/share accounting
# ---------------------------------------------------------------------------
@dataclass
class SimResult:
    daily: pd.DataFrame  # value, cash, shares, invested (0/1), exposure, cost, traded (notional), ret
    trades: pd.DataFrame  # one row per round trip


@dataclass
class RiskRules:
    """Exit and entry-gating rules. Defaults reproduce the traded strategy; the
    optional ones exist for experiments (research/experiments) and are off
    unless an experiment, or a decision recorded in research/decisions.md, turns them on.

    stop_mode       "intrabar": stop fills when the day's low touches it, at the stop
                    price, or at the open if the price gapped through it (the convention
                    used by LEAN, Backtrader, VectorBT and Freqtrade, and how a live stop
                    order behaves). "close": stop checked on the close, exit next open.
    trail_atr_mult  chandelier trailing stop: highest close since entry - k*ATR (only tightens)
    take_profit_atr_mult  limit exit at entry + k*ATR, filled intrabar (gap -> open)
    max_hold_days   time exit after this many trading days (vertical barrier)
    dd_breaker      (max drawdown of the sleeve from its peak, cooldown days): exit and
                    block entries (Freqtrade MaxDrawdown / LEAN MaximumDrawdownPercent analogue)
    stop_guard      (stops, lookback days, cooldown days): after that many stop-outs within
                    the lookback, block entries (Freqtrade StoplossGuard analogue)
    reentry_cooldown_days  after a stop, allow re-entry on a still-active BUY once this many trading
                    days have passed (default None: wait for the signal to leave BUY first)
    fill            "open": orders decided at close t fill at the open of t+1 (default).
                    "close": they fill at the close of t+1 (market-on-close). Daily "open" prices are
                    the first print and may not be tradable in size, so "close" is the more
                    conservative check (EXP-010).
    """

    stop_atr_mult: float | None = 2.0
    stop_mode: str = "intrabar"
    trail_atr_mult: float | None = None
    take_profit_atr_mult: float | None = None
    max_hold_days: int | None = None
    dd_breaker: tuple[float, int] | None = None
    stop_guard: tuple[int, int, int] | None = None
    reentry_cooldown_days: int | None = None
    fill: str = "open"


def rules_from_config(scfg: dict) -> RiskRules:
    """The traded risk rules, as configured in config.yaml -> strategy."""
    return RiskRules(
        stop_atr_mult=scfg["stop_atr_mult"],
        stop_mode=scfg.get("stop_mode", "intrabar"),
        fill=scfg.get("fill", "open"),
    )


def simulate(
    prices: pd.DataFrame,
    decision: pd.Series,
    ann_vol: pd.Series,
    atr: pd.Series,
    *,
    cost_bps: float,
    cash_rate: pd.Series | float = 0.0,
    target_vol: float = 0.15,
    stop_atr_mult: float | None = 2.0,
    initial: float = 1.0,
    fixed_exposure: float | None = None,
    rules: RiskRules | None = None,
    block_entries: pd.Series | None = None,
) -> SimResult:
    """Simulate one sleeve. Decisions at close t are filled at the open of t+1;
    stops and take-profits fill intrabar (see RiskRules).

    fixed_exposure: invest this fraction instead of volatility targeting (buy & hold).
    stop_atr_mult=None disables the stop (ignored if `rules` is given).
    block_entries: boolean series; True at close t forbids a new entry decided at t.
    """
    rules = rules or RiskRules(stop_atr_mult=stop_atr_mult)
    idx = prices.index
    opens, closes = prices["Open"].to_numpy(float), prices["Close"].to_numpy(float)
    highs, lows = prices["High"].to_numpy(float), prices["Low"].to_numpy(float)
    dec = decision.reindex(idx).fillna(HOLD).to_numpy(object)
    blocked = (
        block_entries.reindex(idx).fillna(False).to_numpy(bool)
        if block_entries is not None
        else np.zeros(len(idx), bool)
    )
    vol = ann_vol.reindex(idx).to_numpy(float)
    atr_ = atr.reindex(idx).to_numpy(float)
    rate = (
        cash_rate.reindex(idx).ffill().fillna(0.0).to_numpy(float)
        if isinstance(cash_rate, pd.Series)
        else np.full(len(idx), float(cash_rate))
    )
    c = cost_bps / 1e4

    cash, shares, stop, take, stopped_out, pending = float(initial), 0.0, np.nan, np.nan, False, None
    entry, entry_i, high_close, peak_value, cooldown_until = None, -1, np.nan, float(initial), -1
    stop_days: list[int] = []
    last_stop_i = -(10**9)
    rows, trades = [], []

    def close_position(i, price, reason):
        nonlocal cash, shares, stop, take, entry, high_close
        proceeds = shares * price
        cost = proceeds * c
        cash += proceeds - cost
        pnl = proceeds - cost - entry["entry_value"]
        trades.append(
            {
                **entry,
                "exit_date": idx[i],
                "exit_price": price,
                "cost": entry["cost"] + cost,
                "pnl": pnl,
                "ret": pnl / entry["entry_value"],
                "exit_reason": reason,
                "days": int((idx[i] - entry["entry_date"]).days),
            }
        )
        shares, stop, take, entry, high_close = 0.0, np.nan, np.nan, None, np.nan
        return cost, proceeds

    def fill_pending(i, px):
        """Execute the order decided at the previous close at price px. Returns (cost, traded)."""
        nonlocal cash, shares, stop, take, entry, entry_i, high_close, pending
        if pending == "BUY" and shares == 0 and np.isfinite(px):
            pending = None
            e = fixed_exposure if fixed_exposure is not None else target_exposure(vol[i - 1], target_vol)
            if e <= 0:
                return 0.0, 0.0
            notional = e * cash / (1 + c)
            shares = notional / px
            cost = notional * c
            cash -= notional + cost
            a = atr_[i - 1]
            stop = initial_stop(px, a, rules.stop_atr_mult) if rules.stop_atr_mult else np.nan
            take = px + rules.take_profit_atr_mult * a if rules.take_profit_atr_mult and a > 0 else np.nan
            entry = {
                "entry_date": idx[i],
                "entry_price": px,
                "shares": shares,
                "cost": cost,
                "entry_value": notional + cost,
            }
            entry_i, high_close = i, px
            return cost, notional
        if pending and pending.startswith("EXIT") and shares > 0 and np.isfinite(px):
            reason, pending = pending[5:], None
            return close_position(i, px, reason)
        if pending == "BUY" and shares > 0:
            pending = None
        return 0.0, 0.0

    for i in range(len(idx)):
        cost_today, traded_today = 0.0, 0.0
        if i > 0:
            cash *= 1 + rate[i - 1] / 252  # overnight interest on uninvested cash
        # --- 1. fill orders decided at the previous close (at today's open, or after the intrabar
        #        checks at today's close when rules.fill == "close")
        if rules.fill == "open":
            c1, t1 = fill_pending(i, opens[i])
            cost_today, traded_today = cost_today + c1, traded_today + t1
        # --- 2. intrabar exits: stop first (pessimistic if both are touched), then take-profit
        if shares > 0 and rules.stop_mode == "intrabar" and np.isfinite(stop) and lows[i] <= stop:
            px = opens[i] if opens[i] <= stop else stop  # gap through the stop -> open
            c2, t2 = close_position(i, px, "stop")
            cost_today, traded_today = cost_today + c2, traded_today + t2
            stopped_out, last_stop_i = True, i
            stop_days.append(i)
        elif shares > 0 and np.isfinite(take) and highs[i] >= take:
            px = opens[i] if opens[i] >= take else take
            c2, t2 = close_position(i, px, "take_profit")
            cost_today, traded_today = cost_today + c2, traded_today + t2
        if rules.fill == "close":
            c1, t1 = fill_pending(i, closes[i])
            cost_today, traded_today = cost_today + c1, traded_today + t1
        # --- 3. mark to market at the close
        value = cash + shares * closes[i]
        exposure = shares * closes[i] / value if value > 0 else 0.0
        peak_value = max(peak_value, value)
        if shares > 0:
            high_close = max(high_close, closes[i])
            if rules.trail_atr_mult and np.isfinite(atr_[i]) and atr_[i] > 0:
                trail = high_close - rules.trail_atr_mult * atr_[i]
                stop = trail if not np.isfinite(stop) else max(stop, trail)  # only ever tightens
        # --- 4. decide at the close, for tomorrow's open
        if rules.stop_guard:
            k, look, cool = rules.stop_guard
            if sum(1 for d in stop_days if i - d < look) >= k:
                cooldown_until, stop_days = i + cool, []
        breaker_hit = rules.dd_breaker is not None and value / peak_value - 1 <= -rules.dd_breaker[0]
        if breaker_hit:
            cooldown_until, peak_value = i + rules.dd_breaker[1], value  # reset the peak after a breaker
        if shares > 0:
            if rules.stop_mode == "close" and np.isfinite(stop) and closes[i] <= stop:
                pending, stopped_out, last_stop_i = "EXIT:stop", True, i
                stop_days.append(i)
            elif breaker_hit:
                pending = "EXIT:breaker"
            elif dec[i] == SELL:
                pending = "EXIT:signal"
            elif rules.max_hold_days and i - entry_i >= rules.max_hold_days:
                pending = "EXIT:time"
        else:
            if dec[i] != BUY:
                stopped_out = False  # signal reset: a fresh BUY may enter again
            elif stopped_out and rules.reentry_cooldown_days and i - last_stop_i >= rules.reentry_cooldown_days:
                stopped_out = False  # cooldown elapsed: re-enter on the still-active BUY
            if dec[i] == BUY and not stopped_out and not blocked[i] and i >= cooldown_until:
                pending = "BUY"
        rows.append((value, cash, shares, float(shares > 0), exposure, cost_today, traded_today))

    daily = pd.DataFrame(rows, index=idx, columns=["value", "cash", "shares", "invested", "exposure", "cost", "traded"])
    daily["ret"] = daily["value"].pct_change().fillna(daily["value"].iloc[0] / initial - 1)
    if entry is not None:  # still open at the end: report it marked to market
        mtm = shares * closes[-1]
        pnl = mtm - entry["entry_value"]
        trades.append(
            {
                **entry,
                "exit_date": pd.NaT,
                "exit_price": closes[-1],
                "pnl": pnl,
                "ret": pnl / entry["entry_value"],
                "exit_reason": "open",
                "days": int((idx[-1] - entry["entry_date"]).days),
            }
        )
    cols = [
        "entry_date",
        "entry_price",
        "exit_date",
        "exit_price",
        "shares",
        "cost",
        "entry_value",
        "pnl",
        "ret",
        "exit_reason",
        "days",
    ]
    return SimResult(daily, pd.DataFrame(trades, columns=cols))


# ---------------------------------------------------------------------------
# target-weight simulation (always-invested strategies that resize positions)
# ---------------------------------------------------------------------------
def simulate_weights(
    prices: pd.DataFrame,
    target: pd.Series,
    *,
    cost_bps: float,
    cash_rate: pd.Series | float = 0.0,
    band: float = 0.05,
    fill: str = "open",
    initial: float = 1.0,
) -> SimResult:
    """Simulate one sleeve that holds a *fraction* of its value in the asset.

    target[t] is the desired weight in [0, 1], decided at the close of t using data up to t.
    The order fills at the next open (or next close if fill == "close"). A trade happens only
    if the current weight differs from the target by more than `band` (a no-trade band that
    limits turnover), or when moving between zero and non-zero exposure. Costs are charged on
    the traded notional. Each rebalance is recorded in `trades` (entry_value = traded notional).
    """
    idx = prices.index
    opens, closes = prices["Open"].to_numpy(float), prices["Close"].to_numpy(float)
    tgt = target.reindex(idx).to_numpy(float)
    rate = (
        cash_rate.reindex(idx).ffill().fillna(0.0).to_numpy(float)
        if isinstance(cash_rate, pd.Series)
        else np.full(len(idx), float(cash_rate))
    )
    c = cost_bps / 1e4
    cash, shares, pending = float(initial), 0.0, np.nan
    rows, trades = [], []
    for i in range(len(idx)):
        cost_today = traded_today = 0.0
        if i > 0:
            cash *= 1 + rate[i - 1] / 252
        px = opens[i] if fill == "open" else closes[i]
        if np.isfinite(pending) and np.isfinite(px) and px > 0:
            value = cash + shares * px
            cur = shares * px / value if value > 0 else 0.0
            w = float(np.clip(pending, 0.0, 1.0))
            if abs(w - cur) > band or (w == 0) != (cur == 0):
                delta_value = (w - cur) * value
                if delta_value > 0:  # buy: cost reduces what can be bought
                    delta_value = min(delta_value, cash) / (1 + c)
                cost_today = abs(delta_value) * c
                traded_today = abs(delta_value)
                shares += delta_value / px
                cash -= delta_value + cost_today
                trades.append(
                    {
                        "date": idx[i],
                        "price": px,
                        "from_weight": cur,
                        "to_weight": w,
                        "notional": traded_today,
                        "cost": cost_today,
                    }
                )
        pending = tgt[i] if np.isfinite(tgt[i]) else np.nan
        value = cash + shares * closes[i]
        exposure = shares * closes[i] / value if value > 0 else 0.0
        rows.append((value, cash, shares, float(shares > 1e-12), exposure, cost_today, traded_today))
    daily = pd.DataFrame(rows, index=idx, columns=["value", "cash", "shares", "invested", "exposure", "cost", "traded"])
    daily["ret"] = daily["value"].pct_change().fillna(daily["value"].iloc[0] / initial - 1)
    # performance() reads round-trip trade statistics; rebalances aren't round trips, so they're
    # reported separately and the trade table carries no closed trades
    reb = pd.DataFrame(trades)
    empty = pd.DataFrame(columns=["entry_date", "exit_reason", "pnl", "ret", "days", "entry_value"])
    res = SimResult(daily, empty)
    res.rebalances = reb  # type: ignore[attr-defined]
    return res


def vol_target_weight(ann_vol: pd.Series, target_vol: float, cap: float = 1.0) -> pd.Series:
    """min(cap, target_vol / forecast volatility); 0 where volatility is unknown."""
    w = (target_vol / ann_vol.where(ann_vol > 0)).clip(upper=cap)
    return w.fillna(0.0)
