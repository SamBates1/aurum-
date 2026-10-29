"""Fair Test, registry, risk engine, eligibility gates and paper trading of strategy definitions."""

import copy
import json
from datetime import timezone

import numpy as np
import pandas as pd
import pytest

from aurum import fairtest as FT
from aurum import gates, risk, safety
from aurum import registry as R
from aurum import spec as SP
from aurum import spec_paper as SPP
from aurum import xlab as X


@pytest.fixture(scope="module")
def market():
    from aurum import data
    from aurum.config import load_config

    c = load_config()
    c["offline"] = True
    prices = {t: data.daily_prices_from(t, "2006-06-01", c) for t in ("SPY", "GLD")}
    idx = X.common_index(prices)
    return prices, data.cash_rate(idx, c)


@pytest.fixture(scope="module")
def lib():
    return SP.library()


# ---------------------------------------------------------------- Fair Test
def test_verdict_rules_match_the_preregistered_lab_rules():
    from run_lab import lab_verdict

    cases = [
        (
            {"d_sharpe": 0.2, "share_better": 0.9, "dd_rel": 0.0},
            {"d_sharpe": 0.1},
            {"d_sharpe": 0.1, "dd_rel": 0},
            {"d_sharpe": 0.05, "dd_rel": 0},
            0.7,
        ),
        (
            {"d_sharpe": 0.2, "share_better": 0.9, "dd_rel": 0.0},
            {"d_sharpe": 0.1},
            {"d_sharpe": -0.1, "dd_rel": 0},
            {"d_sharpe": 0.05, "dd_rel": 0},
            0.7,
        ),
        (
            {"d_sharpe": 0.0, "share_better": 0.5, "dd_rel": 0.3},
            {"d_sharpe": -0.01},
            {"d_sharpe": 0.0, "dd_rel": 0.1},
            {"d_sharpe": -0.05, "dd_rel": 0.2},
            0.6,
        ),
        ({"d_sharpe": -0.1, "share_better": 0.2, "dd_rel": 0.1}, {"d_sharpe": -0.2}, None, None, 0.1),
        ({"d_sharpe": 0.05, "share_better": 0.6, "dd_rel": 0.1}, {"d_sharpe": 0.0}, None, None, 0.4),
    ]
    for dev, dev2x, hold, pre, dsr in cases:
        status, _ = FT.verdict(dev, dev2x, hold, pre, dsr)
        lab = lab_verdict(dev, dev2x, hold, pre, dsr)
        expected = "passed" if lab.startswith("KEEP") else ("failed" if lab.startswith("REJECT") else "inconclusive")
        assert status == expected, (dev, lab, status)


def test_lookahead_check_catches_a_rule_that_peeks(market, lib, monkeypatch):
    prices, _ = market
    s = lib["example-70-30-spy-trend-filter"]
    assert FT.lookahead_check(s, prices)[0]
    import aurum.engine as eng

    real = eng.compute
    monkeypatch.setattr(eng, "compute", lambda k, p, params=None: real(k, p, params).shift(-5))  # tomorrow's values
    ok, why = FT.lookahead_check(s, prices)
    assert not ok and "look ahead" in why


def test_fair_test_end_to_end_and_reports(market, lib, tmp_path):
    prices, rf = market
    reg = R.Registry(tmp_path / "r.sqlite")
    res = FT.run_fair_test(
        lib["spy-gld-70-30-risk-cap"], prices, rf, registry=reg, library=lib, data_label="SYNTHETIC test"
    )
    names = [c["name"] for c in res["checks"]]
    assert names[:4] == ["Valid definition", "Enough clean data", "No look-ahead", "Accounting"]
    assert all(c["passed"] for c in res["checks"][:4])
    assert res["status"] in ("passed", "failed", "inconclusive") and res["explanation"]
    assert res["numbers"]["benchmark"].startswith("A: 70/30") and len(res["numbers"]["sensitivity"]) >= 4
    assert reg.holdout_views() == 1 and len(reg.runs(kind="fair_test")) == 1
    path = FT.save_report(res, tmp_path)
    assert (
        "Verdict:" in path.read_text()
        and json.loads(path.with_suffix(".json").read_text())["spec_hash"] == res["spec_hash"]
    )
    assert FT.latest_results(tmp_path)[res["spec_hash"]]["status"] == res["status"]


def test_synthetic_reports_never_land_in_research(lib, monkeypatch, tmp_path):
    from aurum import fairtest

    monkeypatch.setattr(fairtest, "ROOT", tmp_path)
    res = {
        "strategy_id": "x",
        "spec_hash": "abc",
        "run_at": "2026-10-29T00:00",
        "data_label": "SYNTHETIC test data",
        "name": "x",
        "version": 1,
        "status": "failed",
        "explanation": "",
        "checks": [],
        "numbers": {},
        "code_fingerprint": "",
        "git_commit": "",
    }
    p = fairtest.save_report(res)
    assert "logs" in p.parts and "research" not in p.parts


# ---------------------------------------------------------------- registry
def test_registry_status_rules(tmp_path, lib):
    reg = R.Registry(tmp_path / "r.sqlite")
    h = reg.register(lib["spy-gld-70-30-monthly"])
    assert reg.status(h) == "draft"
    with pytest.raises(R.StatusError):
        reg.set_status(h, "paper_trading")  # cannot skip the test
    reg.set_status(h, "testing")
    reg.set_status(h, "passed")
    with pytest.raises(R.StatusError):
        reg.set_status(h, "approved_paper")  # owner only
    reg.set_status(h, "approved_paper", by="owner")
    assert [x["to_status"] for x in reg.history(h)] == ["testing", "passed", "approved_paper"]


def test_trials_and_luck_benchmark_grow_with_tries(tmp_path, lib):
    reg = R.Registry(tmp_path / "r.sqlite")
    base = reg.n_trials()
    for k in range(6):
        s = copy.deepcopy(lib["spy-gld-70-30-monthly"])
        s["schedule"]["band"] = 0.01 * k
        reg.log_run(reg.register(s), "designer", sharpe_daily=0.02 + 0.005 * k)
    assert reg.n_trials() == base + 6
    assert R.luck_benchmark(10) < R.luck_benchmark(1000)
    assert "by luck alone" in R.overfitting_warnings(reg, "x")[0]


# ---------------------------------------------------------------- risk engine
def _closes(n=400, vol=0.01, last_vol=None):
    rng = np.random.default_rng(0)
    r = rng.normal(0, vol, n)
    if last_vol:
        r[-21:] = rng.normal(0, last_vol, 21)
    return pd.Series(100 * np.exp(np.cumsum(r)), index=pd.bdate_range("2020-01-01", periods=n))


def test_risk_engine_only_cuts_risk():
    cfg = {"risk": {"max_weight_per_asset": 0.6}}
    rv = risk.review({"SPY": 0.9, "XYZ": 0.3}, {}, equity=100, peak_equity=100, closes={}, data_age_days=1, cfg=cfg)
    assert rv.approved["SPY"] == 0.6 and rv.approved["XYZ"] == 0.0
    assert {v["rule"] for v in rv.vetoes} == {"max_weight_per_asset", "allowed_assets"}
    # a deep drawdown blocks purchases but still allows sales
    rv = risk.review(
        {"SPY": 0.8, "GLD": 0.1}, {"SPY": 0.5, "GLD": 0.3}, equity=60, peak_equity=100, closes={}, data_age_days=1
    )
    assert rv.halted and rv.approved == {"SPY": 0.5, "GLD": 0.1}
    # volatility spike blocks buying that asset only
    rv = risk.review(
        {"SPY": 0.7, "GLD": 0.3},
        {"SPY": 0.2, "GLD": 0.3},
        equity=100,
        peak_equity=100,
        closes={"SPY": _closes(last_vol=0.08)},
        data_age_days=1,
    )
    assert rv.approved["SPY"] == 0.2 and rv.vetoes[0]["rule"] == "vol_spike"
    # stale data: no orders at all
    rv = risk.review({"SPY": 0.7}, {"SPY": 0.1}, equity=100, peak_equity=100, closes={}, data_age_days=10)
    assert rv.approved == {"SPY": 0.1} and rv.halted


def test_risk_engine_turnover_limit():
    rv = risk.review(
        {"SPY": 0.7, "GLD": 0.3},
        {"SPY": 0.0, "GLD": 0.0},
        equity=100,
        peak_equity=100,
        closes={},
        data_age_days=0,
        cfg={"risk": {"max_turnover_per_day": 0.5}},
    )
    assert sum(rv.approved.values()) == pytest.approx(0.5)


# ---------------------------------------------------------------- gates
def test_gates_need_evidence_and_owner_approval(lib, tmp_path):
    ap = tmp_path / "approvals.yaml"
    s = lib["spy-gld-70-30-risk-cap"]
    h = SP.spec_hash(s)
    el = gates.eligibility(s, "shadow", {}, path=ap)
    assert not el["eligible"] and [g["passed"] for g in el["gates"]] == [True, True, False, False, True]
    with pytest.raises(PermissionError):
        gates.add_approval(s, "shadow", approved_by="claude", evidence="x", path=ap)
    gates.add_approval(s, "shadow", approved_by="owner (test)", evidence="test", path=ap)
    ft = {h: {"status": "failed", "run_at": "2026-10-29"}}
    assert gates.eligibility(s, "shadow", ft, path=ap)["eligible"]  # a shadow may have failed
    assert not gates.eligibility(s, "main", ft, path=ap)["eligible"]  # but cannot be main
    edited = copy.deepcopy(s)
    edited["sizing"]["target_vol"] = 0.25
    assert not gates.eligibility(edited, "shadow", ft, path=ap)["eligible"]  # edits need a new approval
    gates.revoke(h, by="owner", path=ap)
    assert not gates.eligibility(s, "shadow", ft, path=ap)["eligible"]


def test_recorded_option3_approvals_match_the_templates(lib):
    a = gates.approval_for(SP.spec_hash(lib["spy-gld-70-30-monthly"]))
    b = gates.approval_for(SP.spec_hash(lib["spy-gld-70-30-risk-cap"]))
    assert a["role"] == "main" and "EXP-045" in a["based_on"] and b["role"] == "shadow"
    assert gates.eligibility(lib["spy-gld-70-30-monthly"], "main", {})["eligible"]


# ---------------------------------------------------------------- paper trading
def _ny(s):
    return pd.Timestamp(s, tz="America/New_York").tz_convert(timezone.utc).to_pydatetime()


def test_paper_trader_follows_backtest_timing(market, lib, tmp_path, cfg, monkeypatch):
    monkeypatch.setattr(safety, "ROOT", tmp_path)
    monkeypatch.setattr(safety, "KILL_FILE", tmp_path / "STOP_TRADING")
    prices, _ = market
    cut = pd.Timestamp("2024-03-01")  # first trading day of March: a monthly rebalance day
    daily = {t: p.loc[:cut] for t, p in prices.items()}
    tr = SPP.SpecPaperTrader(lib["spy-gld-70-30-monthly"], "main", tmp_path / "ledger.json", cfg)
    pend = tr.decide(daily)
    assert pend["decided"] == "2024-03-01" and pend["targets"] == {"SPY": 0.7, "GLD": 0.3}
    assert tr.decide(daily) is None  # once per close
    live = {t: float(prices[t].loc[:cut, "Close"].iloc[-1]) for t in prices}
    closes = {t: p["Close"] for t, p in daily.items()}
    assert tr.execute(live, closes, 0, now=_ny("2024-03-01 18:00")) == []  # not before the next open
    msgs = tr.execute(live, closes, 0, now=_ny("2024-03-04 09:45"))
    assert any(m.startswith("BUY SPY") for m in msgs) and any(m.startswith("BUY GLD") for m in msgs)
    w, eq = tr.weights(live)
    assert w["SPY"] == pytest.approx(0.7, abs=0.002) and w["GLD"] == pytest.approx(0.3, abs=0.002)
    assert tr.book.state["fees"] == pytest.approx(10000 * (0.7 * 2 + 0.3 * 3) / 1e4, rel=0.01)
    assert tr.book.state["pending"] is None
    recs = [json.loads(x) for x in (tmp_path / "logs" / "decisions.jsonl").read_text().splitlines()]
    assert [r["kind"] for r in recs] == ["decision", "order", "order"] and all(r["spec_hash"] == tr.hash for r in recs)
    # a non-rebalance day makes no decision
    nxt = {t: p.loc[: pd.Timestamp("2024-03-05")] for t, p in prices.items()}
    assert tr.decide(nxt) is None


def test_paper_trader_respects_the_off_switch(market, lib, tmp_path, cfg, monkeypatch):
    monkeypatch.setattr(safety, "ROOT", tmp_path)
    monkeypatch.setattr(safety, "KILL_FILE", tmp_path / "STOP_TRADING")
    (tmp_path / "STOP_TRADING").write_text("stop")
    prices, _ = market
    cut = pd.Timestamp("2024-03-01")
    daily = {t: p.loc[:cut] for t, p in prices.items()}
    tr = SPP.SpecPaperTrader(lib["spy-gld-70-30-monthly"], "main", tmp_path / "l.json", cfg)
    tr.decide(daily)
    live = {t: float(daily[t]["Close"].iloc[-1]) for t in daily}
    msgs = tr.execute(live, {t: p["Close"] for t, p in daily.items()}, 0, now=_ny("2024-03-04 10:00"))
    assert msgs and all(m.startswith(("BLOCKED", "Decision of")) for m in msgs) and not tr.book.state["positions"]
    assert (
        tr.book.state["pending"]
        and tr.execute(live, {t: p["Close"] for t, p in daily.items()}, 0, now=_ny("2024-03-04 11:00")) == []
    )
    (tmp_path / "STOP_TRADING").unlink()  # switched back on: the kept decision is retried the next day
    msgs = tr.execute(live, {t: p["Close"] for t, p in daily.items()}, 0, now=_ny("2024-03-05 10:00"))
    assert any(m.startswith("BUY SPY") for m in msgs) and tr.book.state["pending"] is None


def test_configured_paper_strategies_are_the_option3_pair():
    items = SPP.configured()
    assert [(i["spec"]["id"], i["role"]) for i in items] == [
        ("spy-gld-70-30-monthly", "main"),
        ("spy-gld-70-30-risk-cap", "shadow"),
    ]


# ---------------------------------------------------------------- desk and pages
def test_desk_sees_strategies_but_only_as_saved_text():
    from aurum import desk

    ctx = desk.strategy_context()
    assert "spy-gld-70-30-monthly" in ctx and "Owner approval: main" in ctx
    assert "STRATEGY DESIGNER" in desk.context_for("how is the 70/30 doing?")


@pytest.mark.parametrize(
    "page", ["pages/2_Strategy_Designer.py", "pages/3_Paper_Strategies.py", "pages/4_Strategy_Registry.py"]
)
def test_pages_render_without_errors(page, tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("AURUM_OFFLINE", "1")
    from aurum.config import ROOT

    at = AppTest.from_file(str(ROOT / page), default_timeout=300)
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def test_main_dashboard_survives_strategy_records_in_the_decision_log(tmp_path, monkeypatch):
    """Regression: the legacy paper tab crashed (KeyError 'ticker') once the strategy paper trader wrote records."""
    from streamlit.testing.v1 import AppTest

    from aurum.config import CFG, ROOT

    log = tmp_path / "decisions.jsonl"
    log.write_text(
        json.dumps({"time": "t", "kind": "decision", "strategy": "spy-gld-70-30-monthly", "role": "main"})
        + "\n"
        + json.dumps({"time": "t", "ticker": "GLD", "planned_order": None, "checks": [], "allowed": True})
        + "\n"
    )
    monkeypatch.setitem(CFG["live"], "decision_log", str(log))
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=500)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
