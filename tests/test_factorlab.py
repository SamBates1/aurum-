"""EXP-051 factor lab: a planted signal passes, noise fails, no look-ahead, costs charged, swing cohorts."""

import numpy as np
import pandas as pd
import pytest

from aurum import factorlab as FL


def _panels(n_stocks=150, n_days=1500, seed=3, plant=0.0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2016-01-04", periods=n_days)
    cols = [f"S{i:03d}" for i in range(n_stocks)]
    skill = pd.Series(rng.normal(0, 1, n_stocks), index=cols)  # a fixed per-stock trait
    drift = plant * skill / 252
    r = rng.normal(0, 0.015, (n_days, n_stocks)) + drift.to_numpy()
    c = pd.DataFrame(100 * np.exp(np.cumsum(r, axis=0)), index=idx, columns=cols)
    o = c.shift(1).fillna(c)
    p = FL.Panels(o, c * 1.01, c * 0.99, c, pd.DataFrame(1e6, index=idx, columns=cols))
    roic = pd.DataFrame(np.tile(skill.to_numpy(), (n_days, 1)), index=idx, columns=cols)
    return p, roic


def test_planted_signal_passes_and_noise_fails():
    p, roic = _panels(plant=0.25)  # top stocks drift about 25% a year more per unit of the trait
    res = FL.backtest(p, roic, "monthly", cost_bps=10)
    s = FL.judge(res, "monthly", ("2018-12-31", "2019-01-01"), "2020-06-01")
    assert s["excess_per_year"] > 0.1 and s["t"] > 3 and s["rule_ok"]
    noise = pd.DataFrame(np.random.default_rng(9).normal(size=roic.shape), index=roic.index, columns=roic.columns)
    sn = FL.judge(FL.backtest(p, noise, "monthly", cost_bps=10), "monthly", ("2018-12-31", "2019-01-01"), "2020-06-01")
    v = FL.verdicts({"quality": s, "noise": sn})
    assert v["quality"]["verdict"] == "PASS" and v["noise"]["verdict"] == "FAIL"


def test_costs_are_charged_on_turnover():
    p, roic = _panels(plant=0.0)
    noise = pd.DataFrame(np.random.default_rng(1).normal(size=roic.shape), index=roic.index, columns=roic.columns)
    free = FL.backtest(p, noise, "monthly", cost_bps=0)
    paid = FL.backtest(p, noise, "monthly", cost_bps=50)
    assert (paid["strategy"] < free["strategy"]).all() and paid["turnover"].mean() > 1.0  # noise churns the list


def test_signals_use_only_past_data():
    p, _ = _panels(n_days=600)
    cut = 400
    short = FL.Panels(*(getattr(p, k).iloc[:cut] for k in ("open", "high", "low", "close", "volume")))
    for fam in (FL.long_term_signals, FL.swing_signals):
        full, part = fam(p), fam(short)
        for k in part:
            pd.testing.assert_frame_equal(full[k].iloc[:cut], part[k], check_freq=False)


def test_swing_holds_four_overlapping_cohorts():
    p, roic = _panels(n_days=400)
    res = FL.backtest(p, roic, "weekly", hold=4, cost_bps=15)
    assert len(res) > 60 and res["turnover"].iloc[10:].max() <= 0.5 + 1e-9  # a quarter replaced each week
    w = FL._weights([["A", "B"], ["B", "C"]], 4)
    assert w == pytest.approx({"A": 0.125, "B": 0.25, "C": 0.125})
