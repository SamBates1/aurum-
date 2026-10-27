"""Plain-English explanations and live-only context scores.

The traded score itself is computed in strategy.py. This module explains it,
and scores the two live-only inputs (news sentiment and fundamentals), which
have no point-in-time history and therefore carry weight 0 unless the user
deliberately opts in (see config.yaml -> strategy.weights).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .strategy import technical_components


def _clip(x: float) -> float:
    return float(max(-1.0, min(1.0, x)))


def ml_reasons(prob_up: float, auc: float, skill: float) -> list[str]:
    if not np.isfinite(prob_up):
        return ["Model prediction unavailable (missing or invalid features): ML gets no vote"]
    auc_txt = f"{auc:.3f}" if np.isfinite(auc) else "not yet measurable"
    return [
        f"Model gives a {prob_up:.0%} chance of a rise over the forecast horizon",
        f"Out-of-sample AUC {auc_txt}, so its vote counts at {skill:.0%} strength",
    ]


def technical_reasons(row: pd.Series) -> list[str]:
    c = technical_components(row.to_frame().T).iloc[0]
    reasons = []
    if c["trend"] == 1:
        reasons.append("Price is above its 50- and 200-day averages (uptrend)")
    elif c["trend"] == -1:
        reasons.append("Price is below its 50- and 200-day averages (downtrend)")
    elif np.isfinite(c["trend"]):
        reasons.append("Mixed trend: price is between its 50- and 200-day averages")
    if np.isfinite(c["momentum"]):
        reasons.append(f"MACD momentum is {'positive' if c['momentum'] > 0 else 'negative'}")
    if np.isfinite(c["rsi"]):
        word = "overbought, pullback risk" if c["rsi"] < 0 else "oversold, bounce potential"
        reasons.append(f"RSI {row['rsi_14']:.0f}: {word}")
    return reasons


def sentiment_score(sent: dict) -> tuple[float | None, list[str]]:
    if sent.get("score") is None:
        return None, ["No recent timestamped headlines"]
    s = sent["score"]
    mood = "positive" if s > 0.1 else "negative" if s < -0.1 else "neutral"
    return _clip(s * 2), [f"News tone is {mood} ({s:+.2f} across {sent['n']} recent headlines)"]


def fundamental_score(f: dict) -> tuple[float | None, list[str]]:
    if not f:
        return None, []
    parts, reasons = [], []
    pe = f.get("forwardPE") or f.get("trailingPE")
    if pe and pe > 0:
        if pe < 15:
            parts.append(0.5)
            reasons.append(f"Cheap on earnings (P/E {pe:.1f})")
        elif pe > 30:
            parts.append(-0.5)
            reasons.append(f"Expensive on earnings (P/E {pe:.1f})")
        else:
            parts.append(0.0)
    m = f.get("profitMargins")
    if m is not None:
        parts.append(0.5 if m > 0.15 else -0.5 if m < 0 else 0.0)
        if m > 0.15 or m < 0:
            reasons.append(f"Profit margin {m:.0%}")
    de = f.get("debtToEquity")
    if de is not None and de > 100:
        parts.append(-0.5)
        reasons.append(f"High leverage (debt/equity {de:.0f}%)")
    fcf = f.get("freeCashflow")
    if fcf is not None:
        parts.append(0.3 if fcf > 0 else -0.3)
        reasons.append("Generating free cash flow" if fcf > 0 else "Burning cash (negative free cash flow)")
    if not parts:
        return None, []
    return _clip(float(np.mean(parts))), reasons
