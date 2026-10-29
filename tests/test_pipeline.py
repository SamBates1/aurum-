"""End-to-end checks on synthetic data, including live/backtest consistency."""

from unittest import mock

import numpy as np
import pandas as pd
import pytest

from aurum import benchmarks, data, pipeline
from aurum import strategy as S
from aurum.features import atr


@pytest.fixture(scope="module")
def res():
    from aurum.config import load_config

    c = load_config()
    c["offline"] = True
    c["strategy"]["mode"] = "timing"  # these tests cover the BUY/SELL timing machinery (v0.2)
    return pipeline.research("GLD", cfg=c), c


def test_research_produces_out_of_sample_backtest(res):
    r, _ = res
    assert r.wf.probs.loc[: r.eval_start].iloc[:-1].isna().all()  # nothing before the first fold
    assert r.perf["days"] > 1000 and np.isfinite(r.perf["sharpe"])
    assert len(r.wf.folds) > 10


def test_live_decision_uses_exactly_the_backtest_rule(res):
    """With the same model probability, the live score must equal the backtested score."""
    r, cfg = res
    day = r.prices.index[-3]
    prices = r.prices.loc[:day]
    prob = float(r.wf.probs.loc[day])
    after_close = pd.Timestamp(day).tz_localize("America/New_York") + pd.Timedelta(hours=17)
    with mock.patch("aurum.model.predict_row", return_value=prob):
        d = pipeline.decide("GLD", r, cfg, prices=prices, now=after_close, context=False)
    assert d.as_of == str(day.date())
    assert d.score == pytest.approx(r.score.loc[day])
    assert d.decision == S.decision_for(r.score.loc[day], cfg["strategy"]["buy_above"], cfg["strategy"]["sell_below"])


def test_decide_rebuilds_features_from_fresh_prices(res):
    """Regression: run_bot.py used to refresh prices but keep the morning's features."""
    r, cfg = res
    old = r.prices.iloc[:-10]
    after = pd.Timestamp(old.index[-1]).tz_localize("America/New_York") + pd.Timedelta(hours=17)
    d_old = pipeline.decide("GLD", r, cfg, prices=old, now=after, context=False)
    assert d_old.as_of == str(old.index[-1].date())
    assert d_old.features.index[-1] == old.index[-1]


def test_stale_data_is_not_tradeable(res):
    r, cfg = res
    later = pd.Timestamp(r.prices.index[-1]).tz_localize("America/New_York") + pd.Timedelta(days=10)
    d = pipeline.decide("GLD", r, cfg, now=later, context=False)
    assert not d.tradeable and d.decision == S.HOLD


def test_missing_model_prediction_falls_back_to_technical(res):
    r, cfg = res
    with mock.patch("aurum.model.predict_row", return_value=float("nan")):
        d = pipeline.decide("GLD", r, cfg, context=False)
    assert d.components["ml"]["weight"] == 0
    assert d.score == pytest.approx(d.components["technical"]["score"])


def test_benchmarks_share_dates_and_costs(res):
    r, cfg = res
    sims = benchmarks.run_all(
        r.prices, r.X, r.score, r.wf.probs, None, atr(r.prices), r.rf, cfg["strategy"], 5.0, r.eval_start
    )
    idx = sims["strategy"].daily.index
    for name, s in sims.items():
        assert s.daily.index.equals(idx), name
    assert sims["buy_hold"].daily["invested"].iloc[1:].all()
    assert not sims["cash"].daily["invested"].any()


def test_research_refuses_short_history(cfg):
    cfg["data"]["min_history_days"] = 10**6
    with pytest.raises(data.DataError):
        pipeline.research("GLD", cfg=cfg)


def test_vol_hold_live_weight_matches_backtest_weight():
    """In the adopted mode, the live target weight equals the weight the backtest used that day."""
    from aurum import strategy as S2
    from aurum.config import load_config

    c = load_config()
    c["offline"] = True
    c["model"]["retrain_every_days"] = 252
    r = pipeline.research("NEM", cfg=c)
    day = r.prices.index[-3]
    after = pd.Timestamp(day).tz_localize("America/New_York") + pd.Timedelta(hours=17)
    d = pipeline.decide("NEM", r, c, prices=r.prices.loc[:day], now=after, context=False)
    expected = S2.vol_target_weight(r.sizing_vol, c["strategy"]["target_vol"]).loc[day]
    assert d.target_weight == pytest.approx(expected)


def test_gvz_sizing_scales_volatility_and_falls_back(monkeypatch):
    import copy as _copy

    from aurum.config import load_config

    c = load_config()
    c["offline"] = True
    gld = data.daily_prices("GLD", cfg=c)
    idx = gld.index
    fake_gvz = pd.DataFrame({"Close": 30.0}, index=idx)  # 30% implied vol, constant
    real = data.daily_prices

    def fake_prices(t, cfg=None, use_cache=True):
        return fake_gvz if t == "^GVZ" else real(t, cfg=c)

    online = _copy.deepcopy(c)
    online["offline"] = False
    monkeypatch.setattr(data, "daily_prices", fake_prices)
    vol21 = pd.Series(0.20, index=idx)
    sized, ratio = pipeline.sizing_volatility(vol21, idx, online)
    from aurum.volatility import realised_21d

    expected = (0.30 / realised_21d(gld["Close"])).clip(0.5, 2.0)
    pd.testing.assert_series_equal(ratio.dropna(), expected.dropna(), check_names=False)
    ok = ratio.notna()
    np.testing.assert_allclose(sized[ok], 0.20 * ratio[ok])
    assert (sized[~ok] == 0.20).all()  # before GVZ/GLD vol exist: plain 21-day volatility
    monkeypatch.setattr(data, "daily_prices", lambda *a, **k: (_ for _ in ()).throw(OSError("down")))
    sized2, ratio2 = pipeline.sizing_volatility(vol21, idx, online)
    assert ratio2 is None and (sized2 == vol21).all()  # visible fallback, never a crash
