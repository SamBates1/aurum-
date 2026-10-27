"""Turn each analysis into a score in [-1, 1], then combine into a decision
with plain-English reasons. Missing components are dropped and the remaining
weights re-normalised."""
import math

import numpy as np


def _clip(x: float) -> float:
    return float(max(-1.0, min(1.0, x)))


def ml_skill(auc: float, floor: float = 0.50, full: float = 0.56) -> float:
    """0 = no proven skill (coin flip), 1 = enough out-of-sample skill to trust fully."""
    if full <= floor:
        return 1.0
    return float(max(0.0, min(1.0, (auc - floor) / (full - floor))))


def ml_score(prob_up: float, auc: float | None = None, skill: float = 1.0) -> tuple[float, list[str]]:
    s = _clip((prob_up - 0.5) * 4)  # 0.625 -> +0.5, 0.75 -> +1
    reasons = [f"Model gives a {prob_up:.0%} chance of a rise over the forecast horizon"]
    if auc is not None:
        reasons.append(f"Out-of-sample AUC {auc:.3f}, so the vote counts at {skill:.0%} strength")
    return s, reasons


def technical_score(row) -> tuple[float, list[str]]:
    parts, reasons = [], []
    up50, up200 = row["sma50_gap"] > 0, row["sma200_gap"] > 0
    if up50 and up200:
        parts.append(1.0); reasons.append("Price is above its 50- and 200-day averages (uptrend)")
    elif not up50 and not up200:
        parts.append(-1.0); reasons.append("Price is below its 50- and 200-day averages (downtrend)")
    else:
        parts.append(0.0); reasons.append("Mixed trend: price is between its 50- and 200-day averages")
    parts.append(0.5 if row["macd_hist"] > 0 else -0.5)
    reasons.append(f"MACD momentum is {'positive' if row['macd_hist'] > 0 else 'negative'}")
    rsi = row["rsi_14"]
    if rsi > 70:
        parts.append(-0.5); reasons.append(f"RSI {rsi:.0f}: overbought, pullback risk")
    elif rsi < 30:
        parts.append(0.5); reasons.append(f"RSI {rsi:.0f}: oversold, bounce potential")
    return _clip(float(np.mean(parts))), reasons


def sentiment_score(sent: dict) -> tuple[float | None, list[str]]:
    if sent.get("score") is None:
        return None, []
    s = sent["score"]
    mood = "positive" if s > 0.1 else "negative" if s < -0.1 else "neutral"
    return _clip(s * 2), [f"News tone is {mood} ({s:+.2f} across {sent['n']} recent headlines)"]


def fundamental_score(f: dict) -> tuple[float | None, list[str]]:
    if not f:
        return None, []
    parts, reasons = [], []
    pe = f.get("forwardPE") or f.get("trailingPE")
    if pe and pe > 0:
        if pe < 15: parts.append(0.5); reasons.append(f"Cheap on earnings (P/E {pe:.1f})")
        elif pe > 30: parts.append(-0.5); reasons.append(f"Expensive on earnings (P/E {pe:.1f})")
        else: parts.append(0.0)
    m = f.get("profitMargins")
    if m is not None:
        parts.append(0.5 if m > 0.15 else -0.5 if m < 0 else 0.0)
        if m > 0.15 or m < 0: reasons.append(f"Profit margin {m:.0%}")
    de = f.get("debtToEquity")
    if de is not None and de > 100:
        parts.append(-0.5); reasons.append(f"High leverage (debt/equity {de:.0f}%)")
    fcf = f.get("freeCashflow")
    if fcf is not None:
        parts.append(0.3 if fcf > 0 else -0.3)
        reasons.append("Generating free cash flow" if fcf > 0 else "Burning cash (negative free cash flow)")
    if not parts:
        return None, []
    return _clip(float(np.mean(parts))), reasons


def combine(components: dict, weights: dict, buy_above: float, sell_below: float) -> dict:
    """components: name -> (score or None, reasons)."""
    live = {k: v for k, v in components.items() if v[0] is not None and not math.isnan(v[0])}
    total_w = sum(weights[k] for k in live)
    total = sum(weights[k] * live[k][0] for k in live) / total_w if total_w else 0.0
    decision = "BUY" if total >= buy_above else "SELL" if total <= sell_below else "HOLD"
    return {
        "decision": decision,
        "score": total,
        "confidence": min(1.0, abs(total)),
        "components": {k: {"score": v[0], "weight": weights[k] / total_w, "reasons": v[1]} for k, v in live.items()},
    }
