"""Performance metric formulas and portfolio aggregation."""

import numpy as np
import pandas as pd
import pytest

from aurum.backtest import combine_sleeves, performance, relative, slice_sim
from aurum.stats import bootstrap_sharpe
from aurum.strategy import SimResult


def make_sim(returns, start="2020-01-01"):
    r = pd.Series(returns, index=pd.bdate_range(start, periods=len(returns)), dtype=float)
    value = (1 + r).cumprod()
    daily = pd.DataFrame(
        {"value": value, "cash": 0.0, "shares": 1.0, "invested": 1.0, "exposure": 1.0, "cost": 0.0, "traded": 0.0}
    )
    daily["ret"] = r
    trades = pd.DataFrame(columns=["entry_value", "exit_reason", "pnl", "ret", "days"])
    return SimResult(daily, trades)


def test_sortino_uses_downside_deviation_over_all_days():
    """Regression: the old code used the std of negative days only."""
    r = np.array([0.01, -0.02, 0.03, -0.01, 0.0] * 60)
    p = performance(make_sim(r))
    downside = np.sqrt(np.mean(np.minimum(r, 0) ** 2))
    expected = r.mean() * 252 / (downside * np.sqrt(252))
    assert p["sortino"] == pytest.approx(expected)
    wrong = r.mean() * 252 / (r[r < 0].std(ddof=1) * np.sqrt(252))
    assert p["sortino"] != pytest.approx(wrong)


def test_sharpe_drawdown_calmar():
    r = np.array([0.01, -0.005] * 200)
    p = performance(make_sim(r))
    assert p["sharpe"] == pytest.approx(r.mean() / r.std(ddof=1) * np.sqrt(252))
    eq = np.cumprod(1 + r)
    mdd = (eq / np.maximum.accumulate(eq) - 1).min()
    assert p["max_drawdown"] == pytest.approx(mdd)
    assert p["calmar"] == pytest.approx(p["cagr"] / abs(mdd))


def test_risk_free_is_subtracted_with_one_day_lag():
    """Cash earns yesterday's rate, so a portfolio of pure cash has zero excess return."""
    idx = pd.bdate_range("2020-01-01", periods=300)
    rf = pd.Series(np.linspace(0.0, 0.05, 300), index=idx)
    cash_returns = (rf.shift(1).fillna(0.0) / 252).to_numpy()
    p = performance(make_sim(cash_returns), rf)
    assert np.isnan(p["sharpe"])  # excess return is identically zero


def test_zero_volatility_and_tiny_samples_are_safe():
    assert np.isnan(performance(make_sim([0.0] * 50))["sharpe"])
    assert performance(make_sim([0.01])) == {"days": 1}


def test_relative_to_itself():
    s = make_sim(np.random.default_rng(1).normal(0, 0.01, 300))
    rel = relative(s, s)
    assert rel["beta"] == pytest.approx(1.0) and rel["tracking_error"] == pytest.approx(0.0)


def test_slice_rebases_returns():
    s = make_sim([0.5] + [0.0] * 9)
    sl = slice_sim(s, s.daily.index[0], None)
    assert performance(sl)["total_return"] == pytest.approx(0.0)


def test_portfolio_weights_and_spare_cash():
    a, b = make_sim([0.01] * 10), make_sim([-0.01] * 10)
    port = combine_sleeves({"a": a, "b": b}, {"a": 0.25, "b": 0.25}, cash_rate=0.0)
    v = port.daily["value"]
    expected = 0.25 * a.daily["value"] / a.daily["value"].iloc[0] + 0.25 * b.daily["value"] / b.daily["value"].iloc[0]
    assert np.allclose(v, expected + 0.5)


def test_bootstrap_interval_contains_point_estimate():
    r = pd.Series(np.random.default_rng(2).normal(0.0005, 0.01, 1500), index=pd.bdate_range("2015-01-01", periods=1500))
    b = bootstrap_sharpe(r, block=21, reps=300, seed=1)
    assert b["sharpe_p05"] < b["sharpe"] < b["sharpe_p95"]
