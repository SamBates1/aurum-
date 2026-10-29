"""Paper-trading risk controls. Several are regression tests for v0.1 bugs."""

import json

import pytest

from aurum.paper import PaperPortfolio

PX = {"GLD": 100.0}


@pytest.fixture
def book(tmp_path, cfg):
    return PaperPortfolio(tmp_path / "ledger.json", cfg=cfg)


def test_repeated_buy_never_moves_stop_or_averages_in(book):
    """Regression: v0.1 recomputed the stop on every BUY, so a top-up after a fall LOWERED the stop."""
    book.apply("GLD", "BUY", 100.0, 0.15, 2.0, PX)
    pos = dict(book.state["positions"]["GLD"])
    assert pos["stop"] == pytest.approx(96.0)
    book.apply("GLD", "BUY", 97.0, 0.15, 5.0, {"GLD": 97.0})  # price fell, ATR jumped
    after = book.state["positions"]["GLD"]
    assert after["stop"] == pos["stop"] and after["qty"] == pos["qty"]
    assert sum(t["side"] == "BUY" for t in book.state["trades"]) == 1


def test_costs_are_charged_and_equity_accounts_for_them(book, cfg):
    book.apply("GLD", "BUY", 100.0, 0.15, 2.0, PX)
    fee = book.state["fees"]
    assert fee > 0
    assert book.equity(PX) == pytest.approx(cfg["paper"]["starting_cash"] - fee)
    book.apply("GLD", "SELL", 100.0, 0.15, 2.0, PX)
    assert book.state["realised_pnl"] == pytest.approx(-book.state["fees"])
    assert book.state["cash"] == pytest.approx(cfg["paper"]["starting_cash"] - book.state["fees"])


def test_stop_out_requires_fresh_signal(book):
    book.apply("GLD", "BUY", 100.0, 0.15, 2.0, PX)
    msg = book.apply("GLD", "BUY", 95.0, 0.15, 2.0, {"GLD": 95.0})
    assert msg.startswith("STOP") and "GLD" not in book.state["positions"]
    assert book.apply("GLD", "BUY", 96.0, 0.15, 2.0, {"GLD": 96.0}) is None  # still the same signal
    book.apply("GLD", "HOLD", 96.0, 0.15, 2.0, {"GLD": 96.0})  # signal resets
    assert book.apply("GLD", "BUY", 97.0, 0.15, 2.0, {"GLD": 97.0}).startswith("BUY")


def test_position_size_respects_caps(book, cfg):
    book.apply("GLD", "BUY", 100.0, 0.60, 2.0, PX)  # 60% vol -> exposure 0.25 of the sleeve
    value = book.state["positions"]["GLD"]["qty"] * 100.0
    sleeve = min(cfg["strategy"]["max_position_pct"], 1 / 6)
    assert value == pytest.approx(cfg["paper"]["starting_cash"] * sleeve * 0.25, rel=1e-3)


def test_invalid_price_and_untradeable_data_never_trade(book):
    assert book.apply("GLD", "BUY", float("nan"), 0.15, 2.0, PX).startswith("SKIP")
    assert book.apply("GLD", "BUY", -1.0, 0.15, 2.0, PX).startswith("SKIP")
    assert book.apply("GLD", "BUY", 100.0, 0.15, 2.0, PX, tradeable=False) is None
    assert not book.state["positions"] and not book.state["trades"]


def test_ledger_round_trip_and_v01_migration(tmp_path, cfg):
    path = tmp_path / "ledger.json"
    old = {
        "cash": 9000.0,
        "positions": {"GLD": {"qty": 10.0, "avg_price": 100.0, "stop": 95.0}},
        "trades": [],
        "history": [],
    }
    path.write_text(json.dumps(old))
    book = PaperPortfolio(path, cfg=cfg)
    assert book.equity({"GLD": 110.0}) == pytest.approx(9000 + 1100)
    book.save()
    assert PaperPortfolio(path, cfg=cfg).state["positions"]["GLD"]["entry_price"] == 100.0


def test_vol_hold_rebalance_moves_to_target_with_band(book, cfg):
    sleeve = cfg["paper"]["starting_cash"] * min(cfg["strategy"]["max_position_pct"], 1 / 6)

    def next_day():  # each call below stands for a different trading day (one order per asset per day)
        book.state["orders_by_day"] = {}

    assert book.rebalance("GLD", 0.6, 100.0, PX).startswith("BUY")
    held = book.state["positions"]["GLD"]["qty"] * 100.0
    assert held == pytest.approx(0.6 * sleeve, rel=0.01)
    next_day()
    assert book.rebalance("GLD", 0.62, 100.0, PX) is None  # inside the 5-point band
    assert book.rebalance("GLD", 0.3, 100.0, PX).startswith("SELL")
    assert book.state["positions"]["GLD"]["qty"] * 100.0 == pytest.approx(0.3 * sleeve, rel=0.02)
    next_day()
    assert book.rebalance("GLD", 0.0, 100.0, PX).startswith("SELL") and "GLD" not in book.state["positions"]
    assert book.state["cash"] == pytest.approx(cfg["paper"]["starting_cash"] - book.state["fees"], rel=1e-9)


def test_vol_hold_mode_decision_and_research(cfg):
    from aurum import pipeline

    cfg["strategy"]["mode"] = "vol_hold"
    cfg["model"]["retrain_every_days"] = 252
    r = pipeline.research("GLD", cfg=cfg)
    assert r.sim.daily["invested"].mean() > 0.9  # always invested
    d = pipeline.decide("GLD", r, cfg, context=False)
    assert 0 < d.target_weight <= 1 and d.notes[0].startswith("Always-invested mode")


def test_no_order_on_a_non_rebalance_day(tmp_path, cfg):
    from types import SimpleNamespace

    book = PaperPortfolio(tmp_path / "ledger.json", cfg)
    d = SimpleNamespace(
        ticker="GLD", target_weight=0.5, rebalance_day=False, last_price=100.0, tradeable=True, decision="BUY"
    )
    assert book.act(d, {"GLD": 100.0}) is None and not book.state["positions"]
    d.rebalance_day = True
    assert book.act(d, {"GLD": 100.0}).startswith("BUY")


def test_safety_checks_block_duplicates_bad_prices_and_the_kill_switch(tmp_path, cfg, monkeypatch):
    from aurum import safety

    monkeypatch.setattr(safety, "ROOT", tmp_path)
    monkeypatch.setattr(safety, "KILL_FILE", tmp_path / "STOP_TRADING")
    book = PaperPortfolio(tmp_path / "ledger.json", cfg)
    px = {"GLD": 100.0}
    assert book.rebalance("GLD", 0.5, 100.0, px).startswith("BUY")
    assert book.rebalance("GLD", 1.0, 100.0, px).startswith("BLOCKED BUY GLD: one_order_per_day")
    book.state["orders_by_day"] = {}
    assert "price_sane" in book.rebalance("GLD", 1.0, 100.0, px, last_close=60.0)  # 67% jump: bad tick
    (tmp_path / "STOP_TRADING").write_text("stop")
    assert "kill_switch" in book.rebalance("GLD", 1.0, 100.0, px, last_close=100.0)
    (tmp_path / "STOP_TRADING").unlink()
    cfg["live"]["trading_enabled"] = False
    assert "kill_switch" in book.rebalance("GLD", 1.0, 100.0, px, last_close=100.0)
    cfg["live"]["trading_enabled"] = True
    assert "data_fresh" in book.rebalance("GLD", 1.0, 100.0, px, tradeable=False)
    assert book.rebalance("GLD", 1.0, 100.0, px, last_close=100.0).startswith("BUY")


def test_decision_record_is_written_with_checks(tmp_path, cfg, monkeypatch):
    import json as _json
    from types import SimpleNamespace

    from aurum import safety

    monkeypatch.setattr(safety, "ROOT", tmp_path)
    book = PaperPortfolio(tmp_path / "ledger.json", cfg)
    d = SimpleNamespace(
        ticker="GLD",
        target_weight=0.5,
        rebalance_day=True,
        last_price=100.0,
        tradeable=True,
        decision="BUY",
        notes=["Always-invested mode: hold 50%"],
        ann_vol=0.3,
        as_of="2026-10-28",
    )
    book.act(d, {"GLD": 100.0})
    rec = _json.loads((tmp_path / "logs" / "decisions.jsonl").read_text().splitlines()[-1])
    assert rec["ticker"] == "GLD" and rec["allowed"] is True
    assert rec["planned_order"]["side"] == "BUY" and {c["check"] for c in rec["checks"]} >= {
        "kill_switch",
        "price_sane",
    }
    assert rec["expected_risk"]["position_volatility_contribution"] == pytest.approx(0.15)


def test_ledger_reconciles_after_random_rebalances(tmp_path, cfg):
    """Audit 2026-10-29: after any sequence of buys and partial sells, equity - starting cash must equal
    realised P&L + unrealised P&L (both net of fees), and cash can never go negative."""
    import numpy as np

    rng = np.random.default_rng(7)
    book = PaperPortfolio(tmp_path / "ledger.json", cfg)
    start = cfg["paper"]["starting_cash"]
    px = {"GLD": 100.0, "GDX": 30.0}
    for _ in range(60):
        book.state["orders_by_day"] = {}  # each step is a new trading day
        for t in px:
            px[t] *= float(np.exp(rng.normal(0, 0.02)))
        t = str(rng.choice(list(px)))
        book.rebalance(t, float(rng.uniform(0, 1)), px[t], px)
        book.mark_prices(px)
        eq = book.equity(px)
        assert book.state["cash"] >= -1e-9
        assert eq - start == pytest.approx(book.state["realised_pnl"] + book.unrealised_pnl(), abs=1e-6)
    book.save()
    again = PaperPortfolio(tmp_path / "ledger.json", cfg)  # restart: state survives exactly
    assert again.equity(px) == pytest.approx(book.equity(px))
