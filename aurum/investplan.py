"""Complete investment and trade plans in dollars and pounds (platform phase 6).

Builds on the assessment (phase 4) and the portfolio check (phase 5). Every level has a stated reason, and sizing
comes from the pot's money, the instrument's volatility, the stop distance and the risk limits, never a round guess.

Long-term: an entry zone around fair support, up to three staged buys, an invalidation level based on the long-term
trend (wide), and a review schedule. Swing: an entry at the next open within a narrow zone, a volatility-based stop
under support, targets at 2R/3R or resistance, a time stop. Also supported: WAIT (no entry now), REDUCE, EXIT and
"no addition: concentration".

Costs are shown two ways: in the Alpaca paper account (US dollars, no commission) and for a UK investor buying the
same thing through a UK platform (currency conversion fee, spread, UK stamp duty where it applies). UK tax facts
(sourced, 2026/27): capital gains tax allowance £3,000 a year, rates 18% / 24% (gov.uk); stamp duty 0.5% on UK share
purchases, AIM shares and new listings exempt (London Stock Exchange). Gains inside an ISA are tax-free.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import CFG
from .indicators import compute, pivot_levels

COSTS_UK = {
    # assumptions until the owner names a platform; change in config.yaml under plan_costs
    "fx_fee": 0.0075,  # currency conversion each way on US shares (typical UK platform; varies 0.15%-1.5%)
    "spread_bps_large": 3.0,  # half-spread on liquid large companies and ETFs
    "spread_bps_small": 15.0,
    "uk_stamp_duty": 0.005,  # UK shares only (AIM and new listings exempt)
    "commission_gbp": 0.0,
}
RISK = {
    "long_term_risk_per_position": 0.015,  # of the pot, if the invalidation level is hit
    "swing_risk_per_trade": 0.0075,
    "max_stock": 0.10,
    "max_etf": 0.25,
}
CGT = {"allowance_gbp": 3000, "rates": (0.18, 0.24), "source": "gov.uk, 2026/27"}


def settings(cfg: dict = CFG) -> tuple[dict, dict]:
    c = dict(COSTS_UK)
    c.update(cfg.get("plan_costs") or {})
    r = dict(RISK)
    r.update(cfg.get("plan_risk") or {})
    return c, r


@dataclass
class Plan:
    symbol: str
    horizon: str
    action: str  # BUY, WAIT, NO ENTRY, REDUCE, EXIT, NO ADDITION, HOLD
    pot_usd: float
    price: float
    entry_zone: tuple[float, float] | None = None
    tranches: list[tuple[str, float, float]] = field(default_factory=list)  # (when, price, shares)
    stop: float | None = None
    targets: list[tuple[str, float, float]] = field(default_factory=list)  # (label, price, reward-to-risk)
    shares: float = 0.0
    allocation_usd: float = 0.0
    max_loss_usd: float = 0.0
    gross_profit_usd: list[float] = field(default_factory=list)
    holding_period: str = ""
    costs: dict = field(default_factory=dict)
    fx: str = ""
    reasons: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def gbp(self, usd: float, usd_per_gbp: float) -> float:
        return usd / usd_per_gbp


def _levels(daily: pd.DataFrame) -> dict:
    c = daily["Close"].dropna()
    lv = pivot_levels(daily.tail(260), 5)
    lows = [x for x in lv["support"].dropna().unique()[-40:] if x < c.iloc[-1]]
    highs = [x for x in lv["resistance"].dropna().unique()[-40:] if x > c.iloc[-1]]
    return {
        "close": float(c.iloc[-1]),
        "atr": float(compute("atr_pct", daily, {"n": 14}).iloc[-1] * c.iloc[-1]),
        "sma50": float(c.rolling(50).mean().iloc[-1]) if len(c) >= 50 else np.nan,
        "sma200": float(c.rolling(200).mean().iloc[-1]) if len(c) >= 200 else np.nan,
        "support": float(max(lows)) if lows else None,
        "resistance": float(min(highs)) if highs else None,
    }


def costs_for(alloc_usd: float, usd_per_gbp: float, uk_listed: bool, liquid: bool, cfg: dict = CFG) -> dict:
    c, _ = settings(cfg)
    spread = (c["spread_bps_large"] if liquid else c["spread_bps_small"]) / 1e4
    alpaca = alloc_usd * spread * 2  # in and out, no commission in the paper account
    gbp = alloc_usd / usd_per_gbp
    uk = gbp * spread * 2 + 2 * c["commission_gbp"]
    if uk_listed:
        uk += gbp * c["uk_stamp_duty"]
    else:
        uk += gbp * c["fx_fee"] * 2
    return {
        "paper_account_usd": round(alpaca, 2),
        "uk_platform_gbp": round(uk, 2),
        "uk_platform_pct": uk / gbp if gbp else 0.0,
        "assumptions": f"spread {spread * 1e4:.0f} bps each way; "
        + ("UK stamp duty 0.5% on purchase" if uk_listed else f"currency fee {c['fx_fee']:.2%} each way")
        + "; platform fees vary: set yours under plan_costs",
    }


def build(
    symbol: str,
    daily: pd.DataFrame,
    horizon: str,
    verdict: str,
    pot_usd: float,
    usd_per_gbp: float,
    held_shares: float = 0.0,
    position_cap: float | None = None,
    portfolio_check: dict | None = None,
    setup: str | None = None,
    is_stock: bool = True,
    uk_listed: bool = False,
    liquid: bool = True,
    fractionable: bool = True,
    cfg: dict = CFG,
) -> Plan:
    _, risk = settings(cfg)
    L = _levels(daily)
    px, atr = L["close"], L["atr"]
    plan = Plan(symbol, horizon, verdict, pot_usd, px, fx=f"£1 = ${usd_per_gbp:.4f}")
    cap = position_cap if position_cap is not None else (risk["max_stock"] if is_stock else risk["max_etf"])
    held_usd = held_shares * px

    # exits for held positions
    if held_shares > 0 and verdict in ("SELL", "REDUCE"):
        sell = held_shares if verdict == "SELL" else held_shares / 2
        plan.action = "EXIT" if verdict == "SELL" else "REDUCE"
        plan.shares = -round(sell, 4)
        plan.allocation_usd = -sell * px
        plan.reasons["action"] = "the assessment turned against the position" + (
            "; half is sold first to limit regret if it rebounds" if verdict == "REDUCE" else ""
        )
        plan.costs = costs_for(sell * px, usd_per_gbp, uk_listed, liquid, cfg)
        return plan
    if held_shares > 0 and verdict == "HOLD":
        plan.action = "HOLD"
        plan.reasons["action"] = "the assessment still supports the position"
    if portfolio_check and portfolio_check.get("verdict") in ("duplicate", "blocked"):
        plan.action = "NO ADDITION"
        plan.notes += portfolio_check.get("problems", [])
        plan.reasons["action"] = "portfolio rules: " + "; ".join(portfolio_check.get("problems", []))
        return plan
    if verdict not in ("BUY", "WAIT", "HOLD"):
        plan.action = "NO ENTRY"
        plan.reasons["action"] = f"assessment says {verdict}"
        return plan

    if horizon == "long-term":
        floor = L["sma200"] if np.isfinite(L["sma200"]) else px - 3 * atr
        stop = min(floor - atr, px - 2 * atr)
        plan.reasons["stop"] = (
            f"invalidation: below the 200-day average (${floor:,.2f}) by one daily range (${atr:,.2f}); "
            "the long-term case is broken there"
        )
        lo = max(L["support"] or px - atr, px - atr)
        plan.entry_zone = (round(lo, 2), round(px + 0.25 * atr, 2))
        plan.reasons["entry"] = "between the nearest support (or one daily range lower) and a quarter of a range above"
        plan.holding_period = "6 to 24 months; review after each quarterly report"
        risk_pct = risk["long_term_risk_per_position"]
    else:
        sup = L["support"]
        stop = max((sup - 0.25 * atr) if sup else px - 2 * atr, px - 2 * atr)
        plan.reasons["stop"] = (
            f"under support at ${sup:,.2f} by a quarter of a daily range"
            if sup and stop > px - 2 * atr
            else f"two daily ranges (${2 * atr:,.2f}) below the entry: the setup has failed there"
        )
        plan.entry_zone = (round(px - 0.25 * atr, 2), round(px + 0.25 * atr, 2))
        plan.reasons["entry"] = "the next open, if it is within a quarter of a daily range of the last close"
        plan.holding_period = "1 to 8 weeks; exit after 4 weeks if no progress"
        risk_pct = risk["swing_risk_per_trade"]
    stop = max(stop, 0.01)
    plan.stop = round(stop, 2)
    per_share = px - stop
    budget_risk = risk_pct * pot_usd
    by_risk = budget_risk / per_share if per_share > 0 else 0.0
    by_cap = max(cap * pot_usd - held_usd, 0) / px
    shares = min(by_risk, by_cap)
    plan.reasons["size"] = f"{'risk budget' if by_risk <= by_cap else 'position limit'}: " + (
        f"{risk_pct:.2%} of the pot (${budget_risk:,.0f}) lost if the stop is hit"
        if by_risk <= by_cap
        else f"at most {cap:.0%} of the pot in one position"
    )
    shares = shares if fractionable else float(np.floor(shares))
    plan.shares = round(shares, 4)
    plan.allocation_usd = round(shares * px, 2)
    plan.max_loss_usd = round(shares * per_share, 2)
    for r in (2.0, 3.0):
        plan.targets.append((f"{r:g}R", round(px + r * per_share, 2), r))
    if L["resistance"]:
        plan.targets.append(("resistance", round(L["resistance"], 2), (L["resistance"] - px) / per_share))
    plan.targets.sort(key=lambda t: t[1])
    plan.reasons["targets"] = (
        "2 and 3 times the risk per share, and the nearest resistance (where sellers appeared before)"
    )
    plan.gross_profit_usd = [round(shares * (t[1] - px), 2) for t in plan.targets]
    if horizon == "long-term" and shares > 0:
        third = shares / 3
        plan.tranches = [
            ("now (next open)", round(px, 2), round(third, 4)),
            ("on a pullback to the zone's low", plan.entry_zone[0], round(third, 4)),
            ("after the next quarterly report, if the case holds", round(px, 2), round(shares - 2 * third, 4)),
        ]
    plan.costs = costs_for(plan.allocation_usd, usd_per_gbp, uk_listed, liquid, cfg)
    if verdict == "WAIT":
        plan.action = "WAIT"
        plan.notes.append("Attractive, but no entry now: the plan applies only once the price is in the entry zone")
    elif plan.action != "HOLD":
        plan.action = "BUY" if shares > 0 else "NO ENTRY"
    if horizon == "swing":
        plan.notes.append(
            f"Outside an ISA, gains above £{CGT['allowance_gbp']:,} a year are taxed at "
            f"{CGT['rates'][0]:.0%} or {CGT['rates'][1]:.0%} ({CGT['source']}); frequent trading makes this likely"
        )
    if setup:
        plan.reasons["setup"] = setup
    return plan
