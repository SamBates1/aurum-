"""Portfolio-level simulator (brief 2026-10-29, EXP-032 onwards).

The sleeve simulator (strategy.simulate_weights + backtest.combine_sleeves) runs each asset in its own pot of
money that is never topped up or trimmed against the others. The paper trader, however, sizes each asset as a share
of *total* equity, so the two disagree once sleeves drift apart. This simulator holds all assets and cash in one
account, exactly like the paper trader and a broker account, and supports rules that need the whole portfolio:
cross-asset sizing (risk parity, group caps, cash reserve), circuit breakers on the account's own equity, and
contributions (dollar-cost averaging).

Conventions (same as the rest of Aurum):
  * target.loc[t] = desired share of total equity per asset, decided at the close of t from data up to t;
    NaN for an asset = no order for it that day; a row of all NaN = no decision that day.
  * orders fill at the next open (or next close); a trade happens only when an asset is more than `band` away
    from its target, or moves between zero and non-zero; sells execute before buys; buys never use more cash
    than is available (no borrowing); costs are per-ticker basis points on traded notional.
  * cash earns the T-bill rate. Returns are time-weighted: contributions are not counted as performance.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

TRADING_DAYS = 252


@dataclass
class PortfolioResult:
    daily: pd.DataFrame  # value, cash, exposure, cost, traded, flow, ret
    weights: pd.DataFrame  # end-of-day actual weight per asset
    trades: pd.DataFrame  # one row per order: date, ticker, side, notional, cost, from_w, to_w
    meta: dict = field(default_factory=dict)


def simulate_portfolio(
    prices: dict[str, pd.DataFrame],
    target: pd.DataFrame,
    *,
    cost_bps: dict[str, float],
    cash_rate: pd.Series | float = 0.0,
    band: float = 0.05,
    fill: str = "open",
    initial: float = 1.0,
    contributions: pd.Series | None = None,
    overlay: Callable[[int, np.ndarray, pd.DatetimeIndex], float] | None = None,
) -> PortfolioResult:
    """overlay(i, equity_so_far, index) -> multiplier applied to the decision made at the close of day i, using the
    account's own equity up to and including day i (circuit breakers, loss limits)."""
    tickers = list(target.columns)
    idx = None
    for t in tickers:
        idx = prices[t].index if idx is None else idx.intersection(prices[t].index)
    idx = idx.sort_values()
    n, k = len(idx), len(tickers)
    OP = np.column_stack([prices[t]["Open"].reindex(idx).to_numpy(float) for t in tickers])
    C = np.column_stack([prices[t]["Close"].reindex(idx).to_numpy(float) for t in tickers])
    F = OP if fill == "open" else C
    T = target.reindex(idx).to_numpy(float)
    cost = np.array([cost_bps[t] / 1e4 for t in tickers])
    rate = (
        cash_rate.reindex(idx).ffill().fillna(0.0).to_numpy(float)
        if isinstance(cash_rate, pd.Series)
        else np.full(n, float(cash_rate))
    )
    flows = contributions.reindex(idx).fillna(0.0).to_numpy(float) if contributions is not None else np.zeros(n)

    cash, sh = float(initial), np.zeros(k)
    last_c = np.where(np.isfinite(C[0]), C[0], np.nan)
    pending = None
    rows, wrows, trades = [], [], []
    equity = np.empty(n)
    for i in range(n):
        c_today = traded = 0.0
        if i > 0:
            cash *= 1 + rate[i - 1] / TRADING_DAYS
        cash += flows[i]
        px = np.where(np.isfinite(F[i]) & (F[i] > 0), F[i], last_c)
        if pending is not None:
            value = cash + float(np.nansum(sh * px))
            cur = np.where(value > 0, sh * px / value, 0.0)
            w = np.where(np.isfinite(pending), np.clip(pending, 0.0, 1.0), cur)
            gross = w.sum()
            if gross > 1.0:  # never borrow
                w = w / gross
            move = (np.abs(w - cur) > band) | ((w == 0) != (cur == 0))
            move &= np.isfinite(px)
            # sells first
            for j in np.where(move & (w < cur))[0]:
                notional = (cur[j] - w[j]) * value
                q = sh[j] if w[j] == 0 else min(sh[j], notional / px[j])
                notional = q * px[j]
                fee = notional * cost[j]
                sh[j] -= q
                cash += notional - fee
                c_today += fee
                traded += notional
                trades.append((idx[i], tickers[j], "SELL", notional, fee, cur[j], w[j]))
            buys = np.where(move & (w > cur))[0]
            # as in the sleeve engine and the paper trader, the fee comes out of the planned purchase
            want = np.array([(w[j] - cur[j]) * value / (1 + cost[j]) for j in buys])
            if len(buys) and want.sum() > 0:
                scale = min(1.0, cash / float(np.sum(want * (1 + cost[buys]))))
                for j, amt in zip(buys, want * scale):
                    if amt <= 0:
                        continue
                    fee = amt * cost[j]
                    sh[j] += amt / px[j]
                    cash -= amt + fee
                    c_today += fee
                    traded += amt
                    trades.append((idx[i], tickers[j], "BUY", amt, fee, cur[j], w[j]))
            pending = None
        last_c = np.where(np.isfinite(C[i]) & (C[i] > 0), C[i], last_c)
        hold = sh * last_c
        value = cash + float(np.nansum(hold))
        equity[i] = value
        rows.append((value, cash, float(np.nansum(hold)) / value if value > 0 else 0.0, c_today, traded, flows[i]))
        wrows.append(hold / value if value > 0 else np.zeros(k))
        row = T[i]
        if np.isfinite(row).any():
            pending = row.copy()
            if overlay is not None:
                pending = pending * overlay(i, equity[: i + 1], idx)
    daily = pd.DataFrame(rows, index=idx, columns=["value", "cash", "exposure", "cost", "traded", "flow"])
    prev = daily["value"].shift(1).fillna(initial)
    daily["ret"] = (daily["value"] - daily["flow"]) / prev - 1
    weights = pd.DataFrame(wrows, index=idx, columns=tickers)
    tr = pd.DataFrame(trades, columns=["date", "ticker", "side", "notional", "cost", "from_weight", "to_weight"])
    return PortfolioResult(daily, weights, tr)


def drawdown_breaker(trigger: float, release: float, scale: float, max_days: int | None = None):
    """Circuit breaker on the account's own equity: when it is more than `trigger` below its peak, multiply every
    target by `scale`; restore once the drawdown is back under `release` (or after `max_days`)."""
    state = {"on": False, "since": 0}

    def rule(i, eq, idx):
        dd = eq[-1] / np.max(eq) - 1
        if not state["on"] and dd < -trigger:
            state.update(on=True, since=i)
        elif state["on"] and (dd > -release or (max_days and i - state["since"] >= max_days)):
            state["on"] = False
        return scale if state["on"] else 1.0

    return rule


def loss_limit(window: int, limit: float, scale: float, pause: int):
    """If equity fell more than `limit` over the last `window` days, scale targets for the next `pause` days."""
    state = {"until": -1}

    def rule(i, eq, idx):
        if i >= window and eq[-1] / eq[-1 - window] - 1 < -limit:
            state["until"] = i + pause
        return scale if i <= state["until"] else 1.0

    return rule


def equity_curve_filter(n: int, scale: float):
    """Hold `scale` x targets while equity is below its own n-day average (trading the equity curve)."""

    def rule(i, eq, idx):
        if i < n:
            return 1.0
        return scale if eq[-1] < np.mean(eq[-n:]) else 1.0

    return rule
