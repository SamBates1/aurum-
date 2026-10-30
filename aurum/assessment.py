"""Investment assessments (platform phase 4): a separate long-term and swing verdict for one instrument.

Each assessment combines the scanner's evidence-weighted score with company accounts, risk, market conditions,
events and data quality, by fixed and visible rules (no AI, no hidden weights). It lists the bullish and bearish
evidence, conflicts, risks, assumptions, missing information and what would invalidate the idea, and ends in one
verdict:

  not held:  BUY · WAIT (attractive, but no good entry now) · MONITOR (some merit) · AVOID
  held:      HOLD · REDUCE · SELL

The confidence label is an assessment of how much of the evidence agrees, never a probability of profit. While the
scanner's signals are untested (EXP-051 pending or failed), every verdict carries that label and BUY is capped to
WAIT: an untested ranking is not a reason to buy.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .indicators import compute, pivot_levels


@dataclass
class Assessment:
    symbol: str
    horizon: str  # "long-term" or "swing"
    verdict: str
    score: float | None
    confidence: str
    evidence_status: str  # "evidence" or "untested"
    bullish: list[str] = field(default_factory=list)
    bearish: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    invalidation: list[str] = field(default_factory=list)
    why: str = ""

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def market_regime(spy: pd.DataFrame, vix: float | None = None) -> dict:
    """Risk-on / risk-off from the S&P 500's trend and (if known) the VIX level."""
    c = spy["Close"].dropna()
    above = bool(len(c) >= 200 and c.iloc[-1] > c.rolling(200).mean().iloc[-1])
    calm = vix is None or vix < 25
    state = "risk-on" if above and calm else ("risk-off" if not above and not calm else "mixed")
    text = f"S&P 500 {'above' if above else 'below'} its 200-day average" + (
        f", VIX {vix:.0f}" if vix is not None else ""
    )
    return {"state": state, "text": text}


def _technicals(daily: pd.DataFrame) -> dict:
    c = daily["Close"].dropna()
    t = {"close": float(c.iloc[-1])}
    t["sma50"] = float(c.rolling(50).mean().iloc[-1]) if len(c) >= 50 else np.nan
    t["sma200"] = float(c.rolling(200).mean().iloc[-1]) if len(c) >= 200 else np.nan
    t["atr_pct"] = float(compute("atr_pct", daily, {"n": 14}).iloc[-1]) if len(c) > 20 else np.nan
    t["rsi14"] = float(compute("rsi", daily, {"n": 14}).iloc[-1]) if len(c) > 20 else np.nan
    t["adx"] = float(compute("adx", daily, {"n": 14}).iloc[-1]) if len(c) > 40 else np.nan
    t["mom_12_1"] = float(c.iloc[-21] / c.iloc[-252] - 1) if len(c) > 252 else np.nan
    t["drawdown"] = float(c.iloc[-1] / c.tail(252).max() - 1)
    lv = pivot_levels(daily.tail(260), 5).iloc[-1]
    t["support"], t["resistance"] = float(lv["support"]), float(lv["resistance"])
    return t


def _confidence(bull: int, bear: int, untested: bool) -> str:
    n = bull + bear
    share = bull / n if n else 0.5
    level = "High" if share >= 0.75 and n >= 4 else ("Medium" if share >= 0.5 else "Low")
    if untested and level == "High":
        level = "Medium"
    return f"{level} ({bull} for, {bear} against; an assessment, not a probability)"


def long_term(
    symbol: str,
    daily: pd.DataFrame,
    score: float | None,
    evidence_status: str,
    fundamentals: dict | None = None,
    regime: dict | None = None,
    held: bool = False,
) -> Assessment:
    t = _technicals(daily)
    f = fundamentals or {}
    a = Assessment(symbol, "long-term", "", score, "", evidence_status)
    a.assumptions.append("Company accounts as filed with the SEC by today; nothing filed later is used.")
    a.assumptions.append("Holding period of months to years; short swings are ignored.")
    # trend and momentum
    if np.isfinite(t["sma200"]):
        (a.bullish if t["close"] > t["sma200"] else a.bearish).append(
            f"Price {'above' if t['close'] > t['sma200'] else 'below'} its 200-day average"
        )
    else:
        a.missing.append("less than 200 days of prices")
    if np.isfinite(t["mom_12_1"]):
        (a.bullish if t["mom_12_1"] > 0 else a.bearish).append(f"12-month momentum {t['mom_12_1']:+.0%}")
    # company accounts
    if f:
        for k, good, bad, label in (
            ("roic", 0.12, 0.05, "Return on invested capital"),
            ("revenue_growth", 0.08, 0.0, "Revenue growth"),
            ("fcf_margin", 0.10, 0.0, "Free-cash-flow margin"),
        ):
            v = f.get(k)
            if v is None:
                a.missing.append(label.lower())
            elif v >= good:
                a.bullish.append(f"{label} {v:.0%}")
            elif v < bad:
                a.bearish.append(f"{label} {v:.0%}")
        de = f.get("debt_to_equity")
        if de is not None and de > 2:
            a.bearish.append(f"High debt: {de:.1f} times equity")
            a.risks.append("Heavy debt makes the company sensitive to rates and downturns")
        fy = f.get("fcf_yield")
        if fy is not None:
            (a.bullish if fy > 0.05 else a.bearish if fy < 0.01 else a.conflicts).append(
                f"Free-cash-flow yield {fy:.1%}" + (" (cheap)" if fy > 0.05 else " (expensive)" if fy < 0.01 else "")
            )
        if f.get("period_end"):
            a.assumptions.append(f"Latest annual accounts: year to {f['period_end']}, filed {f.get('filed')}")
    else:
        a.missing.append("company accounts (an ETF, or not an SEC filer)")
    if regime:
        (
            a.bullish if regime["state"] == "risk-on" else a.bearish if regime["state"] == "risk-off" else a.conflicts
        ).append(f"Market: {regime['state']} ({regime['text']})")
    if t["drawdown"] < -0.3:
        a.risks.append(f"{t['drawdown']:.0%} below its 1-year high")
    a.risks.append("A single company can fall sharply on news; size it as one position among many")
    if any("momentum" in x for x in a.bullish) and any(("Revenue" in x or "Return" in x) for x in a.bearish):
        a.conflicts.append("Price is rising while the business numbers are weak")
    if np.isfinite(t["sma200"]):
        a.invalidation.append(f"Two consecutive monthly closes below the 200-day average (now ${t['sma200']:,.2f})")
    a.invalidation.append("Revenue or return on capital falling for two filings in a row")

    stretched = np.isfinite(t["sma50"]) and t["close"] > 1.15 * t["sma50"]
    s = score if score is not None else 50.0
    untested = evidence_status != "evidence"
    if held:
        a.verdict = "SELL" if s < 20 and len(a.bearish) > len(a.bullish) else ("REDUCE" if s < 35 else "HOLD")
    elif s >= 80 and len(a.bullish) > len(a.bearish):
        a.verdict = "WAIT" if (stretched or untested) else "BUY"
    elif s >= 55:
        a.verdict = "MONITOR"
    elif s <= 20 or len(a.bearish) >= len(a.bullish) + 3:
        a.verdict = "AVOID"
    else:
        a.verdict = "MONITOR"
    reasons = []
    if stretched and a.verdict == "WAIT":
        reasons.append(f"price is {t['close'] / t['sma50'] - 1:.0%} above its 50-day average: wait for a pullback")
    if untested and s >= 80:
        reasons.append("the scanner's signals are not yet supported by evidence (EXP-051), so not a BUY")
    a.why = f"Score {s:.0f}/100; {len(a.bullish)} points for, {len(a.bearish)} against" + (
        "; " + "; ".join(reasons) if reasons else ""
    )
    a.confidence = _confidence(len(a.bullish), len(a.bearish), untested)
    return a


def swing(
    symbol: str,
    daily: pd.DataFrame,
    score: float | None,
    evidence_status: str,
    setup: str | None = None,
    events: list | None = None,
    regime: dict | None = None,
    held: bool = False,
) -> Assessment:
    t = _technicals(daily)
    a = Assessment(symbol, "swing", "", score, "", evidence_status)
    a.assumptions.append("Holding period 1 to 8 weeks; decided on daily closes, bought at the next open.")
    if setup:
        a.bullish.append(f"Setup: {setup}")
    else:
        a.bearish.append("No swing setup (breakout, pullback in an uptrend or strong trend) right now")
    if np.isfinite(t["adx"]):
        (a.bullish if t["adx"] > 25 else a.conflicts).append(
            f"Trend strength ADX {t['adx']:.0f}" + (" (trending)" if t["adx"] > 25 else " (weak trend)")
        )
    if np.isfinite(t["rsi14"]):
        if t["rsi14"] > 75:
            a.bearish.append(f"RSI {t['rsi14']:.0f}: stretched, entry risk is high")
        elif t["rsi14"] < 30:
            a.conflicts.append(f"RSI {t['rsi14']:.0f}: oversold (bounce possible, trend down)")
    if np.isfinite(t["sma50"]):
        (a.bullish if t["close"] > t["sma50"] else a.bearish).append(
            f"Price {'above' if t['close'] > t['sma50'] else 'below'} its 50-day average"
        )
    gap = [e for e in (events or []) if getattr(e, "gap_risk", False)]
    earnings = [e for e in gap if e.kind == "earnings"]
    if earnings:
        a.bearish.append(f"Earnings on {earnings[0].date} inside the trade window (overnight gap risk)")
        a.risks.append("An earnings surprise can gap the price through the stop")
    for e in gap:
        if e.kind == "fomc":
            a.risks.append(f"Fed decision on {e.date}")
    if regime:
        (
            a.bullish if regime["state"] == "risk-on" else a.bearish if regime["state"] == "risk-off" else a.conflicts
        ).append(f"Market: {regime['state']}")
    if np.isfinite(t["atr_pct"]):
        a.risks.append(f"Typical daily move {t['atr_pct']:.1%}: size so a stop hit loses a fixed amount")
    else:
        a.missing.append("volatility (ATR)")
    if np.isfinite(t["support"]):
        a.invalidation.append(f"A daily close below support at ${t['support']:,.2f}")
    a.invalidation.append("No progress within 4 weeks (the setup has failed)")

    s = score if score is not None else 50.0
    untested = evidence_status != "evidence"
    stretched = np.isfinite(t["rsi14"]) and t["rsi14"] > 75
    if held:
        a.verdict = "SELL" if (not setup and np.isfinite(t["sma50"]) and t["close"] < t["sma50"]) else "HOLD"
    elif s >= 80 and setup and not earnings and (regime or {}).get("state") != "risk-off":
        a.verdict = "WAIT" if (stretched or untested) else "BUY"
    elif s >= 55 or setup:
        a.verdict = "MONITOR"
    else:
        a.verdict = "AVOID"
    a.why = (
        f"Score {s:.0f}/100; "
        + (f"setup: {setup}" if setup else "no setup")
        + ("; signals not yet supported by evidence" if untested else "")
    )
    a.confidence = _confidence(len(a.bullish), len(a.bearish), untested)
    return a


def detect_setup(daily: pd.DataFrame) -> str | None:
    """Which swing setup (if any) is present on the last completed day (same definitions as EXP-051)."""
    c, v = daily["Close"], daily["Volume"]
    if len(c) < 200:
        return None
    if c.iloc[-1] >= c.tail(20).max() and v.iloc[-1] > v.tail(50).mean():
        return "breakout to a 20-day high on above-average volume"
    rsi2 = compute("rsi", daily, {"n": 2}).iloc[-1]
    if c.iloc[-1] > c.rolling(200).mean().iloc[-1] and rsi2 < 10:
        return "pullback in an uptrend (2-day RSI below 10, above the 200-day average)"
    adx = compute("adx", daily, {"n": 14}).iloc[-1]
    if adx > 25 and c.iloc[-1] > c.rolling(50).mean().iloc[-1]:
        return "strong trend (ADX above 25, above the 50-day average)"
    return None
