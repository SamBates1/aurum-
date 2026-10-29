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
    assert book.rebalance("GLD", 0.6, 100.0, PX).startswith("BUY")
    held = book.state["positions"]["GLD"]["qty"] * 100.0
    assert held == pytest.approx(0.6 * sleeve, rel=0.01)
    assert book.rebalance("GLD", 0.62, 100.0, PX) is None  # inside the 5-point band
    assert book.rebalance("GLD", 0.3, 100.0, PX).startswith("SELL")
    assert book.state["positions"]["GLD"]["qty"] * 100.0 == pytest.approx(0.3 * sleeve, rel=0.02)
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
