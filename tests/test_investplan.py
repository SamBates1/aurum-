"""Platform phase 6: complete plans, sizing, stops, targets, costs and currency."""

import numpy as np
import pandas as pd
import pytest

from aurum import investplan as IP


def _daily(trend=0.001, n=400, seed=7):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(trend, 0.012, n)))
    idx = pd.bdate_range(end="2026-10-29", periods=n)
    return pd.DataFrame({"Open": c, "High": c * 1.01, "Low": c * 0.99, "Close": c, "Volume": 1e6}, index=idx)


def test_swing_plan_sizes_by_risk_and_explains_levels():
    p = IP.build("AAA", _daily(), "swing", "BUY", pot_usd=50_000, usd_per_gbp=1.30, setup="breakout")
    assert p.action == "BUY" and p.stop < p.price and p.entry_zone[0] < p.price < p.entry_zone[1]
    assert p.max_loss_usd == pytest.approx(min(0.0075 * 50_000, p.max_loss_usd), rel=1e-6)
    assert p.max_loss_usd <= 0.0075 * 50_000 + 0.01 and p.allocation_usd <= 0.10 * 50_000 + 0.01
    assert [round(t[2], 1) for t in p.targets if "R" in t[0]] == [2.0, 3.0]
    assert all(k in p.reasons for k in ("stop", "entry", "size", "targets"))
    assert "1 to 8 weeks" in p.holding_period and any("ISA" in n for n in p.notes)
    assert p.costs["uk_platform_pct"] == pytest.approx(0.0075 * 2 + 3e-4 * 2)


def test_long_term_plan_stages_entries_and_respects_the_cap():
    p = IP.build("BBB", _daily(), "long-term", "BUY", pot_usd=50_000, usd_per_gbp=1.30)
    assert len(p.tranches) == 3 and sum(t[2] for t in p.tranches) == pytest.approx(p.shares, rel=1e-6)
    assert p.allocation_usd <= 0.10 * 50_000 + 0.01 and "200-day" in p.reasons["stop"]
    held = IP.build("BBB", _daily(), "long-term", "BUY", 50_000, 1.30, held_shares=48)
    assert held.allocation_usd < p.allocation_usd  # existing holding counts against the cap
    whole = IP.build("BBB", _daily(), "long-term", "BUY", 50_000, 1.30, fractionable=False)
    assert whole.shares == int(whole.shares)


def test_wait_exit_reduce_and_portfolio_blocks():
    d = _daily()
    assert IP.build("C", d, "swing", "WAIT", 50_000, 1.3).action == "WAIT"
    assert IP.build("C", d, "swing", "AVOID", 50_000, 1.3).action == "NO ENTRY"
    ex = IP.build("C", d, "long-term", "SELL", 50_000, 1.3, held_shares=10)
    assert ex.action == "EXIT" and ex.shares == -10
    rd = IP.build("C", d, "long-term", "REDUCE", 50_000, 1.3, held_shares=10)
    assert rd.action == "REDUCE" and rd.shares == -5
    blk = IP.build(
        "C",
        d,
        "long-term",
        "BUY",
        50_000,
        1.3,
        portfolio_check={"verdict": "duplicate", "problems": ["moves like SPY"]},
    )
    assert blk.action == "NO ADDITION" and "SPY" in blk.reasons["action"]


def test_uk_listed_costs_use_stamp_duty_not_fx():
    c = IP.costs_for(13_000, 1.30, uk_listed=True, liquid=True)
    assert c["uk_platform_gbp"] == pytest.approx(10_000 * (3e-4 * 2 + 0.005))
    us = IP.costs_for(13_000, 1.30, uk_listed=False, liquid=False)
    assert us["uk_platform_gbp"] == pytest.approx(10_000 * (15e-4 * 2 + 0.0075 * 2))
