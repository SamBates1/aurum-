"""Headline sentiment. Uses VADER (rule-based, fast, free); falls back to a
tiny finance lexicon if VADER isn't installed. Swap in an LLM later."""

import re
from datetime import datetime, timedelta, timezone

_POS = {
    "rally",
    "rallies",
    "surge",
    "surges",
    "gain",
    "gains",
    "upgrade",
    "upgrades",
    "record",
    "beat",
    "beats",
    "strong",
    "supports",
    "rise",
    "rises",
    "soar",
    "soars",
    "bullish",
    "higher",
    "boost",
}
_NEG = {
    "fall",
    "falls",
    "slip",
    "slips",
    "drop",
    "drops",
    "downgrade",
    "weak",
    "weaker",
    "miss",
    "misses",
    "plunge",
    "plunges",
    "bearish",
    "lower",
    "cut",
    "cuts",
    "weighs",
    "loss",
    "slump",
}

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    _vader = SentimentIntensityAnalyzer()
except ImportError:  # pragma: no cover
    _vader = None


def score_text(text: str) -> float:
    if _vader is not None:
        base = _vader.polarity_scores(text)["compound"]
    else:
        base = 0.0
    words = re.findall(r"[a-z]+", text.lower())
    lex = sum(w in _POS for w in words) - sum(w in _NEG for w in words)
    # VADER misses finance verbs like "slips" or "rallies"; blend in the lexicon
    return max(-1.0, min(1.0, 0.6 * base + 0.4 * max(-1, min(1, lex))))


def headline_sentiment(items: list[dict], max_age_days: int = 7, now: datetime | None = None) -> dict:
    """Average sentiment of headlines published in the window (now - max_age_days, now].
    Undated or future-dated headlines are excluded."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max_age_days)
    scored = []
    for it in items:
        pub = it.get("published")
        if pub is None:
            continue
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        if pub < cutoff or pub > now:
            continue
        scored.append({**it, "sentiment": score_text(it["title"])})
    score = sum(s["sentiment"] for s in scored) / len(scored) if scored else None
    return {"score": score, "n": len(scored), "headlines": scored}
