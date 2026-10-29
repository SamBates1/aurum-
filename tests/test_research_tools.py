"""Overfitting statistics, triple-barrier labels, the model zoo, experiment variants and
two checks borrowed from Freqtrade: recursive (warm-up) analysis and trade-level look-ahead."""

import copy

import numpy as np
import pandas as pd
import pytest
from conftest import make_prices

from aurum import data, model, pipeline, stats
from aurum import strategy as S
from aurum.experiments import Context, build_variants
from aurum.features import atr, build_dataset, triple_barrier_labels
from run_experiments import verdict


# ---- overfitting statistics -------------------------------------------------
def test_psr_and_dsr_behave():
    rng = np.random.default_rng(0)
    noise = pd.DataFrame(rng.normal(0, 0.01, (2500, 20)))
    edge = noise[0] + 0.001
    assert stats.probabilistic_sharpe(edge) > 0.99
    srs = [noise[c].mean() / noise[c].std() for c in noise]
    best = noise[int(np.argmax(srs))]
    assert stats.deflated_sharpe(best, srs) < stats.probabilistic_sharpe(best)  # deflation penalises selection


def test_pbo_detects_luck_and_real_edges():
    rng = np.random.default_rng(1)
    noise = pd.DataFrame(rng.normal(0, 0.01, (2000, 10)))
    assert 0.25 < stats.probability_of_backtest_overfitting(noise, n_blocks=10)["pbo"] < 0.85
    real = noise.copy()
    real[0] += 0.003
    assert stats.probability_of_backtest_overfitting(real, n_blocks=10)["pbo"] < 0.05


def test_expected_max_sharpe_grows_with_trials():
    assert stats.expected_max_sharpe(100, 0.01) > stats.expected_max_sharpe(10, 0.01) > 0


# ---- triple-barrier labels --------------------------------------------------
def test_triple_barrier_labels():
    closes = [100, 100, 101, 104, 99, 98, 97, 96, 95, 94]
    p = make_prices(closes)
    a = pd.Series(1.0, index=p.index)
    y = triple_barrier_labels(p, a, pt_mult=2.0, sl_mult=2.0, horizon=3)
    assert y.iloc[0] == 1.0  # 104 >= 102 before any low <= 98
    assert y.iloc[3] == 0.0  # from 104 (barriers 102/106): the next day's low of 99 hits 102 first
    assert y.iloc[-3:].isna().all()
    both = make_prices([100, 100, 100])
    both.loc[both.index[1], ["High", "Low"]] = [105.0, 95.0]
    assert triple_barrier_labels(both, pd.Series(1.0, both.index), 2, 2, 1).iloc[0] == 0.0  # pessimistic


def test_triple_barrier_labels_use_only_their_window(gld):
    a = atr(gld)
    full = triple_barrier_labels(gld, a, horizon=20)
    cut = triple_barrier_labels(gld.iloc[:1500], a.iloc[:1500], horizon=20)
    pd.testing.assert_series_equal(full.iloc[:1480], cut.iloc[:1480])


# ---- model zoo ----------------------------------------------------------------
@pytest.mark.parametrize("name", list(model.MODEL_FACTORIES))
def test_model_factories_fit_and_predict(gld, cfg, name):
    X, y, _, _ = build_dataset(gld, data.macro_daily(cfg), horizon=5)
    Xv, yv = model.usable(X, y)
    m = model.MODEL_FACTORIES[name](0).fit(Xv.iloc[:1200], yv.iloc[:1200])
    p = m.predict_proba(Xv.iloc[1200:1300])[:, 1]
    assert np.all((p > 0) & (p < 1))
    assert np.isfinite(model.predict_row(m, Xv.iloc[:1300]))


# ---- experiments ----------------------------------------------------------------
@pytest.fixture(scope="module")
def quick_ctx():
    from aurum.config import load_config

    c = load_config()
    c["offline"] = True
    c["model"]["retrain_every_days"] = 252
    res = pipeline.research("NEM", cfg=c)
    gdx = data.daily_prices("GDX", cfg=c)["Close"]
    return Context("NEM", res, c, gdx_close=gdx, is_equity=True)


def test_variant_names_unique_and_cheap_variants_run(quick_ctx):
    variants = build_variants()
    names = [v.name for v in variants]
    assert len(names) == len(set(names)) and names[0] == "baseline"
    base = variants[0].run(quick_ctx, 5.0)
    cheap = {
        "stop_on_close",
        "tsmom_1_3_12",
        "donchian_50_20",
        "gate_vix",
        "dd_breaker",
        "miner_vs_gdx_reversion",
        "base_model_tb_exits",
        "default_long",
        "default_long_full_chandelier",
        "buy_hold",
    }
    for v in variants:
        if v.name in cheap:
            r = v.run(quick_ctx, 5.0)
            assert r.daily.index.equals(base.daily.index), v.name
            assert np.isfinite(r.daily["value"]).all(), v.name


def test_experiment_variants_reproduce_the_traded_strategy(quick_ctx):
    """vol_hold (EXP-014) is the traded rule when sizing uses plain 21-day volatility (offline: no GVZ)."""
    v = {x.name: x for x in build_variants()}
    assert quick_ctx.res.vol_ratio is None  # offline: GVZ unavailable, so sizing falls back to 21-day vol
    rule = quick_ctx.scfg.get("rebalance", "daily")
    if rule == "daily":
        pd.testing.assert_frame_equal(v["vol_hold"].run(quick_ctx, 8.0).daily, quick_ctx.res.sim.daily)
    # the traded rule (D-022: weekly orders) is vol_hold's weights on rebalance days only
    w = quick_ctx.base_weight().where(S.rebalance_days(quick_ctx.prices.index, rule))
    pd.testing.assert_frame_equal(quick_ctx.simw(w, cost_bps=8.0).daily, quick_ctx.res.sim.daily)


def test_verdict_rules():
    good = {"d_sharpe": 0.2, "share_better": 0.9, "dd_rel": 0.0}
    assert verdict(good, {"d_sharpe": 0.1}, {"d_sharpe": 0.05, "dd_rel": 0}, 0.6) == "KEEP (held on holdout)"
    assert verdict(good, {"d_sharpe": 0.1}, {"d_sharpe": -0.05, "dd_rel": 0}, 0.6) == "REJECT (failed on holdout)"
    assert verdict(good, {"d_sharpe": 0.1}, {"d_sharpe": 0.05, "dd_rel": 0}, 0.3) == "INCONCLUSIVE"  # luck?
    assert verdict({"d_sharpe": -0.1, "share_better": 0.2, "dd_rel": 0.0}, {"d_sharpe": -0.1}, {}, 0.6) == "REJECT"


# ---- checks borrowed from Freqtrade -------------------------------------------------
def test_recursive_analysis_features_independent_of_warmup_length(gld):
    """Freqtrade's recursive-analysis: indicators must not depend on how much history
    preceded them (exponential averages do, until they have warmed up)."""
    from aurum.features import technical_features

    long = technical_features(gld).iloc[-1]
    short = technical_features(gld.iloc[-600:]).iloc[-1]
    np.testing.assert_allclose(long.to_numpy(float), short.to_numpy(float), rtol=1e-6, atol=1e-9)


def test_trade_level_lookahead_decisions_unchanged_by_future_data(cfg):
    """Freqtrade's lookahead-analysis, applied to the whole strategy: decisions made up to a
    date must be identical whether or not later data exists."""
    c = copy.deepcopy(cfg)
    c["model"]["retrain_every_days"] = 252
    full = pipeline.research("GLD", cfg=c)
    cut_date = full.wf.folds["test_start"].iloc[4]
    c2 = copy.deepcopy(c)
    prices = full.prices.loc[: cut_date - pd.Timedelta(days=1)]
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(data, "daily_prices", lambda t, cfg=None, use_cache=True: prices)
        part = pipeline.research("GLD", macro=full.macro, cfg=c2)
    # decisions before the last fold of the truncated run can only use data both runs share
    end = full.wf.folds["test_start"].iloc[3]
    d_full = S.decisions(full.score, 0.2, -0.2).loc[full.eval_start : end].iloc[:-1]
    d_part = S.decisions(part.score, 0.2, -0.2).reindex(d_full.index)
    assert len(d_full) > 200 and (d_full == d_part).all()


def test_volatility_forecasts_are_point_in_time(gld):
    from aurum import volatility as V

    full = V.har_parkinson(gld)
    cut = V.har_parkinson(gld.iloc[:2000])
    pd.testing.assert_series_equal(full.iloc[:2000], cut, check_names=False)
    pd.testing.assert_series_equal(V.ewma(gld.Close).iloc[:1500], V.ewma(gld.Close.iloc[:1500]))
    assert full.dropna().between(0.01, 3).all()
