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
    stop    entry - stop_atr_mult * ATR, fixed at entry (never loosened); after a stop, wait for the
            score to leave BUY territory before re-entering
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
) -> SimResult:
    """Simulate one sleeve. Decisions at close t are filled at the open of t+1.

    fixed_exposure: invest this fraction instead of volatility targeting (buy & hold).
    stop_atr_mult=None disables stops.
    """
    idx = prices.index
    opens, closes = prices["Open"].to_numpy(float), prices["Close"].to_numpy(float)
    dec = decision.reindex(idx).fillna(HOLD).to_numpy(object)
    vol = ann_vol.reindex(idx).to_numpy(float)
    atr_ = atr.reindex(idx).to_numpy(float)
    rate = (
        cash_rate.reindex(idx).ffill().fillna(0.0).to_numpy(float)
        if isinstance(cash_rate, pd.Series)
        else np.full(len(idx), float(cash_rate))
    )
    c = cost_bps / 1e4

    cash, shares, stop, stopped_out, pending = float(initial), 0.0, np.nan, False, None
    entry = None
    rows, trades = [], []
    for i in range(len(idx)):
        cost_today, traded_today = 0.0, 0.0
        if i > 0:
            cash *= 1 + rate[i - 1] / 252  # overnight interest on uninvested cash
        # --- fill orders decided at the previous close, at today's open
        if pending == "BUY" and shares == 0 and np.isfinite(opens[i]):
            e = fixed_exposure if fixed_exposure is not None else target_exposure(vol[i - 1], target_vol)
            if e > 0:
                notional = e * cash / (1 + c)
                shares = notional / opens[i]
                cost_today, traded_today = notional * c, notional
                cash -= notional + cost_today
                stop = initial_stop(opens[i], atr_[i - 1], stop_atr_mult) if stop_atr_mult else np.nan
                entry = {
                    "entry_date": idx[i],
                    "entry_price": opens[i],
                    "shares": shares,
                    "cost": cost_today,
                    "entry_value": notional + cost_today,
                }
            pending = None
        elif pending and pending.startswith("EXIT") and shares > 0 and np.isfinite(opens[i]):
            proceeds = shares * opens[i]
            cost_today, traded_today = proceeds * c, proceeds
            cash += proceeds - cost_today
            pnl = proceeds - cost_today - entry["entry_value"]
            trades.append(
                {
                    **entry,
                    "exit_date": idx[i],
                    "exit_price": opens[i],
                    "cost": entry["cost"] + cost_today,
                    "pnl": pnl,
                    "ret": pnl / entry["entry_value"],
                    "exit_reason": pending[5:],
                    "days": int((idx[i] - entry["entry_date"]).days),
                }
            )
            shares, stop, entry, pending = 0.0, np.nan, None, None
        # --- mark to market at the close
        value = cash + shares * closes[i]
        exposure = shares * closes[i] / value if value > 0 else 0.0
        # --- decide at the close, for tomorrow's open
        if shares > 0:
            if np.isfinite(stop) and closes[i] <= stop:
                pending, stopped_out = "EXIT:stop", True
            elif dec[i] == SELL:
                pending = "EXIT:signal"
        else:
            if dec[i] != BUY:
                stopped_out = False  # signal reset: a fresh BUY may enter again
            if dec[i] == BUY and not stopped_out:
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
