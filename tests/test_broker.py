"""Platform phase 7: Alpaca paper orders with a mocked broker. No network, no real orders."""

import pandas as pd
import pytest

from aurum import broker as BR


class FakeAlpaca:
    """Minimal in-memory imitation of Alpaca's paper API (accepts, partially fills, rejects duplicates)."""

    def __init__(self, cash=100_000.0):
        self.cash, self.pos, self.open, self.history, self.calls = cash, {}, [], [], []

    def __call__(self, method, path, body):
        self.calls.append((method, path))
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
            }
        if path == "/v2/positions":
            return [{"symbol": s, "qty": p["qty"], "market_value": p["qty"] * p["px"]} for s, p in self.pos.items()]
        if path.startswith("/v2/orders?"):
            return self.open if "status=open" in path else self.history
        if method == "POST" and path == "/v2/orders":
            if any(o["client_order_id"] == body["client_order_id"] for o in self.history):
                raise BR.BrokerError("HTTP 422: client_order_id must be unique")
            o = dict(body, id=f"o{len(self.history)}", status="accepted", filled_qty="0")
            self.history.append(o)
            self.open.append(o)
            return o
        if method == "DELETE":
            self.open = []
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


def test_emergency_stop_pauses_then_cancels(tmp_path):
    fake = FakeAlpaca()
    b = BR.PaperBroker(fake, cfg=ON, folder=tmp_path)
    b.submit(BR.OrderRequest("SPY", "buy", 1, plan_id="x"), 700.0, NOW, approved=True)
    b.cancel_all_and_pause("owner pressed stop")
    assert b.paused() and fake.open == [] and ("DELETE", "/v2/orders") in fake.calls
