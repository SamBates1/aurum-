"""Trade plan for one ticker (live-charts stage 3): entry, stop, targets, reward-to-risk, size in pounds, UK fund,
what would prove it wrong, and a rule-based confidence assessment.

Everything is computed from completed daily closes (the strategy's own clock); nothing here places an order. The plan
describes what the strategy says and how a position of that kind could be sized and protected. Sizing respects the
risk engine's limits (aurum/risk.py) and never exceeds the strategy's own target weight. The confidence label is an
assessment from simple checks, not a probability of profit.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import risk as R
from .config import CFG
from .decision_board import UK_FUNDS, uk_fund
from .indicators import compute, pivot_levels

DEFAULTS = {
    "account_gbp": 10_000.0,  # size of the account the plan is sized for (paper)
    "risk_per_trade": 0.01,  # share of the account lost if the stop is hit (before gaps and costs)
    "stop_atr": 2.0,  # default stop distance in multiples of the 14-day ATR (when the strategy has no stop)
    "targets_r": [2.0, 3.0],  # profit targets as multiples of the risk (R)
    "atr_window": 14,
    "pivot_k": 5,
}


def settings(cfg: dict = CFG) -> dict:
    d = dict(DEFAULTS)
    d.update(cfg.get("trade_plan", {}) or {})
    return d


@dataclass
class TradePlan:
    symbol: str
    as_of: pd.Timestamp
    action: str  # BUY / HOLD / SELL / STAY OUT
    action_text: str
    entry: float
    stop: float
    stop_source: str
    targets: list[tuple[str, float, float]]  # (label, price, reward-to-risk)
    support: float | None
    resistance: float | None
    atr: float
    target_weight: float
    size_gbp: float
    size_weight: float
    size_reason: str
    risk_gbp: float
    uk_fund: str
    allowed: bool
    invalidation: list[str]
    confidence: str
    confidence_points: list[tuple[bool, str]]
    correlation: float | None
    correlation_text: str
    notes: list[str] = field(default_factory=list)

    def summary_rows(self) -> list[tuple[str, str]]:
        rows = [
            ("What the strategy says", self.action_text),
            ("Reference entry", f"${self.entry:,.2f} (last close; an order would fill at the next open)"),
            ("Stop", f"${self.stop:,.2f} ({self.stop / self.entry - 1:+.1%}) · {self.stop_source}"),
        ]
        for lab, px, rr in self.targets:
            rows.append((lab, f"${px:,.2f} ({px / self.entry - 1:+.1%}) · reward-to-risk {rr:.1f} : 1"))
        rows += [
            (
                "Size",
                f"£{self.size_gbp:,.0f} ({self.size_weight:.0%} of £{settings()['account_gbp']:,.0f}) · "
                f"{self.size_reason}",
            ),
            ("Loss if the stop is hit", f"about £{self.risk_gbp:,.0f} before gaps and costs"),
            ("Buy it in the UK as", self.uk_fund),
            ("Confidence (assessment, not a probability)", self.confidence),
            ("Overlap with the main paper account", self.correlation_text),
        ]
        return rows


def _last(s: pd.Series):
    s = s.dropna()
    return float(s.iloc[-1]) if len(s) else None


def build(
    symbol: str,
    daily: pd.DataFrame,
    run,
    *,
    research_only: bool = False,
    holdings_returns: pd.Series | None = None,
    cfg: dict = CFG,
) -> TradePlan:
    """`daily`: the symbol's daily OHLCV (engine convention). `run`: the strategy's StrategyRun on it.
    `holdings_returns`: daily returns of what the owner (paper account) already holds, for the overlap check."""
    st = settings(cfg)
    lim = R.limits(cfg)
    d = daily.dropna(subset=["Close"])
    as_of = d.index[-1]
    entry = float(d["Close"].iloc[-1])
    atr_pct = _last(compute("atr_pct", d, {"n": st["atr_window"]})) or 0.02
    atr = atr_pct * entry
    lv = pivot_levels(d, st["pivot_k"])
    # nearest confirmed swing levels below / above today's close
    lows = lv["support"].dropna().unique()
    highs = lv["resistance"].dropna().unique()
    below = [x for x in lows[-60:] if x < entry]
    above = [x for x in highs[-60:] if x > entry]
    support = float(max(below)) if below else None
    resistance = float(min(above)) if above else None

    s = run.spec
    comp = run.compiled
    tw = float(comp.raw_target[symbol].iloc[-1]) if symbol in comp.raw_target else 0.0
    held_before = (
        float(comp.raw_target[symbol].iloc[-2]) if symbol in comp.raw_target and len(comp.raw_target) > 1 else 0.0
    )
    stg = s["exits"].get("stop_target")
    levels = comp.exit_levels.get(symbol) if comp.exit_levels else None

    # stop: the strategy's own stop if it has one, otherwise the default ATR stop
    if stg and stg.get("stop") is not None and levels is not None and np.isfinite(levels["stop"].iloc[-1]):
        stop, stop_src = float(levels["stop"].iloc[-1]), "the strategy's own stop (fixed when it bought)"
    elif stg and stg.get("stop") is not None:
        k = float(stg["stop"])
        stop = entry * (1 - k * atr_pct) if stg.get("unit", "atr") == "atr" else entry * (1 - k)
        stop_src = "the strategy's own stop rule, measured from today's close"
    else:
        stop = entry - st["stop_atr"] * atr
        stop_src = f"{st['stop_atr']:g} x the {st['atr_window']}-day ATR (${atr:,.2f}) below the close (plan default)"
    stop = max(stop, 0.01)
    risk_ps = entry - stop
    targets = []
    if stg and stg.get("target") is not None:
        if levels is not None and np.isfinite(levels["target"].iloc[-1]):
            t = float(levels["target"].iloc[-1])
        else:
            k = float(stg["target"])
            t = entry * (1 + k * atr_pct) if stg.get("unit", "atr") == "atr" else entry * (1 + k)
        targets.append(("Target (strategy's take-profit)", t, (t - entry) / risk_ps))
    for r in st["targets_r"]:
        targets.append((f"Target {r:g}R", entry + r * risk_ps, float(r)))
    if resistance:
        targets.append(("Nearest resistance", resistance, (resistance - entry) / risk_ps))
    targets.sort(key=lambda x: x[1])

    # what the strategy says
    if tw > 0 and held_before <= 0:
        action, text = "BUY", f"buy: the rules now want {tw:.0%} of the account in {symbol}"
    elif tw > 0:
        action, text = "HOLD", f"hold: the rules want {tw:.0%} of the account in {symbol}"
    elif held_before > 0:
        action, text = "SELL", f"sell: the rules no longer want {symbol}"
    else:
        action, text = "STAY OUT", f"stay out: the rules do not want {symbol} now"
    if research_only:
        text += " (research only: these rules were not Fair-Tested on this ticker)"

    # size: risk budget / stop distance, capped by the strategy's weight and the risk engine's per-asset limit
    acct = float(st["account_gbp"])
    stop_frac = risk_ps / entry
    by_risk = st["risk_per_trade"] / stop_frac if stop_frac > 0 else 0.0
    caps = [(by_risk, f"{st['risk_per_trade']:.1%} of the account at risk to the stop")]
    caps.append((tw, "the strategy's own target weight"))
    caps.append((float(lim["max_weight_per_asset"]), "the risk engine's limit per asset"))
    w, why = min(caps, key=lambda x: x[0])
    allowed = symbol in lim["allowed_assets"]
    notes = []
    if not allowed:
        notes.append(
            f"{symbol} is not on the risk engine's allowed list, so the paper accounts would not trade it. "
            "Shown for research only."
        )
        w, why = 0.0, "not on the risk engine's allowed list"
    size_gbp = w * acct
    risk_gbp = size_gbp * stop_frac

    invalid = [f"a daily close below ${stop:,.2f} (the stop)"]
    if support and stop < support < entry:
        invalid.append(f"a close below the nearest support at ${support:,.2f} would be an early warning")
    for g in s["signals"]:
        if symbol in g["apply_to"]:
            invalid.append(f"the rule '{g['label']}' stops being met")
    if s["sizing"]["method"] == "vol_cap":
        invalid.append(f"volatility above {s['sizing']['target_vol']:.0%} (the strategy would cut the position)")

    # confidence: simple, visible checks (not a probability)
    c = d["Close"]
    sma200 = _last(c.rolling(200).mean())
    adx = _last(compute("adx", d, {"n": 14}))
    stoch = _last(compute("stoch_k", d, {"n": 14, "smooth": 3}))
    wk = c.resample("W-FRI").last().dropna()
    wk_trend = len(wk) > 40 and wk.iloc[-1] > wk.rolling(40).mean().iloc[-1]
    pts = [
        (tw > 0, "the strategy wants to hold it" if tw > 0 else "the strategy does not want it"),
        (
            bool(sma200 and entry > sma200),
            "price above its 200-day average" if sma200 and entry > sma200 else "price below its 200-day average",
        ),
        (bool(wk_trend), "weekly trend up (above the 40-week average)" if wk_trend else "weekly trend not up"),
        (
            bool(adx and adx > 25),
            f"trend strength ADX {adx:.0f}" + (" (trending)" if adx and adx > 25 else " (weak trend)")
            if adx
            else "ADX not known",
        ),
        (
            bool(stoch is not None and stoch < 80),
            f"stochastic {stoch:.0f}"
            + (" (not stretched)" if stoch is not None and stoch < 80 else " (stretched: may pull back)")
            if stoch is not None
            else "stochastic not known",
        ),
        (
            not research_only,
            "ticker is part of this strategy (not a research-only variant)"
            if not research_only
            else "rules not tested on this ticker (research only)",
        ),
    ]
    score = sum(ok for ok, _ in pts)
    conf = "High" if score >= 5 else ("Medium" if score >= 3 else "Low")
    conf = f"{conf} ({score} of {len(pts)} checks agree)"

    corr, corr_text = None, "not available"
    if holdings_returns is not None:
        r = c.pct_change(fill_method=None).iloc[-252:]
        j = pd.concat([r, holdings_returns], axis=1, join="inner").dropna()
        if len(j) > 60:
            corr = float(j.iloc[:, 0].corr(j.iloc[:, 1]))
            word = (
                "high: adds little diversification"
                if corr > 0.7
                else ("moderate" if corr > 0.3 else "low: diversifies")
            )
            corr_text = f"{corr:+.2f} correlation of daily returns over the last year ({word})"

    return TradePlan(
        symbol=symbol,
        as_of=as_of,
        action=action,
        action_text=text,
        entry=entry,
        stop=stop,
        stop_source=stop_src,
        targets=targets,
        support=support,
        resistance=resistance,
        atr=atr,
        target_weight=tw,
        size_gbp=size_gbp,
        size_weight=w,
        size_reason=f"limited by {why}",
        risk_gbp=risk_gbp,
        uk_fund=uk_fund(symbol)
        if symbol in UK_FUNDS
        else (
            "US shares: buy through a UK platform that offers US stocks (in an ISA if possible)"
            if symbol.isalpha() and symbol not in lim["allowed_assets"]
            else uk_fund(symbol)
        ),
        allowed=allowed,
        invalidation=invalid,
        confidence=conf,
        confidence_points=pts,
        correlation=corr,
        correlation_text=corr_text,
        notes=notes,
    )


def holdings_returns(daily: dict[str, pd.DataFrame], weights: dict[str, float]) -> pd.Series | None:
    """Daily returns of a fixed mix (e.g. the main paper account's 70/30), for the overlap check."""
    parts = []
    for t, w in weights.items():
        if t in daily and w > 0:
            parts.append(daily[t]["Close"].pct_change(fill_method=None) * w)
    if not parts:
        return None
    return pd.concat(parts, axis=1).sum(axis=1, min_count=len(parts))
