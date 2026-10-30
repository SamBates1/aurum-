"""Alpaca PAPER trading integration (platform phase 7). Built and tested, but switched OFF until the owner says so.

Safety design (D-042):
  * The only trading address in this module is Alpaca's paper endpoint. There is no setting that changes it, and
    `PaperBroker` refuses to start if the address is anything else. Real-money trading is not implemented.
  * Orders are blocked unless `paper_orders.enabled` is true in config.yaml (false by default), and each order needs
    an approval record (manual mode, the default). An optional auto mode must be enabled separately.
  * Before every order, independent checks run (not the AI, not the strategy): pause switch, enabled flag, approval,
    buying power, position and order-size limits, data freshness, and duplicate prevention (a deterministic client
    order id plus a check for an open order on the same symbol and side).
  * Submitting is not filling: order status is read back and reconciled; partial fills, rejections and cancellations
    are recorded as they are.
Every request and result is appended to research/orders/audit.jsonl (no keys are ever written).
"""

from __future__ import annotations

import hashlib
import json
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
        if self.take_profit and self.stop_loss:
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
        return (self.folder / "PAUSE").is_file()

    def pause(self, reason: str) -> None:
        (self.folder / "PAUSE").write_text(f"{pd.Timestamp.now(tz='UTC')}: {reason}\n")
        self._audit({"event": "pause", "reason": reason})

    def resume(self) -> None:
        (self.folder / "PAUSE").unlink(missing_ok=True)
        self._audit({"event": "resume"})

    def check(
        self, req: OrderRequest, price: float, price_time, approved: bool, market_open: bool | None = None
    ) -> CheckResult:
        r = []
        if self.paused():
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
        if value > self.cfg["max_order_usd"]:
            r.append(f"order value ${value:,.0f} above the ${self.cfg['max_order_usd']:,.0f} limit")
        try:
            acct = self.account()
            if acct.get("trading_blocked") or acct.get("account_blocked"):
                r.append("Alpaca reports the account as blocked")
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
                    r.append(f"an open {req.side} order for {req.symbol} already exists")
        except BrokerError as e:
            r.append(f"could not check the account: {e}")
        return CheckResult(not r, r)

    # ---- orders ---------------------------------------------------------------------------------------------
    def submit(
        self, req: OrderRequest, price: float, price_time, approved: bool, market_open: bool | None = None
    ) -> dict:
        chk = self.check(req, price, price_time, approved, market_open)
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
        res = dict(self.t("POST", "/v2/orders", req.payload()))
        self._audit(
            {"event": "submitted", "client_order_id": req.client_id(), "id": res.get("id"), "status": res.get("status")}
        )
        return res

    def cancel(self, order_id: str) -> None:
        self.t("DELETE", f"/v2/orders/{order_id}", None)
        self._audit({"event": "cancel", "id": order_id})

    def cancel_all_and_pause(self, reason: str) -> None:
        """Emergency stop: pause first (nothing new goes out), then cancel every open order."""
        self.pause(reason)
        self.t("DELETE", "/v2/orders", None)
        self._audit({"event": "cancel_all"})

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
