"""The shared strategy rules and the simulator's accounting."""

import numpy as np
import pandas as pd
import pytest
from conftest import make_prices

from aurum import strategy as S


def sim(prices, decisions, vol=0.15, atr=1.0, **kw):
    idx = prices.index
    kw.setdefault("cost_bps", 0.0)
    kw.setdefault("stop_atr_mult", None)
    return S.simulate(prices, pd.Series(decisions, idx, dtype=object), pd.Series(vol, idx), pd.Series(atr, idx), **kw)


# ---- scores and thresholds -------------------------------------------------
def test_ml_score_mapping_and_invalid_probabilities():
    assert S.ml_score(0.5) == 0
    assert S.ml_score(0.75) == 1
    assert S.ml_score(0.625) == pytest.approx(0.5)
    assert np.isnan(S.ml_score(1.5)) and np.isnan(S.ml_score(float("nan")))


def test_technical_score_components():
    F = pd.DataFrame(
        {
            "sma50_gap": [0.1, -0.1, 0.1],
            "sma200_gap": [0.1, -0.1, -0.1],
            "macd_hist": [1, -1, 1],
            "rsi_14": [75, 25, 50],
        }
    )
    s = S.technical_score(F)
    assert s.iloc[0] == pytest.approx((1 + 0.5 - 0.5) / 3)  # uptrend, +momentum, overbought
    assert s.iloc[1] == pytest.approx((-1 - 0.5 + 0.5) / 3)  # downtrend, -momentum, oversold
    assert s.iloc[2] == pytest.approx((0 + 0.5) / 2)  # mixed trend, RSI not extreme -> not counted


def test_decision_thresholds_are_inclusive():
    assert S.decision_for(0.20, 0.20, -0.20) == S.BUY
    assert S.decision_for(-0.20, 0.20, -0.20) == S.SELL
    assert S.decision_for(0.1999, 0.20, -0.20) == S.HOLD
    assert S.decision_for(float("nan"), 0.20, -0.20) == S.HOLD


def test_combine_skips_missing_and_zero_weight():
    assert S.combine({"a": 1.0, "b": None}, {"a": 1.0, "b": 1.0}) == 1.0
    assert S.combine({"a": 1.0, "b": -1.0}, {"a": 1.0, "b": 0.0}) == 1.0
    assert np.isnan(S.combine({"a": None}, {"a": 1.0}))


def test_coin_flip_model_cannot_dominate():
    """Regression: a confident model with no proven skill must not override other signals."""
    idx = pd.RangeIndex(1)
    F = pd.DataFrame({"sma50_gap": [-0.1], "sma200_gap": [-0.1], "macd_hist": [-1.0], "rsi_14": [50.0]}, index=idx)
    cfg = {"weights": {"ml": 0.6, "technical": 0.4}, "ml_auc_floor": 0.5, "ml_auc_full": 0.56}
    score = S.strategy_score(F, pd.Series([0.95], idx), pd.Series([0.50], idx), cfg)
    assert score.iloc[0] == pytest.approx(S.technical_score(F).iloc[0])  # ML weight is zero at AUC 0.5


def test_sizing():
    assert S.sleeve_weight(6, 0.2) == pytest.approx(1 / 6)
    assert S.sleeve_weight(3, 0.2) == 0.2
    assert S.target_exposure(0.30, 0.15) == 0.5
    assert S.target_exposure(0.05, 0.15) == 1.0
    assert S.target_exposure(float("nan"), 0.15) == 0.0


# ---- simulator ------------------------------------------------------------
def test_fills_at_next_open_not_signal_close():
    p = make_prices(closes=[100, 100, 110, 120], opens=[100, 105, 108, 115])
    r = sim(p, ["BUY", "HOLD", "HOLD", "HOLD"])
    t = r.trades.iloc[0]
    assert t["entry_date"] == p.index[1] and t["entry_price"] == 105  # decided day 0, filled at day 1 open
    assert r.daily["shares"].iloc[0] == 0


def test_costs_are_deducted_exactly():
    p = make_prices(closes=[100, 100, 100, 100], opens=[100, 100, 100, 100])
    r = sim(p, ["BUY", "SELL", "HOLD", "HOLD"], vol=0.15, cost_bps=10, target_vol=0.15)
    # full exposure: buy notional n with n*(1+c)=1, sell n at the same price paying c again
    c = 0.001
    n = 1 / (1 + c)
    assert r.daily["value"].iloc[-1] == pytest.approx(1 - n * c - n * c)
    assert r.trades.iloc[0]["cost"] == pytest.approx(2 * n * c)


def test_uninvested_cash_earns_the_cash_rate():
    p = make_prices([100] * 253)
    r = sim(p, ["HOLD"] * 253, cash_rate=0.0252)
    assert r.daily["value"].iloc[-1] == pytest.approx((1 + 0.0252 / 252) ** 252)


def test_volatility_targeting_sets_exposure():
    p = make_prices([100] * 5)
    r = sim(p, ["BUY"] + ["HOLD"] * 4, vol=0.30, target_vol=0.15)
    assert r.daily["exposure"].iloc[2] == pytest.approx(0.5, rel=1e-3)


def test_stop_exits_next_open_and_waits_for_fresh_signal():
    closes = [100, 100, 100, 90, 95, 100, 100, 100]
    p = make_prices(closes)
    dec = ["BUY", "BUY", "BUY", "BUY", "BUY", "HOLD", "BUY", "HOLD"]
    r = sim(p, dec, vol=0.15, atr=2.0, stop_atr_mult=2.0)
    first = r.trades.iloc[0]
    assert first["exit_reason"] == "stop"  # stop = 100 - 4 = 96; close 90 breaches it
    assert first["exit_date"] == p.index[4]  # exits at the next open
    assert r.daily["shares"].iloc[5] == 0  # still BUY at day 4 close, but stopped out: no re-entry
    assert r.trades.iloc[1]["entry_date"] == p.index[7]  # HOLD on day 5 resets; BUY on day 6 fills day 7


def test_sell_signal_exits():
    p = make_prices([100, 101, 102, 103, 104])
    r = sim(p, ["BUY", "HOLD", "SELL", "HOLD", "HOLD"])
    assert r.trades.iloc[0]["exit_reason"] == "signal" and r.trades.iloc[0]["exit_date"] == p.index[3]


def test_no_trades_when_flat():
    p = make_prices([100, 99, 101, 98])
    r = sim(p, ["HOLD"] * 4)
    assert r.trades.empty and (r.daily["value"] == 1.0).all()
