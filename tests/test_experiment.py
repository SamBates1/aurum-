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
    # a ranking too short to say where A stands is "not ranked today", not "ranked low" (audit F4): no sale
    ps = EX.propose("long-term", 50_000, 40_000, held, _ranking(["B"]), "live-test", daily, 1.3, {}, TODAY)
    assert not any(p.symbol == "A" and p.side == "sell" for p in ps)
    long_table = _ranking(["B"] + [f"Z{i}" for i in range(EX.LIMITS["long-term"]["exit_rank"])])
    ps = EX.propose("long-term", 50_000, 40_000, held, long_table, "live-test", daily, 1.3, {}, TODAY)
    assert any(p.symbol == "A" and p.side == "sell" and "top 150" in p.reason for p in ps)
    ranked_149 = _ranking([f"Z{i}" for i in range(149)] + ["A"] + [f"Y{i}" for i in range(20)])
    ps = EX.propose("long-term", 50_000, 40_000, held, ranked_149, "live-test", daily, 1.3, {}, TODAY)
    assert not any(p.symbol == "A" and p.side == "sell" for p in ps)  # rank 150 of 170 is still inside the rule
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


def test_swing_orders_are_whole_shares():
    syms = [f"T{i}" for i in range(15)]
    daily = {s: _daily(0.003, 10 + i) for i, s in enumerate(syms)}
    ps = EX.propose(
        "swing", 50_000, 50_000, {}, _ranking(syms), "live-test", daily, 1.3, {}, TODAY, fractionable=set(syms)
    )
    assert ps and all(p.qty == int(p.qty) and p.qty >= 1 for p in ps)


def test_paper_status_lists_orders(tmp_path, monkeypatch):
    import paper_status as PS

    fake = FakeAlpaca()
    b = BR.PaperBroker(fake, cfg={"paper_orders": {"enabled": True}}, folder=tmp_path)
    b.submit(
        BR.OrderRequest("PSX", "buy", 17, type="limit", limit_price=285.43, pot="swing", plan_id="s"),
        285.0,
        pd.Timestamp.now(tz="UTC"),
        approved=True,
    )
    monkeypatch.setattr(PS.BR, "FOLDER", tmp_path)
    monkeypatch.setattr(PS.EX, "load", lambda folder=None: {})
    text = PS.main(b)
    assert "Open orders: 1" in text and "| PSX | buy | 17 | limit | 285.43" in text and "swing" in text


def test_swing_brackets_are_good_till_cancelled():
    syms = [f"T{i}" for i in range(15)]
    daily = {s: _daily(0.003, 10 + i) for i, s in enumerate(syms)}
    ps = EX.propose("swing", 50_000, 50_000, {}, _ranking(syms), "live-test", daily, 1.3, {}, TODAY)
    assert ps and all(p.request("x").payload()["time_in_force"] == "gtc" for p in ps)
    lt = EX.propose("long-term", 50_000, 50_000, {}, _ranking(syms), "live-test", daily, 1.3, {}, TODAY)
    assert all(p.request("x").payload()["time_in_force"] == "day" for p in lt)  # plain entries expire daily


def test_unprotected_swing_position_gets_stop_and_target_reattached():
    daily = {"PSX": _daily(0.002, 5)}
    held = {"PSX": {"qty": 17, "cost": 17 * 285.0}}
    ps = EX.propose(
        "swing",
        50_000,
        45_000,
        held,
        _ranking(["PSX"]),
        "live-test",
        daily,
        1.3,
        {"PSX": {"opened": str(TODAY.date()), "stop": 260.0, "targets": [["2R", 320.0, 2.0]]}},
        TODAY,
        protected=set(),
    )
    prot = [p for p in ps if "re-attach" in p.reason]
    assert len(prot) == 1 and prot[0].qty == 17 and (prot[0].stop_loss, prot[0].take_profit) == (260.0, 320.0)
    pay = prot[0].request("x").payload()
    assert pay["order_class"] == "oco" and pay["side"] == "sell" and pay["time_in_force"] == "gtc"
    assert float(pay["stop_loss"]["stop_price"]) < float(pay["take_profit"]["limit_price"])
    again = EX.propose(
        "swing",
        50_000,
        45_000,
        held,
        _ranking(["PSX"]),
        "live-test",
        daily,
        1.3,
        {"PSX": {"opened": str(TODAY.date())}},
        TODAY,
        protected={"PSX"},
    )
    assert not [p for p in again if "re-attach" in p.reason]  # already protected at Alpaca: nothing added


def test_exit_cancels_working_stop_and_target_first(tmp_path):
    fake = FakeAlpaca()
    b = BR.PaperBroker(fake, cfg={"paper_orders": {"enabled": True}}, folder=tmp_path)
    b.submit(BR.OrderRequest("PSX", "buy", 10, pot="swing", plan_id="b"), 285.0, pd.Timestamp.now(tz="UTC"), True)
    fake.fill(0, 10, 285.0)
    fake.open = []
    b.submit(
        BR.OrderRequest("PSX", "sell", 10, type="limit", take_profit=320.0, stop_loss=260.0, pot="swing", plan_id="p"),
        285.0,
        pd.Timestamp.now(tz="UTC"),
        True,
    )
    assert len(fake.open) == 1
    b.submit_exit(
        BR.OrderRequest("PSX", "sell", 10, pot="swing", plan_id="exit"), 285.0, pd.Timestamp.now(tz="UTC"), True
    )
    assert len([o for o in fake.open if o["type"] == "market"]) == 1 and not [
        o for o in fake.open if o.get("order_class") == "oco"
    ]


def test_protective_reattach_orders_do_not_free_position_slots():
    # 7 swing positions held with no working stop: the re-attach orders keep them open, so at most 1 new buy
    held_syms = [f"H{i}" for i in range(7)]
    new_syms = [f"N{i}" for i in range(10)]
    daily = {s: _daily(0.003, 30 + i) for i, s in enumerate(held_syms + new_syms)}
    held = {s: {"qty": 10, "cost": 1000.0} for s in held_syms}
    st = {s: {"opened": "2026-10-27", "stop": 90.0, "targets": [["2R", 130.0, 2.0]]} for s in held_syms}
    ps = EX.propose("swing", 50_000, 40_000, held, _ranking(new_syms + held_syms), "live-test", daily, 1.3, st, TODAY)
    reattach = [p for p in ps if p.side == "sell" and p.take_profit and p.stop_loss]
    exits = [p for p in ps if p.side == "sell" and not (p.take_profit and p.stop_loss)]
    buys = [p for p in ps if p.side == "buy" and p.symbol not in held]
    assert reattach  # the positions get their protection back
    assert len(held) - len(exits) + len(buys) <= EX.LIMITS["swing"]["max_positions"]


# ---- audit 2026-11-11 -------------------------------------------------------------------------------------------
def _entry(sym="ABC"):
    plan = {"stop": 90.0, "targets": [["2R", 120.0, 2.0], ["3R", 135.0, 3.0]], "tranches": [], "reference_price": 100.0}
    return {"pot": "swing", "symbol": sym, "side": "buy", "plan": plan}


def test_plan_is_kept_for_an_entry_that_fills_on_a_later_day():
    # audit F3: the plan used to be dropped the evening the order was sent but not yet filled
    empty = {"swing": {"positions": {}}, "long-term": {"positions": {}}}
    held = {
        "swing": {"positions": {"ABC": {"qty": 10, "cost": 1000, "opened": "2026-11-11"}}},
        "long-term": empty["long-term"],
    }
    state = EX.update_state({"long-term": {}, "swing": {}}, empty, [_entry()], pd.Timestamp("2026-11-10"))
    assert "ABC" not in state["swing"] and state["_pending"]["swing"]["ABC"]["stop"] == 90.0
    state = EX.update_state(state, held, [], pd.Timestamp("2026-11-11"))  # filled a day later; proposals file is new
    assert state["swing"]["ABC"]["stop"] == 90.0 and state["swing"]["ABC"]["opened"] == "2026-11-11"
    assert "ABC" not in state["_pending"]["swing"]
    state = EX.update_state(state, empty, [], pd.Timestamp("2026-12-01"))  # sold: the plan goes with it
    assert state["swing"] == {}


def test_position_with_no_plan_still_gets_a_clock_and_its_original_levels():
    held = {"swing": {"positions": {"GILD": {"qty": 29, "cost": 4960, "opened": "2026-11-02"}}}}
    known = {"GILD": {"stop": 161.05, "target": 189.95}}
    state = EX.update_state({}, held, [], pd.Timestamp("2026-11-11"), known)
    assert state["swing"]["GILD"] == {
        "opened": "2026-11-02", "tranches_left": [], "stop": 161.05, "targets": [["2R", 189.95, 2.0]],
    }  # fmt: skip
    bare = EX.update_state({}, held, [], pd.Timestamp("2026-11-11"))
    assert bare["swing"]["GILD"]["opened"] == "2026-11-02"  # the 28-day time stop can still fire


def test_staged_buy_uses_up_one_tranche_once():
    # found during the audit fix: every proposal carries a reference price, so the old "has a plan" test was always
    # true and a staged top-up never reduced the tranches left: the same third could be proposed every evening
    st = {
        "long-term": {
            "AXTI": {"opened": "2026-11-03", "tranches_left": [["pullback", 53.36, 19.5], ["quarterly", 55.0, 19.5]]}
        }
    }
    pots = {"long-term": {"positions": {"AXTI": {"qty": 39.0, "cost": 2000.0}}}}
    top_up = {"pot": "long-term", "symbol": "AXTI", "side": "buy", "plan": {"reference_price": 45.0}}
    st = EX.update_state(st, pots, [top_up], pd.Timestamp("2026-11-12"))
    assert st["long-term"]["AXTI"]["tranches_left"] == [["quarterly", 55.0, 19.5]]


def test_reattach_uses_original_levels_and_never_todays_price():
    # audit F5: with no saved plan the stop used to be recomputed from the latest close, following the price down
    held = {"H": {"qty": 10, "cost": 1000.0}}
    notes: list[str] = []
    args = ("swing", 50_000, 40_000, held, _ranking(["H"]), "live-test", {"H": _daily(0.003, 30)}, 1.3, {}, TODAY)
    none = EX.propose(*args, notes=notes)
    assert not [p for p in none if p.side == "sell"] and "ACTION NEEDED: H" in notes[0]
    back = EX.propose(*args, known_levels={"H": {"stop": 95.5, "target": 131.25}})
    (p,) = [p for p in back if p.side == "sell"]
    assert (p.stop_loss, p.take_profit) == (95.5, 131.25)


def test_levels_are_read_back_from_the_original_alpaca_orders():
    orders = [
        {"client_order_id": "AUR-SW-1", "symbol": "GILD", "side": "buy", "type": "limit", "limit_price": "172",
         "submitted_at": "2026-11-02T09:00:00Z",
         "legs": [{"type": "limit", "limit_price": "189.95"}, {"type": "stop", "stop_price": "161.05"}]},
        {"client_order_id": "AUR-LT-2", "symbol": "AXTI", "side": "buy", "type": "limit", "limit_price": "55",
         "submitted_at": "2026-11-02T09:00:00Z"},
        {"client_order_id": "AUR-SW-3", "symbol": "PSX", "side": "sell", "type": "limit", "limit_price": "320",
         "submitted_at": "2026-11-10T13:00:00Z", "legs": [{"type": "stop", "stop_price": "260"}]},
    ]  # fmt: skip
    assert EX.levels_from_orders(orders) == {
        "GILD": {"stop": 161.05, "target": 189.95},
        "PSX": {"stop": 260.0, "target": 320.0},
    }


def test_buys_already_working_at_alpaca_use_a_position_slot():
    # audit F8
    held_syms = [f"H{i}" for i in range(7)]
    new_syms = [f"N{i}" for i in range(10)]
    daily = {s: _daily(0.003, 30 + i) for i, s in enumerate(held_syms + new_syms)}
    held = {s: {"qty": 10, "cost": 1000.0} for s in held_syms}
    args = ("swing", 50_000, 40_000, held, _ranking(new_syms + held_syms), "live-test", daily, 1.3, {}, TODAY)
    free = [p for p in EX.propose(*args, protected=set(held_syms)) if p.side == "buy"]
    assert len(free) == 1  # 7 held + 1 = the limit of 8
    full = [p for p in EX.propose(*args, protected=set(held_syms), open_buys={free[0].symbol}) if p.side == "buy"]
    assert full == []  # that buy is still working at Alpaca: no slot left, and it is not proposed twice


def test_saved_long_term_ranking_reaches_past_the_exit_rank():
    import run_scans

    assert run_scans.SAVED_ROWS["long-term"] >= EX.LIMITS["long-term"]["exit_rank"] + 50


# ---- the Approve button (EX.approve): every outcome is a message, never a crash ----------------------------------
def _approve_setup(tmp_path):
    fake = FakeAlpaca()
    return fake, BR.PaperBroker(fake, cfg={"paper_orders": {"enabled": True, "mode": "manual"}}, folder=tmp_path)


def _prop(side, symbol, qty, type_, **kw):
    base = {"pot": "swing", "symbol": symbol, "side": side, "qty": qty, "type": type_, "limit_price": None,
            "take_profit": None, "stop_loss": None, "reason": "test", "plan": {"reference_price": 100.0},
            "status": "proposed"}  # fmt: skip
    return base | kw


def _fresh(symbol):
    return {"price": 100.0, "time": pd.Timestamp.now(tz="UTC")}


def test_approve_buy_reattach_and_exit(tmp_path):
    fake, b = _approve_setup(tmp_path)
    buy = _prop("buy", "ABC", 10, "limit", limit_price=101.0, take_profit=120.0, stop_loss=90.0)
    assert EX.approve(buy, "2026-11-10", b, _fresh, market_open=True).startswith("sent to Alpaca")
    assert fake.open[0]["order_class"] == "bracket" and fake.open[0]["time_in_force"] == "gtc"
    assert "already sent" in EX.approve(buy, "2026-11-10", b, _fresh, market_open=True)  # second click: refused
    fake.fill(0, 10, 100.0)
    fake.open = []
    again = EX.approve(buy, "2026-11-10", b, _fresh, market_open=True)  # after a refresh, once it has filled
    assert again.startswith("failed") and "must be unique" in again and fake.pos["ABC"]["qty"] == 10
    oco = _prop("sell", "ABC", 10, "limit", take_profit=120.0, stop_loss=90.0)
    assert EX.approve(oco, "2026-11-10", b, _fresh, market_open=True).startswith("sent to Alpaca")
    assert [o.get("order_class") for o in fake.open] == ["oco"]
    exit_ = _prop("sell", "ABC", 10, "market")
    stale = EX.approve(exit_, "2026-11-10", b, None, market_open=True)  # no live price while the market is open
    assert stale.startswith("blocked") and "minutes old" in stale
    assert [o.get("order_class") for o in fake.open] == ["oco"]  # blocked exit: the stop and target still work
    assert EX.approve(exit_, "2026-11-10", b, _fresh, market_open=True).startswith("sent to Alpaca")
    assert [o["type"] for o in fake.open] == ["market"]


def test_approve_survives_a_failed_price_lookup(tmp_path):
    # the bug of 10 Nov 2026: the latest-price request raised and the page crashed before any order was sent
    fake, b = _approve_setup(tmp_path)

    def broken(symbol):
        raise RuntimeError("HTTP 401 from the data API")

    buy = _prop("buy", "ABC", 10, "limit", limit_price=101.0)
    msg = EX.approve(buy, str(pd.Timestamp.now(tz="UTC").date()), b, broken, market_open=False)
    assert msg.startswith("sent to Alpaca") and "latest price unavailable (RuntimeError)" in msg
    assert EX.approve(_prop("buy", "XYZ", 1, "limit", plan={}), "2026-11-10", b, broken).endswith(
        "blocked: no price to check the order against"
    )


def test_orders_log_is_written_from_alpaca_history(tmp_path):
    orders = [
        {"id": "1", "client_order_id": "AUR-SW-1", "symbol": "GILD", "side": "buy", "qty": "29", "type": "limit",
         "status": "filled", "submitted_at": "2026-11-02T09:00:00Z", "filled_qty": "29", "filled_avg_price": "171.02",
         "legs": [{"id": "1a", "symbol": "GILD", "side": "sell", "type": "stop", "stop_price": "161.05",
                   "status": "canceled", "submitted_at": "2026-11-02T09:00:00Z"}]},
        {"id": "2", "client_order_id": "manual", "symbol": "SPY", "side": "buy", "qty": "1", "type": "market",
         "status": "filled", "submitted_at": "2026-11-03T09:00:00Z"},
    ]  # fmt: skip
    log = pd.read_csv(EX.write_orders_log(orders, tmp_path))
    assert len(log) == 3 and list(log["pot"]) == ["swing", "swing", "not Aurum"]
    assert log.loc[1, "parent_id"] == 1 and log.loc[1, "stop_price"] == 161.05
