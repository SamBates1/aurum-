"""Alpaca PAPER trading integration (platform phase 7). Switched ON by the owner on 2026-10-30 (D-046), manual mode.

Safety design (D-042):
  * The only trading address in this module is Alpaca's paper endpoint. There is no setting that changes it, and
    `PaperBroker` refuses to start if the address is anything else. Real-money trading is not implemented.
  * Orders are blocked unless `paper_orders.enabled` is true in config.yaml, and each order needs the owner's
    approval (manual mode, the default). An optional auto mode must be enabled separately.
  * A held position never loses its protection by accident (audit 2026-11-11, F1/F2): an exit is checked BEFORE its
    stop and target are cancelled, they are put back if the sale fails, and the emergency stop cancels unfilled BUY
    orders only. The emergency pause is also set at Alpaca itself (suspend_trade), so every machine sees it.
  * Before every order, independent checks run (not the AI, not the strategy): pause switch, enabled flag, approval,
    buying power, position and order-size limits, data freshness, and duplicate prevention (a deterministic client
    order id plus a check for an open order on the same symbol and side).
  * Submitting is not filling: order status is read back and reconciled; partial fills, rejections and cancellations
    are recorded as they are.
Every request and result is appended to research/orders/audit.jsonl on the machine that sent it (no keys are ever
written). That file is local: the lasting record is Alpaca's own order history, which the evening run copies to
research/orders/orders-log.csv (experiment.write_orders_log).
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .config import CFG, ROOT
from .providers.keys import alpaca_keys, redact

PAPER_URL = "https://paper-api.alpaca.markets"
FOLDER = ROOT / "research" / "orders"
PAUSE_FILE = ROOT / "research" / "orders" / "PAUSE"
ORDER_TYPES = ("market", "limit", "stop", "stop_limit")
DEFAULTS = {
    "enabled": False,
    "mode": "manual",
    "max_order_usd": 10_000.0,
    "max_position_pct": 0.25,
    "max_data_age_minutes": 30,
}

DONE_STATUSES = ("canceled", "cancelled", "filled", "expired", "rejected", "replaced", "done_for_day")

Transport = Callable[[str, str, dict | None], dict | list]


class BrokerError(RuntimeError):
    pass


class OrderBlocked(BrokerError):
    pass


def settings(cfg: dict = CFG) -> dict:
    s = dict(DEFAULTS)
    s.update(cfg.get("paper_orders") or {})
    return s


def _http(method: str, path: str, body: dict | None = None) -> dict | list:
    keys = alpaca_keys()
    if not keys:
        raise BrokerError("Alpaca keys not set")
    url = PAPER_URL + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"APCA-API-KEY-ID": keys[0], "APCA-API-SECRET-KEY": keys[1], "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            txt = r.read().decode()
            return json.loads(txt) if txt else {}
    except urllib.error.HTTPError as e:
        raise BrokerError(redact(f"HTTP {e.code} {method} {path}: {e.read().decode(errors='replace')[:300]}")) from None


@dataclass
class OrderRequest:
    symbol: str
    side: str  # buy / sell
    qty: float
    type: str = "market"
    limit_price: float | None = None
    stop_price: float | None = None
    time_in_force: str = "day"
    take_profit: float | None = None  # bracket: both legs given -> order_class bracket
    stop_loss: float | None = None
    pot: str = "long-term"  # long-term / swing (tags the order for the pot ledgers)
    plan_id: str = ""  # the recommendation or plan this order carries out

    def client_id(self) -> str:
        """Deterministic: the same plan and order always get the same id, so a resend is refused as a duplicate."""
        raw = f"{self.plan_id}|{self.symbol}|{self.side}|{self.qty}|{self.type}|{self.limit_price}|{self.stop_price}"
        tag = "LT" if self.pot == "long-term" else "SW"
        return f"AUR-{tag}-{hashlib.sha256(raw.encode()).hexdigest()[:20]}"

    def payload(self) -> dict:
        if self.type not in ORDER_TYPES:
            raise BrokerError(f"unknown order type {self.type}")
        p = {
            "symbol": self.symbol,
            "side": self.side,
            "type": self.type,
            "time_in_force": self.time_in_force,
            "qty": str(self.qty),
            "client_order_id": self.client_id(),
        }
        if self.type in ("limit", "stop_limit"):
            p["limit_price"] = str(self.limit_price)
        if self.type in ("stop", "stop_limit"):
            p["stop_price"] = str(self.stop_price)
        if self.take_profit and self.stop_loss and self.side == "sell":
            # protect a position that is already held: one-cancels-other (target limit + stop), no new buy
            p["order_class"] = "oco"
            p["type"] = "limit"
            p["take_profit"] = {"limit_price": str(self.take_profit)}
            p["stop_loss"] = {"stop_price": str(self.stop_loss)}
            p.pop("limit_price", None)
        elif self.take_profit and self.stop_loss:
            p["order_class"] = "bracket"
            p["take_profit"] = {"limit_price": str(self.take_profit)}
            p["stop_loss"] = {"stop_price": str(self.stop_loss)}
        return p


@dataclass
class CheckResult:
    ok: bool
    reasons: list[str] = field(default_factory=list)


class PaperBroker:
    def __init__(self, transport: Transport | None = None, cfg: dict = CFG, folder: Path | None = None):
        if not PAPER_URL.startswith("https://paper-api."):
            raise BrokerError("refusing to run: the trading address is not Alpaca's paper endpoint")
        self.t = transport or _http
        self.sleep = time.sleep if transport is None else (lambda s: None)  # no waiting against a test double
        self.cfg = settings(cfg)
        self.folder = folder or FOLDER
        self.folder.mkdir(parents=True, exist_ok=True)

    # ---- read-only ------------------------------------------------------------------------------------------
    def account(self) -> dict:
        a = self.t("GET", "/v2/account", None)
        return {
            k: a.get(k)
            for k in (
                "status",
                "currency",
                "cash",
                "buying_power",
                "equity",
                "last_equity",
                "trading_blocked",
                "account_blocked",
                "trade_suspended_by_user",
            )
        } | {"paper": True}

    def positions(self) -> list[dict]:
        return list(self.t("GET", "/v2/positions", None))

    def orders(self, status: str = "all", limit: int = 200) -> list[dict]:
        return list(
            self.t(
                "GET",
                "/v2/orders?" + urllib.parse.urlencode({"status": status, "limit": limit, "nested": "true"}),
                None,
            )
        )

    def orders_all(self, page: int = 500, max_pages: int = 40) -> list[dict]:
        """Every order in the account, oldest pages included (Alpaca returns at most 500 per request, newest first)."""
        out: dict[str, dict] = {}
        until = None
        for _ in range(max_pages):
            q = {"status": "all", "limit": page, "nested": "true", "direction": "desc"}
            if until:
                q["until"] = until
            batch = list(self.t("GET", "/v2/orders?" + urllib.parse.urlencode(q), None))
            new = [o for o in batch if o.get("id") not in out]
            for o in new:
                out[o.get("id") or f"noid-{len(out)}"] = o
            times = [o.get("submitted_at") for o in batch if o.get("submitted_at")]
            if len(batch) < page or not new or not times:
                break
            until = min(times)
        return list(out.values())

    def order(self, order_id: str) -> dict:
        return dict(self.t("GET", f"/v2/orders/{order_id}", None))

    def test_connection(self) -> dict:
        try:
            a = self.account()
            return {"ok": a.get("status") == "ACTIVE", "status": a.get("status"), "paper": True}
        except Exception as e:
            return {"ok": False, "error": redact(str(e))}

    # ---- checks ---------------------------------------------------------------------------------------------
    def paused(self) -> bool:
        """Paused by a local PAUSE file, or at Alpaca itself (suspend_trade), which every machine can see."""
        if (self.folder / "PAUSE").is_file():
            return True
        try:
            return bool(self.t("GET", "/v2/account", None).get("trade_suspended_by_user"))
        except Exception:
            return False

    def _suspend(self, on: bool) -> bool:
        try:
            self.t("PATCH", "/v2/account/configurations", {"suspend_trade": bool(on)})
            return True
        except Exception as e:
            self._audit({"event": "suspend_failed", "on": on, "error": redact(str(e))[:200]})
            return False

    def pause(self, reason: str) -> bool:
        """Returns True if Alpaca confirmed the suspension (otherwise only this machine's PAUSE file is set)."""
        (self.folder / "PAUSE").write_text(f"{pd.Timestamp.now(tz='UTC')}: {reason}\n")
        at_broker = self._suspend(True)
        self._audit({"event": "pause", "reason": reason, "at_alpaca": at_broker})
        return at_broker

    def resume(self) -> bool:
        (self.folder / "PAUSE").unlink(missing_ok=True)
        at_broker = self._suspend(False)
        self._audit({"event": "resume", "at_alpaca": at_broker})
        return at_broker

    def check(
        self,
        req: OrderRequest,
        price: float,
        price_time,
        approved: bool,
        market_open: bool | None = None,
        exit_of_position: bool = False,
    ) -> CheckResult:
        """`exit_of_position`: the order sells a held position whose own stop/target will be cancelled just before it
        is sent, so those working sell orders are not counted as duplicates."""
        r = []
        if (self.folder / "PAUSE").is_file():
            r.append("emergency pause is on")
        if not self.cfg["enabled"]:
            r.append("paper orders are switched off (paper_orders.enabled is false) until the owner approves")
        if self.cfg["mode"] == "manual" and not approved:
            r.append("needs the owner's approval")
        age = (pd.Timestamp.now(tz="UTC") - pd.Timestamp(price_time).tz_convert("UTC")).total_seconds() / 60
        if market_open is None:
            try:
                market_open = bool(self.t("GET", "/v2/clock", None).get("is_open"))
            except Exception:
                market_open = True  # unknown: apply the strict intraday rule
        limit = self.cfg["max_data_age_minutes"] if market_open else 4 * 24 * 60  # closed: the last completed close
        if age > limit:
            r.append(f"price is {age:.0f} minutes old (limit {limit:.0f})")
        value = req.qty * price
        if req.side == "buy" and value > self.cfg["max_order_usd"]:  # caps new risk; never blocks a sale
            r.append(f"order value ${value:,.0f} above the ${self.cfg['max_order_usd']:,.0f} limit")
        try:
            acct = self.account()
            if acct.get("trading_blocked") or acct.get("account_blocked"):
                r.append("Alpaca reports the account as blocked")
            if acct.get("trade_suspended_by_user") and "emergency pause is on" not in r:
                r.append("emergency pause is on (trading suspended at Alpaca)")
            equity = float(acct.get("equity") or 0)
            if req.side == "buy" and value > float(acct.get("buying_power") or 0):
                r.append("not enough buying power")
            pos = {p["symbol"]: float(p.get("market_value") or 0) for p in self.positions()}
            after = pos.get(req.symbol, 0.0) + (value if req.side == "buy" else -value)
            if equity and after / equity > self.cfg["max_position_pct"]:
                r.append(
                    f"{req.symbol} would be {after / equity:.0%} of the account (limit "
                    f"{self.cfg['max_position_pct']:.0%})"
                )
            if req.side == "sell" and req.qty > float(
                next((p.get("qty") for p in self.positions() if p["symbol"] == req.symbol), 0) or 0
            ):
                r.append("selling more than is held (no short selling)")
            for o in self.orders("open"):
                if o.get("client_order_id") == req.client_id():
                    r.append("the same order was already sent")
                elif o.get("symbol") == req.symbol and o.get("side") == req.side:
                    if not (exit_of_position and req.side == "sell"):
                        r.append(f"an open {req.side} order for {req.symbol} already exists")
        except BrokerError as e:
            r.append(f"could not check the account: {e}")
        return CheckResult(not r, r)

    # ---- orders ---------------------------------------------------------------------------------------------
    def _checked(self, req, price, price_time, approved, market_open, exit_of_position=False) -> None:
        chk = self.check(req, price, price_time, approved, market_open, exit_of_position)
        self._audit(
            {
                "event": "check",
                "client_order_id": req.client_id(),
                "symbol": req.symbol,
                "side": req.side,
                "qty": req.qty,
                "ok": chk.ok,
                "reasons": chk.reasons,
            }
        )
        if not chk.ok:
            raise OrderBlocked("; ".join(chk.reasons))

    def _post(self, req: OrderRequest) -> dict:
        res = dict(self.t("POST", "/v2/orders", req.payload()))
        self._audit(
            {"event": "submitted", "client_order_id": req.client_id(), "id": res.get("id"), "status": res.get("status")}
        )
        return res

    def submit(
        self, req: OrderRequest, price: float, price_time, approved: bool, market_open: bool | None = None
    ) -> dict:
        self._checked(req, price, price_time, approved, market_open)
        return self._post(req)

    def cancel_open(self, symbol: str, side: str) -> int:
        """Cancel Aurum's open orders for one symbol and side."""
        n = 0
        for o in self.orders("open"):
            if o.get("symbol") == symbol and o.get("side") == side and pot_of(o.get("client_order_id")):
                self.cancel(o["id"])
                n += 1
        return n

    def _wait_cancelled(self, ids: list[str], tries: int = 10, pause: float = 0.5) -> None:
        """Alpaca cancels asynchronously: wait (briefly) until the orders no longer hold the shares."""
        for _ in range(tries):
            try:
                live = [i for i in ids if str(self.order(i).get("status")) not in DONE_STATUSES]
            except Exception:
                return  # cannot tell: carry on, the sale is retried below if the shares are still held
            if not live:
                return
            self.sleep(pause)

    def submit_exit(
        self, req: OrderRequest, price: float, price_time, approved: bool, market_open: bool | None = None
    ) -> dict:
        """Sell a held position without ever leaving it unprotected by accident (audit F1).

        1. every safety check runs FIRST: if the sale is blocked, the stop and target are untouched;
        2. only then are the position's working sell orders (its stop/target, which hold the shares) cancelled;
        3. the sale is sent; 4. if it fails, the stop and target are put back and the error says so."""
        self._checked(req, price, price_time, approved, market_open, exit_of_position=True)
        held = [o for o in self.orders("open") if o.get("symbol") == req.symbol and o.get("side") == "sell"]
        for o in held:
            try:
                self.cancel(o["id"])
            except BrokerError:
                pass  # e.g. the other half of a pair, already cancelled with its partner
        self._wait_cancelled([o["id"] for o in held])
        err: BrokerError | None = None
        for attempt in range(3):
            try:
                return self._post(req)
            except BrokerError as e:
                err = e
                if "insufficient" not in str(e).lower() and "held" not in str(e).lower():
                    break
                self.sleep(1.0 + attempt)  # the cancelled orders may still hold the shares for a moment
        restored = self._restore_protection(held)
        self._audit({"event": "exit_failed", "symbol": req.symbol, "error": str(err)[:300], "restored": restored})
        if held and not restored:
            raise BrokerError(
                f"the sale of {req.symbol} failed ({err}) AND its stop and target could NOT be put back: "
                "it has no protection now; re-attach them or sell it in Alpaca"
            )
        raise BrokerError(
            f"the sale of {req.symbol} failed ({err})" + ("; its stop and target were put back" if held else "")
        )

    def _restore_protection(self, cancelled: list[dict]) -> bool:
        """Re-create the stop/target that submit_exit cancelled. No checks apply: this only reduces risk."""
        if not cancelled:
            return True
        ok = True
        for o in cancelled:
            target, stop = protection_levels(o)
            qty = float(o.get("qty") or 0) - float(o.get("filled_qty") or 0)
            if qty <= 0:
                continue
            try:
                if target and stop:
                    r = OrderRequest(
                        o["symbol"], "sell", qty, type="limit", take_profit=target, stop_loss=stop,
                        time_in_force="gtc", pot=pot_of(o.get("client_order_id")) or "swing",
                        plan_id=f"restore:{o.get('id')}:{pd.Timestamp.now(tz='UTC').value}",
                    )  # fmt: skip
                elif stop:
                    r = OrderRequest(
                        o["symbol"], "sell", qty, type="stop", stop_price=stop, time_in_force="gtc",
                        pot=pot_of(o.get("client_order_id")) or "swing",
                        plan_id=f"restore:{o.get('id')}:{pd.Timestamp.now(tz='UTC').value}",
                    )  # fmt: skip
                else:
                    continue  # a plain limit sell (a target with no stop) protected nothing
                self._post(r)
            except Exception as e:
                ok = False
                self._audit({"event": "restore_failed", "symbol": o.get("symbol"), "error": redact(str(e))[:300]})
        return ok

    def cancel(self, order_id: str) -> None:
        self.t("DELETE", f"/v2/orders/{order_id}", None)
        self._audit({"event": "cancel", "id": order_id})

    def cancel_all_and_pause(self, reason: str) -> dict:
        """Emergency stop: pause first (nothing new goes out), then cancel every unfilled BUY order.

        Working SELL orders are kept on purpose: they are the stops and targets protecting held positions, and
        cancelling them would add risk, not remove it (audit F2)."""
        at_broker = self.pause(reason)
        cancelled = kept = 0
        for o in self.orders("open", 500):
            if o.get("side") == "buy":
                try:
                    self.cancel(o["id"])
                    cancelled += 1
                except BrokerError:
                    pass
            else:
                kept += 1
        self._audit({"event": "emergency_stop", "buys_cancelled": cancelled, "protective_sells_kept": kept})
        return {"paused_at_alpaca": at_broker, "buys_cancelled": cancelled, "protective_sells_kept": kept}

    def _audit(self, rec: dict) -> None:
        rec = {"time": str(pd.Timestamp.now(tz="UTC")), **rec}
        with open(self.folder / "audit.jsonl", "a") as f:
            f.write(json.dumps(rec, default=str) + "\n")


# ---------------------------------------------------------------------------------------------------------------
# pot ledgers and reconciliation
# ---------------------------------------------------------------------------------------------------------------
def pot_of(client_order_id: str | None) -> str | None:
    if not client_order_id or not client_order_id.startswith("AUR-"):
        return None
    return "long-term" if client_order_id.startswith("AUR-LT-") else "swing"


def protection_levels(o: dict) -> tuple[float | None, float | None]:
    """(target, stop) of a working sell order as Alpaca lists it: a one-cancels-other or bracket pair shows the target
    as the order's limit price and the stop as a leg; a lone stop order has only a stop price."""
    target = stop = None
    for x in [o, *(o.get("legs") or [])]:
        if x.get("stop_price") and stop is None:
            stop = float(x["stop_price"])
        elif x.get("limit_price") and target is None and str(x.get("type")) == "limit":
            target = float(x["limit_price"])
    return target, stop


def ledgers_from_orders(orders: list[dict], start_cash: dict[str, float]) -> dict[str, dict]:
    """Rebuild each pot from the broker's FILLED quantities and prices (partial fills count for what filled)."""
    pots = {p: {"cash": float(c), "positions": {}, "fills": 0, "realised": 0.0} for p, c in start_cash.items()}
    flat = []
    for o in orders:  # bracket orders: the stop and target legs belong to the parent's pot
        flat.append(o)
        for leg in o.get("legs") or []:
            flat.append(dict(leg, client_order_id=o.get("client_order_id")))
    for o in sorted(flat, key=lambda x: x.get("filled_at") or x.get("submitted_at") or ""):
        pot = pot_of(o.get("client_order_id"))
        q = float(o.get("filled_qty") or 0)
        if pot not in pots or q <= 0:
            continue
        px = float(o.get("filled_avg_price") or 0)
        led = pots[pot]
        pos = led["positions"].setdefault(o["symbol"], {"qty": 0.0, "cost": 0.0})
        if o.get("side") == "buy":
            if pos["qty"] <= 1e-9:  # the position opens with this fill
                pos["opened"] = str(o.get("filled_at") or o.get("submitted_at") or "")[:10]
            pos["qty"] += q
            pos["cost"] += q * px
            led["cash"] -= q * px
        else:
            avg = pos["cost"] / pos["qty"] if pos["qty"] else px
            led["realised"] += q * (px - avg)
            pos["qty"] -= q
            pos["cost"] -= q * avg
            led["cash"] += q * px
        led["fills"] += 1
        if abs(pos["qty"]) < 1e-9:
            del led["positions"][o["symbol"]]
    return pots


def reconcile(pots: dict[str, dict], broker_positions: list[dict]) -> list[str]:
    """Differences between Aurum's pots (summed) and Alpaca's positions. Empty list = they agree."""
    ours: dict[str, float] = {}
    for led in pots.values():
        for s, p in led["positions"].items():
            ours[s] = ours.get(s, 0.0) + p["qty"]
    theirs = {p["symbol"]: float(p.get("qty") or 0) for p in broker_positions}
    out = []
    for s in sorted(set(ours) | set(theirs)):
        a, b = ours.get(s, 0.0), theirs.get(s, 0.0)
        if abs(a - b) > 1e-6:
            out.append(f"{s}: Aurum's pots hold {a:g}, Alpaca shows {b:g}")
    return out
