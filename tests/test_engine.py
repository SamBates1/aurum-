"""Strategy definitions, the designer engine, indicators and charts (master build prompt, phases 1-2)."""

import copy

import numpy as np
import pandas as pd
import pytest
from conftest import make_prices

from aurum import designer as D
from aurum import designer_charts as DC
from aurum import engine as E
from aurum import spec as SP
from aurum import strategy as S
from aurum import xlab as X
from aurum.indicators import INDICATORS, compute


@pytest.fixture(scope="module")
def market():
    from aurum import data
    from aurum.config import load_config

    c = load_config()
    c["offline"] = True
    prices = {t: data.daily_prices_from(t, "2006-06-01", c) for t in ("SPY", "GLD")}
    idx = X.common_index(prices)
    return prices, data.cash_rate(idx, c), idx


@pytest.fixture(scope="module")
def lib():
    return SP.library()


def test_templates_load_and_hash_ignores_names(lib):
    a = lib["spy-gld-70-30-monthly"]
    assert a["base_weights"] == {"SPY": 0.7, "GLD": 0.3} and a["schedule"]["rebalance"] == "monthly"
    b = copy.deepcopy(a)
    b["name"], b["description"] = "renamed", "different words"
    assert SP.spec_hash(a) == SP.spec_hash(b)  # cosmetic edits keep the approval
    b["schedule"]["band"] = 0.01
    assert SP.spec_hash(a) != SP.spec_hash(b)  # any behaviour change gives a new fingerprint


def test_validation_reports_every_problem():
    bad = {
        "id": "x y",
        "name": "",
        "universe": ["SPY"],
        "base_weights": {"SPY": 0.8, "GLD": 0.4},
        "schedule": {"rebalance": "hourly"},
        "signals": [
            {
                "id": "r",
                "conditions": [{"left": {"ind": "nope", "asset": "SPY"}, "op": "~", "right": 1}],
                "when_true": 2,
            }
        ],
    }
    with pytest.raises(SP.SpecError) as e:
        SP.validate(bad)
    msg = str(e.value)
    for part in (
        "id must be",
        "name is required",
        "GLD, which is not in the universe",
        "more than 100%",
        "rebalance must be",
        "unknown indicator",
        "unknown comparison",
        "when_true must be",
    ):
        assert part in msg


@pytest.mark.parametrize(
    "sid,band",
    [("spy-gld-70-30-monthly", 0.0), ("spy-gld-70-30-risk-cap", 0.05), ("example-70-30-spy-trend-filter", 0.05)],
)
def test_engine_reproduces_the_exp045_code_path_exactly(market, lib, sid, band):
    prices, rf, idx = market
    p2 = {t: prices[t].reindex(idx) for t in ("SPY", "GLD")}
    base = pd.DataFrame({"SPY": 0.7, "GLD": 0.3}, index=idx)
    if sid == "spy-gld-70-30-monthly":
        first = idx.to_series().groupby([idx.year, idx.month]).transform("min") == idx.to_series()
        tgt = base.where(first, np.nan)
    elif sid == "spy-gld-70-30-risk-cap":
        tgt = base * pd.DataFrame(
            {t: S.vol_target_weight(X.realised_21d(p2[t]["Close"]), 0.20) for t in ("SPY", "GLD")}
        )
    else:
        tgt = base.assign(SPY=0.7 * X.above_sma(p2["SPY"]["Close"], 200).fillna(1.0))
    a = E.run_spec(lib[sid], p2, rf, capital=1.0, index=idx).daily["value"].to_numpy()
    b = X.run(p2, tgt, rf, band=band, fill="open").daily["value"].to_numpy()
    np.testing.assert_allclose(a, b, rtol=0, atol=1e-12)


@pytest.mark.parametrize("key", list(INDICATORS))
def test_every_indicator_uses_only_past_data(market, key):
    p = market[0]["GLD"]
    full = compute(key, p, INDICATORS[key].defaults())
    cut = p.index[3000]
    part = compute(key, p.loc[:cut], INDICATORS[key].defaults())
    np.testing.assert_allclose(full.loc[:cut].to_numpy(), part.to_numpy(), rtol=1e-9, equal_nan=True)


def test_conditions_crosses_and_unknowns():
    idx = pd.bdate_range("2024-01-01", periods=6)
    left = pd.Series([1, 2, 3, 2, 1, np.nan], index=idx, dtype=float)
    right = pd.Series(2.5, index=idx)
    up = E.evaluate_condition(left, "crosses_above", right)
    dn = E.evaluate_condition(left, "crosses_below", right)
    assert list(up.iloc[1:5]) == [0, 1, 0, 0] and np.isnan(up.iloc[0]) and np.isnan(up.iloc[5])
    assert list(dn.iloc[1:5]) == [0, 0, 1, 0]
    a = pd.Series([1, 0, np.nan, 1], dtype=float)
    b = pd.Series([1, 1, 1, np.nan], dtype=float)
    assert list(E.combine_states([a, b], "all", 1).fillna(-1)) == [1, 0, -1, -1]
    assert list(E.combine_states([a, b], "any", 1).fillna(-1)) == [1, 1, 1, 1]  # one true is enough
    assert list(E.combine_states([a, b, b], "k_of_n", 2).fillna(-1)) == [1, 1, 1, -1]


def test_schedules():
    idx = pd.bdate_range("2024-01-01", "2024-12-31")
    m = E.schedule_days(idx, "monthly")
    assert m.sum() == 12 and m.iloc[0] and m[pd.Timestamp("2024-02-01")]
    assert E.schedule_days(idx, "quarterly").sum() == 4
    assert E.schedule_days(idx, "yearly").sum() == 1
    assert E.schedule_days(idx, "once").sum() == 1
    assert E.schedule_days(idx, "weekly").sum() == 52


def test_trailing_stop_exits_then_reenters_after_cooldown():
    c = pd.Series([100, 110, 120, 105, 100, 101, 102, 103, 90.0])
    m = E.trailing_stop_mult(c, 0.10, 2)
    # 105 is 12.5% below the 120 peak -> out that close and for 2 more days, then back in with a fresh peak
    assert list(m) == [1, 1, 1, 0, 0, 0, 1, 1, 0]


def test_signal_rule_moves_money_to_cash_and_explains_itself(market, lib):
    prices, rf, idx = market
    run = E.run_spec(lib["example-70-30-spy-trend-filter"], prices, rf)
    comp = run.compiled
    off = comp.signal_state["spy_trend"] == 0
    assert off.any() and (comp.raw_target.loc[off, "SPY"] == 0).all()
    assert np.allclose(comp.raw_target.loc[off, "GLD"], 0.3)
    t = run.trades.iloc[5]
    assert t["decided"] < t["date"]  # decided at a close, filled at the next open
    assert comp.index.get_loc(t["date"]) == comp.index.get_loc(t["decided"]) + 1
    assert 0 < t["pct_of_account"] < 1 and "SPY above its 200-day average" in run.trades["reason"].str.cat()
    ex = E.explain_day(run, t["decided"])
    assert ex["orders_next_session"] and ex["signals"][0]["conditions"][0]["rule"] == "SPY Close > SPY SMA 200"
    assert ex["assets"]["SPY"]["target_weight"] == pytest.approx(comp.raw_target.at[t["decided"], "SPY"])


def test_targets_never_borrow_and_inverse_vol_keeps_total(market):
    prices, rf, idx = market
    s = {
        "id": "iv",
        "name": "iv",
        "universe": ["SPY", "GLD"],
        "base_weights": {"SPY": 0.5, "GLD": 0.5},
        "schedule": {"rebalance": "monthly"},
        "sizing": {"method": "inverse_vol"},
    }
    comp = E.compile_targets(s, prices)
    tot = comp.raw_target.sum(axis=1).iloc[30:]
    assert np.allclose(tot, 1.0) and (comp.raw_target.iloc[30:] > 0).all().all()


def test_summary_and_amounts_in_dollars():
    p = {"A": make_prices([100, 100, 110, 121.0], opens=[100, 100, 110, 121.0])}
    s = {
        "id": "a",
        "name": "a",
        "universe": ["A"],
        "base_weights": {"A": 1.0},
        "schedule": {"rebalance": "once"},
        "execution": {"costs_bps": {"A": 0}},
    }
    run = E.run_spec(s, p, 0.0, capital=1000)
    assert run.trades.iloc[0]["notional"] == pytest.approx(1000)
    sm = E.summary(run)
    assert sm["final_value"] == pytest.approx(1210) and sm["orders"] == 1


def test_describe_in_plain_english(lib):
    lines = " ".join(D.describe(lib["spy-gld-70-30-risk-cap"]))
    assert "70% SPY" in lines and "min(1, 20% /" in lines and "5% of the account" in lines and "no borrowing" in lines


def test_sweep_scores_development_only_and_counts_tries(market, lib, tmp_path):
    from aurum.registry import Registry

    prices, rf, _ = market
    reg = Registry(tmp_path / "r.sqlite")
    sw = D.sweepable(lib["spy-gld-70-30-risk-cap"])
    path = sw["Target volatility"][0]
    table, rets = D.sweep(lib["spy-gld-70-30-risk-cap"], path, [0.15, 0.2, 0.25], prices, rf, registry=reg)
    assert len(table) == 3 and table["sharpe"].notna().all()
    assert rets.index.min() >= D.DEV[0] and rets.index.max() <= D.DEV[1]
    assert len(reg.trial_sharpes()) == 3 and reg.holdout_views() == 0


def test_scanner_and_freshness(market, lib):
    prices = market[0]
    tab = D.scanner(lib["example-70-30-spy-trend-filter"], prices)
    assert set(tab["asset"]) == {"SPY", "GLD"} and "rule: SPY above its 200-day average" in tab
    from aurum.config import load_config

    c = load_config()
    c["offline"] = True
    assert D.freshness(prices, c)["status"].str.contains("SYNTHETIC").all()


def test_decision_chart_links_every_panel_to_one_time_axis(market, lib):
    prices, rf, _ = market
    run = E.run_spec(lib["example-70-30-spy-trend-filter"], prices, rf)
    fig = DC.decision_chart(
        run, "SPY", {"SPY": E.run_spec(lib["spy-buy-and-hold"], prices, rf)}, start="2020-01-01", end="2020-12-31"
    )
    assert {getattr(t, "xaxis", None) or "x" for t in fig.data} == {"x"}
    names = [t.name for t in fig.data]
    assert "SPY price" in names and "SPY SMA 200" in names and any("orders (SPY)" in str(n) for n in names)
    assert fig.layout.hovermode == "x unified" and fig.layout.yaxis.domain[1] == 1
    buys = [t for t in fig.data if str(t.name).startswith("Buy orders")]
    assert buys and "of account" in buys[0].text[0]
