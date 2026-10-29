"""Portfolio-level simulator (EXP-032 onwards): parity with the sleeve engine, cash limits, flows, breakers."""

import numpy as np
import pandas as pd
from conftest import make_prices

from aurum import strategy as S
from aurum.portfolio import drawdown_breaker, loss_limit, simulate_portfolio


def test_single_asset_matches_sleeve_engine():
    rng = np.random.default_rng(0)
    closes = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 300)))
    opens = closes * (1 + rng.normal(0, 0.002, 300))
    p = make_prices(closes, opens)
    w = pd.Series(np.clip(0.5 + 0.3 * np.sin(np.arange(300) / 20), 0, 1), index=p.index)
    a = S.simulate_weights(p, w, cost_bps=10, cash_rate=0.02, band=0.05)
    b = simulate_portfolio({"X": p}, w.to_frame("X"), cost_bps={"X": 10}, cash_rate=0.02, band=0.05)
    np.testing.assert_allclose(a.daily["value"].to_numpy(), b.daily["value"].to_numpy(), rtol=1e-10)


def test_never_borrows_and_sells_before_buying():
    p = {"A": make_prices([100.0] * 5), "B": make_prices([50.0] * 5)}
    idx = p["A"].index
    tgt = pd.DataFrame({"A": [0.9, 0.1, 0.1, 0.1, 0.1], "B": [0.9, 0.9, 0.9, 0.9, 0.9]}, index=idx)
    r = simulate_portfolio(p, tgt, cost_bps={"A": 0, "B": 0}, band=0.0)
    assert (r.daily["cash"] >= -1e-12).all()
    # day 1: asks for 180% -> scaled to 100% (50/50); day 2: A sold to 10%, then B bought up to 90%
    np.testing.assert_allclose(r.weights.iloc[1].to_numpy(), [0.5, 0.5], atol=1e-9)
    np.testing.assert_allclose(r.weights.iloc[2].to_numpy(), [0.1, 0.9], atol=1e-9)


def test_contributions_are_not_counted_as_returns():
    p = {"A": make_prices([100.0] * 6)}
    tgt = pd.DataFrame({"A": [0.5] * 6}, index=p["A"].index)
    flows = pd.Series([0, 0, 1.0, 0, 0, 0], index=p["A"].index)
    r = simulate_portfolio(p, tgt, cost_bps={"A": 0}, contributions=flows)
    assert np.allclose(r.daily["ret"], 0.0)
    assert np.isclose(r.daily["value"].iloc[-1], 2.0)


def test_drawdown_breaker_halves_and_releases():
    rule = drawdown_breaker(0.15, 0.075, 0.5)
    eq = [1.0, 0.9, 0.84, 0.88, 0.95]
    out = [rule(i, np.array(eq[: i + 1]), None) for i in range(len(eq))]
    assert out == [1.0, 1.0, 0.5, 0.5, 1.0]


def test_loss_limit_pauses_for_the_set_days():
    rule = loss_limit(2, 0.05, 0.5, 2)
    eq = [1.0, 1.0, 0.94, 0.95, 0.96, 0.97, 0.98]
    out = [rule(i, np.array(eq[: i + 1]), None) for i in range(len(eq))]
    assert out[2] == 0.5 and out[4] == 0.5 and out[6] == 1.0
