"""Research lab (EXP-020 onwards): whole-share fills, signal look-ahead checks, verdict rules."""

import numpy as np
import pandas as pd
from conftest import make_prices

from aurum import data
from aurum import strategy as S
from aurum.lab import LabCtx, build_lab_variants, chandelier_weights, fair_value_z, zscore
from run_lab import lab_verdict


def test_whole_shares_round_down_and_track_fractional():
    p = make_prices([100.0] * 10)
    tgt = pd.Series(0.5, index=p.index)
    # $1,000 sleeve, 50% target at $100 -> exactly 5 shares; $950 -> 4 shares (rounded down)
    r = S.simulate_weights(p, tgt, cost_bps=0, band=0.0, capital=1000)
    assert np.isclose(r.daily["shares"].iloc[-1] * 1000, 5)
    r2 = S.simulate_weights(p, pd.Series(0.475, index=p.index), cost_bps=0, band=0.0, capital=1000)
    assert np.isclose(r2.daily["shares"].iloc[-1] * 1000, 4)
    frac = S.simulate_weights(p, pd.Series(0.475, index=p.index), cost_bps=0, band=0.0)
    assert np.isclose(frac.daily["exposure"].iloc[-1], 0.475)
    # selling to zero sells every share
    tgt0 = pd.Series([0.5] * 5 + [0.0] * 5, index=p.index)
    r3 = S.simulate_weights(p, tgt0, cost_bps=0, band=0.0, capital=1000)
    assert r3.daily["shares"].iloc[-1] == 0


def test_fair_value_z_has_no_lookahead():
    rng = np.random.default_rng(3)
    idx = pd.bdate_range("2010-01-01", periods=1400)
    ry = pd.Series(np.cumsum(rng.normal(0, 0.03, len(idx))), index=idx)
    dx = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.004, len(idx)))), index=idx)
    gold = pd.Series(np.exp(7 - 0.1 * ry + np.cumsum(rng.normal(0, 0.01, len(idx)))), index=idx)
    full = fair_value_z(gold, ry, dx, window=500)
    cut = idx[1100]
    part = fair_value_z(gold[:cut], ry[:cut], dx[:cut], window=500)
    common = part.dropna().index
    assert len(common) > 500
    assert np.allclose(full.loc[common], part.loc[common])


def test_chandelier_goes_to_cash_then_reenters():
    closes = [100.0] * 30 + [80.0] * 30
    p = make_prices(closes)
    p["High"], p["Low"] = p["Close"] * 1.01, p["Close"] * 0.99
    ctx = LabCtx("GLD", p, pd.Series(0.0, index=p.index), {"strategy": {"target_vol": 0.15}}, {})
    w = chandelier_weights(ctx, pd.Series(0.8, index=p.index), mult=3.0, cooldown=10)
    drop = p.index[30]
    assert w.loc[drop] == 0.0  # 20-point fall >> 3 ATR
    assert (w.iloc[31:41] == 0).all() and w.iloc[45] == 0.8  # cooldown, then back in


def test_zscore_uses_past_only():
    s = pd.Series(np.arange(100.0))
    z = zscore(s, 20)
    s2 = s.copy()
    s2.iloc[60:] = 0
    assert np.allclose(z.iloc[:60].dropna(), zscore(s2, 20).iloc[:60].dropna())


def test_lab_verdict_requires_both_confirmations():
    good = {"d_sharpe": 0.15, "share_better": 0.9, "dd_rel": 0.0}
    x2 = {"d_sharpe": 0.05}
    assert lab_verdict(good, x2, good, good, 0.6).startswith("KEEP")
    bad = {"d_sharpe": -0.1, "share_better": 0.1, "dd_rel": 0.0}
    assert "pre-2013" in lab_verdict(good, x2, good, bad, 0.6)
    assert "holdout" in lab_verdict(good, x2, bad, good, 0.6)
    assert lab_verdict(good, x2, good, good, 0.3) == "INCONCLUSIVE"


def test_every_lab_variant_runs_offline(cfg):
    p = data.daily_prices_from("GLD", "2010-01-01", cfg).iloc[21:]
    shared = {
        "gld_close": p["Close"],
        "gdx_close": data.daily_prices_from("GDX", "2010-01-01", cfg)["Close"],
        "gvz": None,
        "gold": data.synthetic.macro(["gold"])["gold"],
        "dxy": data.synthetic.macro(["dxy"])["dxy"],
        "real_yield": data.synthetic.macro(["real_yield_10y"])["real_yield_10y"],
        "epu": data.synthetic.macro(["epu"])["epu"].abs() * 100 + 100,
        "gpr": data.gpr_daily(cfg),
        "cot_gold": data.cot_managed_money("gold", cfg),
        "cot_silver": data.cot_managed_money("silver", cfg),
    }
    ctx = LabCtx("GLD", p, data.cash_rate(p.index, cfg), cfg, shared)
    for v in build_lab_variants(["fv_rolling", "cot_flow"]):
        w = v.weight(ctx)
        assert w.index.equals(p.index), v.name
        assert ((w >= 0) & (w <= 1)).all(), v.name


def test_weekly_rebalance_days():
    idx = pd.bdate_range("2026-10-05", "2026-10-21")  # Mon 5 Oct ... Wed 21 Oct
    m = S.rebalance_days(idx.delete(idx.get_loc(pd.Timestamp("2026-10-16"))), "weekly")  # Fri 16 Oct a holiday
    assert m[pd.Timestamp("2026-10-09")] and m[pd.Timestamp("2026-10-15")]  # Friday; Thursday before the holiday
    assert not m[pd.Timestamp("2026-10-21")]  # last row is a Wednesday: the week is not over
    assert m.sum() == 2
    assert S.rebalance_days(idx, "daily").all()
