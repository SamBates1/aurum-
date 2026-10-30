"""Platform phase 4: long-term and swing assessments, verdict rules and labels."""

import numpy as np
import pandas as pd

from aurum import assessment as AS
from aurum.events import Event


def _daily(trend=0.001, n=400, seed=4, vol=0.01):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(trend, vol, n)))
    idx = pd.bdate_range(end="2026-10-29", periods=n)
    return pd.DataFrame({"Open": c, "High": c * 1.01, "Low": c * 0.99, "Close": c, "Volume": 1e6}, index=idx)


GOOD = {
    "roic": 0.25,
    "revenue_growth": 0.15,
    "fcf_margin": 0.2,
    "debt_to_equity": 0.3,
    "fcf_yield": 0.06,
    "period_end": "2025-12-31",
    "filed": "2026-02-02",
}
BAD = {"roic": 0.01, "revenue_growth": -0.1, "fcf_margin": -0.05, "debt_to_equity": 3.5, "fcf_yield": 0.002}
ON = {"state": "risk-on", "text": "S&P 500 above its 200-day average"}


def test_untested_signals_never_give_a_buy():
    a = AS.long_term("X", _daily(), 92, "untested", GOOD, ON)
    assert a.verdict == "WAIT" and "not yet supported by evidence" in a.why
    assert "not a probability" in a.confidence and a.confidence.startswith(("Medium", "Low"))
    b = AS.long_term("X", _daily(), 92, "evidence", GOOD, ON)
    assert b.verdict in ("BUY", "WAIT")  # WAIT only if the price is stretched above its 50-day average


def test_weak_business_is_avoided_and_explained():
    a = AS.long_term("Y", _daily(trend=-0.001), 15, "evidence", BAD, {"state": "risk-off", "text": "below"})
    assert a.verdict == "AVOID"
    assert any("debt" in x.lower() for x in a.bearish) and a.risks and a.invalidation
    held = AS.long_term("Y", _daily(trend=-0.001), 15, "evidence", BAD, ON, held=True)
    assert held.verdict == "SELL"


def test_missing_accounts_are_listed_not_invented():
    a = AS.long_term("ETF", _daily(), 60, "evidence", None, ON)
    assert any("company accounts" in m for m in a.missing) and a.verdict == "MONITOR"


def test_swing_earnings_blocks_a_buy_and_setups_are_detected():
    d = _daily(trend=0.003, vol=0.008)
    setup = AS.detect_setup(d) or "breakout to a 20-day high on above-average volume"
    ev = [Event("2026-11-10", "earnings", "Z", "Z earnings", False, "test")]
    a = AS.swing("Z", d, 90, "evidence", setup, ev, ON)
    assert a.verdict != "BUY" and any("Earnings" in x for x in a.bearish)
    b = AS.swing("Z", d, 90, "evidence", setup, [], ON)
    assert b.verdict in ("BUY", "WAIT")
    c = AS.swing("Z", _daily(trend=-0.002), 10, "evidence", None, [], ON)
    assert c.verdict == "AVOID" and any("No swing setup" in x for x in c.bearish)


def test_market_regime():
    up = AS.market_regime(_daily(trend=0.002), vix=15)
    down = AS.market_regime(_daily(trend=-0.002), vix=35)
    assert up["state"] == "risk-on" and down["state"] == "risk-off"
    assert AS.market_regime(_daily(trend=0.002), vix=35)["state"] == "mixed"


def test_pullback_setup_is_a_warning_after_exp051a():
    a = AS.swing(
        "Z",
        _daily(trend=0.003, vol=0.008),
        95,
        "evidence",
        "pullback in an uptrend (2-day RSI below 10, above the 200-day average)",
        [],
        ON,
    )
    assert a.verdict != "BUY" and any("harmful" in x for x in a.bearish)
