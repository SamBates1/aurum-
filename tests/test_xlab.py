"""Cross-asset lab (EXP-037 onwards): look-ahead, statistics and accounting checks on hand-built data."""

import numpy as np
import pandas as pd
import pytest
from conftest import make_prices

from aurum import xlab as X


def test_garch_forecast_has_no_lookahead():
    rng = np.random.default_rng(1)
    idx = pd.bdate_range("2010-01-01", periods=1100)
    r = pd.Series(rng.standard_t(5, len(idx)) * 0.01, index=idx)
    full = X.garch11(r, min_obs=600, refit=100)
    cut = idx[900]
    part = X.garch11(r[:cut], min_obs=600, refit=100)
    common = part.dropna().index
    assert len(common) > 250
    np.testing.assert_allclose(full.loc[common], part.loc[common], rtol=1e-8)


def test_garch_tracks_a_volatility_regime_change():
    rng = np.random.default_rng(2)
    idx = pd.bdate_range("2010-01-01", periods=1400)
    sd = np.where(np.arange(1400) < 1000, 0.005, 0.02)
    r = pd.Series(rng.normal(0, sd), index=idx)
    g = X.garch11(r, min_obs=756, refit=63)
    assert g.iloc[1300:].mean() > 2 * g.iloc[800:1000].mean()


def test_candle_patterns_on_hand_built_bars():
    o = [10, 10, 10, 10, 10, 10, 9.0, 8.9]
    c = [10, 10, 10, 10, 10, 9.5, 8.95, 9.4]  # day 6 small body; day 7 bullish
    h = [10.1] * 6 + [9.05, 9.45]
    lo = [9.9] * 5 + [9.4, 8.0, 8.85]  # day 6: long lower shadow after a fall (hammer)
    p = pd.DataFrame(
        {"Open": o, "High": h, "Low": lo, "Close": c, "Volume": 1.0}, index=pd.bdate_range("2024-01-01", periods=8)
    )
    f = X.candle_patterns(p)
    assert f["hammer"].iloc[6] and not f["hammer"].iloc[5]
    assert f["bullish_engulfing"].iloc[7]  # bullish body engulfs the prior small bearish body
    assert not f["bearish_engulfing"].any()


def test_benjamini_hochberg_controls_false_discoveries():
    rng = np.random.default_rng(3)
    p = np.r_[rng.uniform(size=95), [1e-6, 2e-6, 1e-5, 1e-4, 2e-4]]
    found = X.benjamini_hochberg(p, 0.10)
    assert found[-5:].all() and found[:95].sum() <= 3
    assert not X.benjamini_hochberg(rng.uniform(size=200), 0.10).sum() > 3


def test_newey_west_matches_ols_coefficients_and_widens_errors():
    rng = np.random.default_rng(4)
    n = 2000
    x = np.cumsum(rng.normal(size=n))  # persistent regressor
    e = np.convolve(rng.normal(size=n + 20), np.ones(21) / 21, "valid")[:n]  # overlapping-return style noise
    y = 0.0 * x + e
    Xm = np.column_stack([np.ones(n), x])
    b, t_nw = X.newey_west_t(y, Xm, lags=21)
    b0, t_0 = X.newey_west_t(y, Xm, lags=0)
    np.testing.assert_allclose(b, np.linalg.lstsq(Xm, y, rcond=None)[0])
    assert abs(t_nw[1]) < abs(t_0[1])  # HAC errors are larger with autocorrelated residuals


def test_engle_granger_separates_cointegrated_from_random_walks():
    rng = np.random.default_rng(5)
    idx = pd.bdate_range("2015-01-01", periods=1500)
    x = np.cumsum(rng.normal(0, 0.01, 1500))
    s = np.zeros(1500)
    for i in range(1, 1500):  # stationary AR(1) spread
        s[i] = 0.9 * s[i - 1] + rng.normal(0, 0.005)
    a, b = pd.Series(np.exp(1 + x + s), idx), pd.Series(np.exp(x), idx)
    assert X.engle_granger(a, b)["cointegrated_5pct"]
    c = pd.Series(np.exp(np.cumsum(rng.normal(0, 0.01, 1500))), idx)
    assert not X.engle_granger(c, b)["cointegrated_5pct"]


def test_leverage_doubles_asset_returns_and_charges_financing():
    closes = 100 * np.exp(np.cumsum(np.r_[0, np.full(99, 0.001)]))
    p = {"A": make_prices(closes)}
    tgt = pd.DataFrame({"A": 1.0}, index=p["A"].index)
    one = X.run(p, tgt, 0.0, costs={"A": 0}).daily["ret"]
    two = X.run(p, tgt, 0.0, costs={"A": 0}, leverage=2.0).daily["ret"]
    fin = X.run(p, tgt, 0.0, costs={"A": 0}, leverage=2.0, financing_spread=0.0252).daily["ret"]
    np.testing.assert_allclose(two.iloc[5:], 2 * one.iloc[5:], rtol=1e-9)
    np.testing.assert_allclose((two - fin).iloc[5:], 0.0252 / 252, rtol=1e-6)  # pays on the borrowed 100%


def test_trend_signals_use_only_past_prices():
    rng = np.random.default_rng(6)
    c = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 600))), index=pd.bdate_range("2020-01-01", periods=600))
    for fn in (lambda s: X.sma_cross(s, 50, 200), lambda s: X.tsmom(s, 126), lambda s: X.donchian(s), X.rsi2_reversion):
        full = fn(c)
        cut = fn(c.iloc[:450])
        np.testing.assert_array_equal(full.iloc[:450].fillna(-1).to_numpy(), cut.fillna(-1).to_numpy())


def test_run_honours_the_configured_fill():
    """Regression: the first EXP-037 close-fill run ignored --fill for the ETF legs."""
    p = {"A": make_prices([100, 101, 102, 103, 104.0], opens=[100, 100.5, 105, 102, 103.0])}
    tgt = pd.DataFrame({"A": [1.0, np.nan, np.nan, np.nan, np.nan]}, index=p["A"].index)
    old = X.DEFAULT_FILL
    try:
        X.DEFAULT_FILL = "open"
        a = X.run(p, tgt, 0.0, costs={"A": 0}).daily["value"].iloc[-1]
        X.DEFAULT_FILL = "close"
        b = X.run(p, tgt, 0.0, costs={"A": 0}).daily["value"].iloc[-1]
    finally:
        X.DEFAULT_FILL = old
    assert a == pytest.approx(104 / 100.5) and b == pytest.approx(104 / 101)
