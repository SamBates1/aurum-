"""Platform phase 7: Alpaca paper orders with a mocked broker. No network, no real orders."""

import pandas as pd
import pytest

from aurum import broker as BR


class FakeAlpaca:
    """Minimal in-memory imitation of Alpaca's paper API (accepts, partially fills, rejects duplicates)."""

    def __init__(self, cash=100_000.0):
        self.cash, self.pos, self.open, self.history, self.calls = cash, {}, [], [], []
        self.suspended, self.fail_next_post = False, None

    def __call__(self, method, path, body):
        self.calls.append((method, path))
        if path == "/v2/account/configurations":
            self.suspended = bool(body["suspend_trade"])
            return {"suspend_trade": self.suspended}
        if method == "GET" and path.startswith("/v2/orders/"):
            oid = path.rsplit("/", 1)[-1]
            o = next(x for x in self.history if x["id"] == oid)
            return dict(o, status="new" if o in self.open else "canceled")
        if path == "/v2/account":
            eq = self.cash + sum(p["qty"] * p["px"] for p in self.pos.values())
            return {
                "status": "ACTIVE",
                "currency": "USD",
                "cash": self.cash,
                "buying_power": self.cash,
                "equity": eq,
                "trading_blocked": False,
                "account_blocked": False,
                "trade_suspended_by_user": self.suspended,
            }
        if path == "/v2/positions":
            return [{"symbol": s, "qty": p["qty"], "market_value": p["qty"] * p["px"]} for s, p in self.pos.items()]
        if path.startswith("/v2/orders?"):
            return self.open if "status=open" in path else self.history
        if method == "POST" and path == "/v2/orders":
            if self.suspended:
                raise BR.BrokerError("HTTP 403: new orders are rejected by user request")
            if self.fail_next_post:
                msg, self.fail_next_post = self.fail_next_post, None
                raise BR.BrokerError(msg)
            if any(o["client_order_id"] == body["client_order_id"] for o in self.history):
                raise BR.BrokerError("HTTP 422: client_order_id must be unique")
            o = dict(body, id=f"o{len(self.history)}", status="accepted", filled_qty="0")
            self.history.append(o)
            self.open.append(o)
            return o
        if method == "DELETE" and path == "/v2/orders":
            self.open = []
            return {}
        if method == "DELETE" and path.startswith("/v2/orders/"):
            oid = path.rsplit("/", 1)[-1]
            self.open = [o for o in self.open if o["id"] != oid]
            return {}
        raise AssertionError(path)

    def fill(self, i, qty, px):
        o = self.history[i]
        o["filled_qty"], o["filled_avg_price"] = str(qty), str(px)
        o["status"] = "filled" if float(qty) == float(o["qty"]) else "partially_filled"
        p = self.pos.setdefault(o["symbol"], {"qty": 0.0, "px": px})
        p["qty"] += qty if o["side"] == "buy" else -qty
        self.cash -= qty * px if o["side"] == "buy" else -qty * px


NOW = pd.Timestamp.now(tz="UTC")
ON = {"paper_orders": {"enabled": True, "mode": "manual"}}


def test_only_the_paper_address_exists_and_orders_start_switched_off(tmp_path):
    assert BR.PAPER_URL == "https://paper-api.alpaca.markets"
    import inspect

    src = inspect.getsource(BR)
    assert "https://api.alpaca.markets" not in src  # no live trading address anywhere
    b = BR.PaperBroker(FakeAlpaca(), cfg={}, folder=tmp_path)
    with pytest.raises(BR.OrderBlocked, match="switched off"):
        b.submit(BR.OrderRequest("SPY", "buy", 1, plan_id="p1"), 700.0, NOW, approved=True)


def test_checks_block_unsafe_orders(tmp_path):
    fake = FakeAlpaca(cash=5_000)
    b = BR.PaperBroker(fake, cfg=ON, folder=tmp_path)
    req = BR.OrderRequest("SPY", "buy", 10, plan_id="p1")
    chk = b.check(req, 700.0, NOW - pd.Timedelta(hours=2), approved=False)
    text = " ".join(chk.reasons)
    assert not chk.ok and "approval" in text and "minutes old" in text and "buying power" in text
    sell = b.check(BR.OrderRequest("AAPL", "sell", 1, plan_id="p2"), 300.0, NOW, approved=True)
    assert "no short selling" in " ".join(sell.reasons)
    b.pause("test")
    assert "pause" in " ".join(b.check(BR.OrderRequest("SPY", "buy", 1), 700.0, NOW, True).reasons)
    b.resume()
    assert b.check(BR.OrderRequest("SPY", "buy", 1, plan_id="p3"), 700.0, NOW, True).ok


def test_submit_partial_fill_duplicate_and_reconcile(tmp_path):
    fake = FakeAlpaca()
    b = BR.PaperBroker(fake, cfg=ON, folder=tmp_path)
    req = BR.OrderRequest("SPY", "buy", 10, type="limit", limit_price=701.0, pot="long-term", plan_id="plan-1")
    res = b.submit(req, 700.0, NOW, approved=True)
    assert res["status"] == "accepted" and res["client_order_id"].startswith("AUR-LT-")
    with pytest.raises(BR.OrderBlocked, match="already sent"):
        b.submit(req, 700.0, NOW, approved=True)  # resend of the same plan's order
    fake.fill(0, 6, 700.5)  # partial fill: only 6 of 10
    fake.open = []
    swing = BR.OrderRequest("AAPL", "buy", 5, pot="swing", plan_id="plan-2", take_profit=330, stop_loss=290)
    assert swing.payload()["order_class"] == "bracket"
    b.submit(swing, 300.0, NOW, approved=True)
    fake.fill(1, 5, 300.0)
    pots = BR.ledgers_from_orders(fake.history, {"long-term": 50_000, "swing": 50_000})
    assert pots["long-term"]["positions"]["SPY"]["qty"] == 6 and pots["swing"]["positions"]["AAPL"]["qty"] == 5
    assert pots["long-term"]["cash"] == pytest.approx(50_000 - 6 * 700.5)
    assert BR.reconcile(pots, b.positions()) == []
    fake.pos["MSFT"] = {"qty": 2.0, "px": 500.0}  # something bought outside Aurum
    assert BR.reconcile(pots, b.positions()) == ["MSFT: Aurum's pots hold 0, Alpaca shows 2"]
    audit = (tmp_path / "audit.jsonl").read_text()
    assert "submitted" in audit and "APCA" not in audit


def _held_with_protection(tmp_path, qty=29, px=167.0):
    """A held swing position with its stop/target pair working at Alpaca, as Alpaca lists it."""
    fake = FakeAlpaca()
    fake.pos["GILD"] = {"qty": float(qty), "px": px}
    oco = {
        "id": "oco1", "symbol": "GILD", "side": "sell", "qty": str(qty), "type": "limit", "limit_price": "189.95",
        "client_order_id": "AUR-SW-abc", "filled_qty": "0",
        "legs": [{"id": "oco1s", "symbol": "GILD", "side": "sell", "type": "stop", "stop_price": "161.05"}],
    }  # fmt: skip
    fake.open.append(oco)
    fake.history.append(oco)
    return fake, BR.PaperBroker(fake, cfg=ON, folder=tmp_path)


def test_emergency_stop_blocks_new_orders_but_keeps_protective_stops(tmp_path):
    # audit F2: the stop used to cancel EVERY open order, including the stops protecting held positions
    fake, b = _held_with_protection(tmp_path)
    b.submit(BR.OrderRequest("SPY", "buy", 1, plan_id="x"), 700.0, NOW, approved=True)
    res = b.cancel_all_and_pause("owner pressed stop")
    assert res == {"paused_at_alpaca": True, "buys_cancelled": 1, "protective_sells_kept": 1}
    assert [o["id"] for o in fake.open] == ["oco1"] and ("DELETE", "/v2/orders") not in fake.calls
    assert b.paused() and fake.suspended
    # a second machine (no local PAUSE file) sees the pause too, because it is set at Alpaca
    other = BR.PaperBroker(fake, cfg=ON, folder=tmp_path / "elsewhere")
    assert other.paused()
    assert "pause" in " ".join(other.check(BR.OrderRequest("SPY", "buy", 1, plan_id="y"), 700.0, NOW, True).reasons)
    assert b.resume() and not other.paused()


def test_blocked_exit_leaves_the_stop_working(tmp_path):
    # audit F1: the stop and target used to be cancelled BEFORE the checks, so a blocked sale left no protection
    fake, b = _held_with_protection(tmp_path)
    req = BR.OrderRequest("GILD", "sell", 29, pot="swing", plan_id="2026-12-01:swing:GILD:sell")
    with pytest.raises(BR.OrderBlocked, match="minutes old"):
        b.submit_exit(req, 167.0, NOW - pd.Timedelta(hours=16), approved=True, market_open=True)
    assert [o["id"] for o in fake.open] == ["oco1"]


def test_exit_cancels_protection_only_after_the_checks_pass_and_then_sells(tmp_path):
    fake, b = _held_with_protection(tmp_path)
    req = BR.OrderRequest("GILD", "sell", 29, pot="swing", plan_id="exit")
    res = b.submit_exit(req, 167.0, NOW, approved=True, market_open=True)
    assert res["status"] == "accepted" and [o["side"] for o in fake.open] == ["sell"]
    assert fake.open[0]["client_order_id"] == req.client_id()  # the sale replaced the stop/target pair


def test_failed_exit_puts_the_stop_and_target_back(tmp_path):
    fake, b = _held_with_protection(tmp_path)
    fake.fail_next_post = "HTTP 500: internal error"
    with pytest.raises(BR.BrokerError, match="were put back"):
        b.submit_exit(BR.OrderRequest("GILD", "sell", 29, pot="swing", plan_id="exit"), 167.0, NOW, True, True)
    (back,) = fake.open
    assert back["order_class"] == "oco" and back["take_profit"] == {"limit_price": "189.95"}
    assert back["stop_loss"] == {"stop_price": "161.05"} and back["time_in_force"] == "gtc"
    assert float(back["qty"]) == 29 and back["client_order_id"].startswith("AUR-SW-")


def test_order_size_limit_caps_buys_but_never_blocks_a_sale(tmp_path):
    # audit F7
    fake = FakeAlpaca()
    fake.pos["WIN"] = {"qty": 100.0, "px": 120.0}  # worth $12,000, above the $10,000 order limit
    b = BR.PaperBroker(fake, cfg=ON, folder=tmp_path)
    assert b.check(BR.OrderRequest("WIN", "sell", 100, pot="swing", plan_id="x"), 120.0, NOW, True, False).ok
    buy = b.check(BR.OrderRequest("SPY", "buy", 20, plan_id="y"), 700.0, NOW, True, False)
    assert "above the $10,000 limit" in " ".join(buy.reasons)


def test_every_order_is_read_not_only_the_newest_500(tmp_path):
    # audit F6: Alpaca returns at most 500 orders per request, newest first
    orders = []
    for i in range(300):  # 300 round trips = 600 orders
        t = f"2026-01-{1 + i // 20:02d}T{i % 20:02d}:00:00"
        base = {"symbol": "ABC", "filled_qty": "1", "filled_avg_price": "100"}
        orders.append(dict(base, id=f"b{i}", client_order_id=f"AUR-SW-b{i}", side="buy", submitted_at=t + ".1Z"))
        orders.append(dict(base, id=f"s{i}", client_order_id=f"AUR-SW-s{i}", side="sell", submitted_at=t + ".2Z"))

    def paged(method, path, body):
        import urllib.parse as up

        q = dict(up.parse_qsl(path.split("?", 1)[1]))
        pool = sorted(orders, key=lambda o: o["submitted_at"], reverse=True)
        if q.get("until"):
            pool = [o for o in pool if o["submitted_at"] <= q["until"]]
        return pool[: int(q["limit"])]

    b = BR.PaperBroker(paged, cfg=ON, folder=tmp_path)
    assert len(b.orders("all", 500)) == 500  # one request misses the oldest 100
    everything = b.orders_all()
    assert len(everything) == 600
    pot = BR.ledgers_from_orders(everything, {"swing": 50_000})["swing"]
    assert pot["cash"] == 50_000 and not pot["positions"]
    wrong = BR.ledgers_from_orders(b.orders("all", 500)[:-1], {"swing": 50_000})["swing"]
    assert wrong["positions"]  # what the old single request could produce: a holding that does not exist


def test_position_records_the_day_it_opened():
    o = [{"client_order_id": "AUR-SW-1", "symbol": "ABC", "side": "buy", "filled_qty": "2", "filled_avg_price": "10",
          "filled_at": "2026-11-12T14:31:00Z"}]  # fmt: skip
    assert BR.ledgers_from_orders(o, {"swing": 100})["swing"]["positions"]["ABC"]["opened"] == "2026-11-12"
