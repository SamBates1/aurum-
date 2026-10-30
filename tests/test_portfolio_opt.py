"""Platform phase 5: portfolio view, candidate checks and the four allocation methods."""

import numpy as np
import pandas as pd
import pytest

from aurum import portfolio_opt as PO


def _returns(seed=5, n=300):
    rng = np.random.default_rng(seed)
    base = rng.normal(0, 0.01, n)
    r = pd.DataFrame(
        {
            "SPY": base + rng.normal(0, 0.002, n),
            "VOO": base + rng.normal(0, 0.0005, n),  # the same index: a duplicate of SPY
            "GLD": rng.normal(0, 0.009, n),
            "TLT": -0.3 * base + rng.normal(0, 0.008, n),
            "AAA": 1.5 * base + rng.normal(0, 0.02, n),
        },
        index=pd.bdate_range(end="2026-10-29", periods=n),
    )
    return r


def test_view_measures_weights_risk_and_limits():
    hs = [
        PO.Holding("SPY", 100, 600, asset_class="etf"),
        PO.Holding("AAA", 300, 100, sector="Technology"),
        PO.Holding("UKFUND", 1000, 10, currency="GBP", asset_class="etf"),
    ]
    pv = PO.view(hs, {"SPY": 700.0, "AAA": 100.0}, cash=10_000, returns=_returns(), fx_usd_per_gbp=1.3)
    assert pv.value == pytest.approx(70_000 + 30_000 + 13_000 + 10_000)
    assert pv.weights["AAA"] == pytest.approx(30_000 / 123_000)
    assert any("AAA" in n and "limit 10%" in n for n in pv.notes)  # one stock over 10%
    assert any("UKFUND" in n for n in pv.notes)  # no price history: said, not hidden
    assert pv.risk_contribution.sum() == pytest.approx(1.0) and pv.volatility > 0
    assert pv.by_asset_class["cash"] == pytest.approx(10_000 / 123_000)


def test_candidate_check_finds_duplicates_and_diversifiers():
    r = _returns()
    pv = PO.view([PO.Holding("SPY", 100, 700, asset_class="etf")], {"SPY": 700.0}, 30_000, r)
    dup = PO.check_candidate(pv, "VOO", r, 0.2, "etf")
    assert dup["verdict"] == "duplicate" and "SPY" in dup["problems"][0]
    gold = PO.check_candidate(pv, "GLD", r, 0.2, "commodity etf")
    assert (
        gold["verdict"] == "ok" and gold["corr_with_portfolio"] < 0.3 and gold["vol_after"] < gold["vol_before"] + 0.05
    )
    big = PO.check_candidate(pv, "GLD", r, 0.5, "commodity etf")
    assert big["verdict"] == "blocked" and any("cash" in p for p in big["problems"])


def test_methods_respect_caps_and_differ():
    r = _returns()
    kinds = {"SPY": "etf", "GLD": "etf", "TLT": "etf", "AAA": "stock"}
    t = PO.compare(r, ["SPY", "GLD", "TLT", "AAA"], kinds, budget=1.0, scores={"AAA": 90})
    w = t.loc[["SPY", "GLD", "TLT", "AAA"]]
    assert (w.loc["AAA"] <= 0.10 + 1e-6).all() and (w.loc[["SPY", "GLD", "TLT"]] <= 0.25 + 1e-6).all().all()
    assert (t.loc["invested"] <= 1.0 + 1e-6).all() and (t.loc["cash"] >= -1e-6).all()  # caps leave cash
    rp = w["risk parity"].to_numpy()
    cov = PO.shrunk_cov(r[["SPY", "GLD", "TLT", "AAA"]]).to_numpy()
    rc = rp * (cov @ rp)
    assert rc.std() / rc.mean() < 0.35 or (rp >= np.array([0.25, 0.25, 0.25, 0.10]) - 1e-4).any()
    assert t.loc["diversification ratio", "maximum diversification"] >= t.loc["diversification ratio"].max() - 1e-3
