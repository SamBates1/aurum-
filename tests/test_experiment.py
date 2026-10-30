"""The 50/50 experiment runner: proposals from scans, exits, pot limits, and a full evening run on a fake Alpaca."""

import sys

import numpy as np
import pandas as pd
import pytest
from test_broker import FakeAlpaca

from aurum import broker as BR
from aurum import experiment as EX
from aurum.config import ROOT

sys.path.insert(0, str(ROOT / "scripts"))
TODAY = pd.Timestamp("2026-10-29")


def _daily(trend, seed, n=400):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(trend, 0.01, n)))
    idx = pd.bdate_range(end=TODAY, periods=n)
    v = np.full(n, 1e6)
    v[-1] = 5e6  # volume spike on the last day (helps a breakout setup)
    return pd.DataFrame({"Open": c, "High": c * 1.005, "Low": c * 0.995, "Close": c, "Volume": v}, index=idx)


def _ranking(syms):
    return pd.DataFrame({"score": np.linspace(95, 60, len(syms))}, index=pd.Index(syms, name="symbol"))


def test_long_term_live_test_proposes_staged_buys_within_limits():
    syms = [f"S{i}" for i in range(20)]
    daily = {s: _daily(0.002, i) for i, s in enumerate(syms)}
    ps = EX.propose("long-term", 50_000, 50_000, {}, _ranking(syms), "live-test", daily, 1.3, {}, TODAY)
    assert 0 < len(ps) <= EX.LIMITS["long-term"]["max_positions"]
    assert all(p.side == "buy" and p.type == "limit" for p in ps)
    assert sum(p.qty * p.limit_price for p in ps) <= 50_000
    assert all(p.qty * p.limit_price <= 0.10 * 50_000 / 3 + 50 for p in ps)  # first third of a <=10% position
    assert all("live-test" in p.reason for p in ps)
    untested = EX.propose("long-term", 50_000, 50_000, {}, _ranking(syms), "untested", daily, 1.3, {}, TODAY)
    assert untested == []  # without the live test, untested rankings never buy


def test_exits_and_time_stop():
    syms = ["A", "B"]
    daily = {"A": _daily(-0.004, 1), "B": _daily(0.002, 2)}
    held = {"A": {"qty": 10, "cost": 1000.0}}
    ps = EX.propose("long-term", 50_000, 40_000, held, _ranking(["B"]), "live-test", daily, 1.3, {}, TODAY)
    assert any(p.symbol == "A" and p.side == "sell" for p in ps)  # fell out of the ranks / assessment SELL
    st = {"B": {"opened": "2026-09-01"}}
    sw = EX.propose(
        "swing", 50_000, 45_000, {"B": {"qty": 5, "cost": 500.0}}, _ranking(syms), "live-test", daily, 1.3, st, TODAY
    )
    assert any(p.symbol == "B" and "time stop" in p.reason for p in sw)


def test_swing_entries_carry_bracket_stop_and_target():
    syms = [f"T{i}" for i in range(15)]
    daily = {s: _daily(0.003, 10 + i) for i, s in enumerate(syms)}
    ps = EX.propose("swing", 50_000, 50_000, {}, _ranking(syms), "live-test", daily, 1.3, {}, TODAY)
    for p in ps:
        assert p.stop_loss < p.limit_price < p.take_profit
        assert p.request("x").payload()["order_class"] == "bracket"
    assert len(ps) <= EX.LIMITS["swing"]["max_positions"]


def test_full_evening_run_manual_mode_proposes_without_sending(tmp_path, monkeypatch):
    import run_experiment as RE

    monkeypatch.setattr(EX, "FOLDER", tmp_path)
    syms = [f"S{i}" for i in range(10)]
    daily = {s: _daily(0.002, i) for i, s in enumerate(syms)} | {"SPY": _daily(0.001, 99)}
    monkeypatch.setattr(
        RE, "rankings", lambda: {"long-term": (_ranking(syms), "live-test"), "swing": (_ranking(syms), "live-test")}
    )
    fake = FakeAlpaca()
    b = BR.PaperBroker(fake, cfg={"paper_orders": {"enabled": True, "mode": "manual"}}, folder=tmp_path)
    monkeypatch.setattr(RE.BR, "settings", lambda cfg=None: {**BR.DEFAULTS, "enabled": True, "mode": "manual"})
    monkeypatch.setattr(RE.EX.BR, "settings", lambda cfg=None: {**BR.DEFAULTS, "enabled": True, "mode": "manual"})
    out = RE.main(broker=b, frames=daily)
    assert out["proposals"] and all(p.status == "proposed" for p in out["proposals"])
    assert not [c for c in fake.calls if c[0] == "POST"]  # manual mode: nothing sent
    saved = EX.load(tmp_path)
    assert saved["proposals"] and (tmp_path / "experiment.md").is_file()
    # the owner approves one: it goes through the broker's checks with the same client id
    p = saved["proposals"][0]
    req = EX.Proposal(**{k: p[k] for k in EX.Proposal.__dataclass_fields__}).request(EX.plan_id(saved["asof"], p))
    b.submit(req, p["plan"]["reference_price"], pd.Timestamp.now(tz="UTC"), approved=True, market_open=False)
    with pytest.raises(BR.OrderBlocked, match="already sent"):
        b.submit(req, p["plan"]["reference_price"], pd.Timestamp.now(tz="UTC"), approved=True, market_open=False)


def test_bracket_legs_count_in_the_pot():
    parent = {
        "client_order_id": "AUR-SW-abc",
        "symbol": "X",
        "side": "buy",
        "filled_qty": "10",
        "filled_avg_price": "100",
        "filled_at": "2026-11-02T14:31:00Z",
        "legs": [
            {
                "symbol": "X",
                "side": "sell",
                "filled_qty": "10",
                "filled_avg_price": "110",
                "filled_at": "2026-11-05T15:00:00Z",
                "client_order_id": "leg-1",
            }
        ],
    }
    pots = BR.ledgers_from_orders([parent], {"long-term": 50_000, "swing": 50_000})
    assert pots["swing"]["positions"] == {} and pots["swing"]["realised"] == pytest.approx(100.0)
    assert pots["swing"]["cash"] == pytest.approx(50_100.0)
