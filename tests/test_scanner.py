"""Platform phase 3: scanner stages, evidence weights, ranking and the swing earnings check."""

import numpy as np
import pandas as pd
import pytest

from aurum import factorlab as FL
from aurum import scanner as SC
from aurum.events import Event


def _universe():
    rows = {
        "AAA": ("stock", 50.0, 50e6, 90),
        "BBB": ("stock", 8.0, 50e6, 90),  # too cheap for long-term/swing
        "CCC": ("stock", 40.0, 2e6, 90),  # too little trading
        "SPY": ("etf", 700.0, 3e9, 90),
        "GLD": ("commodity etf", 350.0, 1e9, 90),
        "DDD": ("stock", 60.0, 80e6, 90),
    }
    df = pd.DataFrame(rows, index=["kind", "price", "dollar_volume_20d", "bars"]).T
    df["eligible"] = True
    df.loc["DDD", "eligible"] = False
    for c in ("price", "dollar_volume_20d", "bars"):
        df[c] = df[c].astype(float)
    return df


def test_fast_filter_records_each_stage():
    keep, notes = SC.fast_filter(_universe(), SC.SCANNERS["long-term"])
    assert list(keep) == ["AAA", "SPY", "GLD"]
    assert [n for _, n, _ in notes] == [5, 4, 3]  # kind, price, volume
    keep_x, _ = SC.fast_filter(_universe(), SC.SCANNERS["cross-asset"])
    assert sorted(keep_x) == ["GLD", "SPY"]
    atr = pd.Series({"AAA": 0.02, "SPY": 0.008, "GLD": 0.015})
    keep_s, notes_s = SC.fast_filter(_universe(), SC.SCANNERS["swing"], atr)
    assert list(keep_s) == ["AAA"] and notes_s[-1][0] == "volatility band"


def test_weights_only_from_passed_signals_and_shared_between_twins():
    stats = {
        "momentum": {"verdict": "PASS", "t": 3.0},
        "near_52w_high": {"verdict": "PASS", "t": 3.0},
        "quality": {"verdict": "PASS", "t": 2.0},
        "value": {"verdict": "FAIL", "t": 1.0},
    }
    corr = pd.DataFrame(
        np.eye(3), index=["momentum", "near_52w_high", "quality"], columns=["momentum", "near_52w_high", "quality"]
    )
    corr.loc["momentum", "near_52w_high"] = corr.loc["near_52w_high", "momentum"] = 0.8
    w = SC.weights_from_tests(stats, SC.SCANNERS["long-term"]["signals"], corr)
    assert set(w) == {"momentum", "near_52w_high", "quality"} and "value" not in w
    assert w["momentum"] == pytest.approx(1.5 / 5.0) and w["quality"] == pytest.approx(2.0 / 5.0)
    assert SC.weights_from_tests({"value": {"verdict": "FAIL", "t": 1}}, ("value",)) == {}


def _panels(n=40, days=400, seed=2):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2025-01-01", periods=days)
    cols = [f"S{i:02d}" for i in range(n)]
    drift = np.linspace(-0.001, 0.001, n)  # S39 rises fastest
    c = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.01, (days, n)) + drift, axis=0)), index=idx, columns=cols)
    return FL.Panels(c.shift(1).fillna(c), c * 1.01, c * 0.99, c, pd.DataFrame(1e6, index=idx, columns=cols))


def test_rank_untested_vs_evidence_and_history_check():
    p = _panels()
    cands = pd.Index(p.close.columns)
    t, used, status = SC.rank("cross-asset", p, cands, None)
    assert status == "untested" and set(used) == {"trend", "momentum", "low_volatility"}
    assert t["score"].between(0, 100).all()
    order = pd.Series(range(len(t)), index=t.index)
    drift_rank = pd.Series({c: int(c[1:]) for c in t.index})
    assert order.corr(drift_rank, method="spearman") < -0.3  # faster risers rank higher on average
    t2, used2, status2 = SC.rank("cross-asset", p, cands, {"momentum": 1.0, "trend": 0.0})
    assert status2 == "evidence" and used2 == {"momentum": 1.0}
    assert t2["score"].corr(t2["rank_momentum"] * 100) > 0.999
    short = SC.rank("cross-asset", p, cands, None, min_history=1000)[0]
    assert short.empty  # not enough history: never ranked


def test_swing_risk_check_drops_earnings_inside_window():
    t = pd.DataFrame({"score": [90.0, 80.0]}, index=["AAA", "BBB"])
    ev = {"AAA": [Event("2026-11-05", "earnings", "AAA", "AAA earnings", False, "test")], "BBB": []}
    kept, dropped = SC.risk_check(t, "swing", ev)
    assert list(kept.index) == ["BBB"] and dropped == 1
    assert SC.risk_check(t, "long-term", ev)[1] == 0


def test_swing_missing_setup_counts_as_no_setup_and_cash_like_funds_are_left_out():
    p = _panels(n=20)
    c = p.close.copy()
    c["CASH"] = 100 * np.exp(np.cumsum(np.full(len(c), 0.0001)))  # a T-bill-like fund: barely moves
    p2 = FL.Panels(c.shift(1).fillna(c), c * 1.001, c * 0.999, c, pd.DataFrame(1e6, index=c.index, columns=c.columns))
    lt, _, _ = SC.rank("long-term", p2, pd.Index(c.columns), None, min_history=252)
    assert "CASH" not in lt.index
    sw, used, _ = SC.rank("swing", p, pd.Index(p.close.columns), None, min_history=200)
    one_signal = sw[sw["signals_known"] == 1]
    assert len(one_signal) and (one_signal["score"] <= 100 / len(used) + 1e-6).all()
