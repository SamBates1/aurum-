"""The 50/50 long-term vs swing experiment (D-042, D-045): turns each evening's scans into order proposals for the
two pots in the Alpaca PAPER account.

Each evening, for each pot:
  1. Exits first: a held position whose assessment turned to SELL, that fell out of the scanner's top 150 (long-term;
     the scanner saves the top 300 so this can be told apart from "not ranked today"), or (swing) that has been held
     longer than the time stop. Swing entries carry their own stop and target with Alpaca (bracket
     orders), so those exits happen at the broker.
  2. Then entries: the best-ranked candidates whose assessment says BUY and whose plan fits the pot (position cap,
     risk budget, cash, portfolio duplicates), up to the pot's position limit. Long-term entries buy the first third of
     the planned position; later thirds are proposed when the plan's conditions are met.
Proposals are written to research/orders/proposals-latest.json. In manual mode (the default) the owner approves each
one on the Portfolio page; in auto mode the runner submits them through every independent check in broker.py.
Nothing here can reach a real-money account.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pandas as pd

from . import assessment as AS
from . import broker as BR
from . import investplan as IP
from .config import CFG, ROOT

FOLDER = ROOT / "research" / "orders"
LIMITS = {
    "long-term": {"max_positions": 12, "candidates": 40, "exit_rank": 150},
    "swing": {"max_positions": 8, "candidates": 40, "exit_rank": None, "time_stop_days": 28},
}


@dataclass
class Proposal:
    pot: str
    symbol: str
    side: str
    qty: float
    type: str
    limit_price: float | None
    take_profit: float | None
    stop_loss: float | None
    reason: str
    plan: dict = field(default_factory=dict)
    status: str = "proposed"

    def request(self, plan_id: str) -> BR.OrderRequest:
        return BR.OrderRequest(
            self.symbol,
            self.side,
            self.qty,
            type=self.type,
            limit_price=self.limit_price,
            take_profit=self.take_profit,
            stop_loss=self.stop_loss,
            pot=self.pot,
            plan_id=plan_id,
            # swing orders carry a stop and target: "gtc" keeps them working after the first day (a "day" bracket
            # cancels its stop and target at that day's close); unfilled entries are cancelled by the runner
            time_in_force="gtc" if (self.take_profit and self.stop_loss) else "day",
        )


def _rank_list(ranking: pd.DataFrame | None) -> list[str]:
    return [] if ranking is None or ranking.empty else list(ranking.index)


def propose(
    pot: str,
    pot_value: float,
    pot_cash: float,
    held: dict[str, dict],
    ranking: pd.DataFrame | None,
    status: str,
    daily: dict[str, pd.DataFrame],
    usd_per_gbp: float,
    state: dict,
    today: pd.Timestamp,
    regime: dict | None = None,
    fractionable: set[str] | None = None,
    protected: set[str] | None = None,
    open_buys: set[str] | None = None,
    known_levels: dict[str, dict] | None = None,
    notes: list[str] | None = None,
) -> list[Proposal]:
    """Order proposals for one pot. `held`: {symbol: {qty, cost}}; `state`: what was planned per held symbol.

    `open_buys`: symbols with a buy order already working at Alpaca for this pot (they use a position slot).
    `known_levels`: {symbol: {stop, target}} read back from the position's ORIGINAL Alpaca order, used to re-attach
    protection when the saved plan is missing. `notes`: anything the owner must look at is appended here."""
    lim = LIMITS[pot]
    out: list[Proposal] = []
    ranks = _rank_list(ranking)
    pos_rank = {s: i for i, s in enumerate(ranks)}
    # 1. exits
    for s, h in held.items():
        d = daily.get(s)
        if d is None or not len(d):
            continue
        st = state.get(s, {})
        reason = None
        if pot == "long-term":
            a = AS.long_term(
                s,
                d,
                float(ranking.at[s, "score"]) if ranking is not None and s in ranking.index else None,
                status,
                None,
                regime,
                held=True,
            )
            if a.verdict == "SELL":
                reason = f"assessment says SELL ({a.why})"
            elif lim["exit_rank"]:
                # a missing name is "ranked low" only if the saved ranking is long enough to say so (audit F4)
                rank = pos_rank.get(s, len(ranks) if len(ranks) >= lim["exit_rank"] else None)
                if rank is not None and rank >= lim["exit_rank"]:
                    reason = f"fell out of the scanner's top {lim['exit_rank']}"
        else:
            opened = pd.Timestamp(st.get("opened", today))
            if (today - opened).days >= lim["time_stop_days"]:
                reason = f"time stop: held {(today - opened).days} days without reaching the target"
        if reason:
            out.append(Proposal(pot, s, "sell", round(float(h["qty"]), 4), "market", None, None, None, reason))
    # 1b. swing positions with no working stop/target: put the ORIGINAL levels back. They come from the saved plan
    # or from the position's own Alpaca order; they are never recomputed from today's price, which would move the
    # stop down as the price falls (audit F5).
    if pot == "swing":
        for s, h in held.items():
            if s in (protected or set()) or any(p.symbol == s for p in out):
                continue
            st = state.get(s, {})
            lv = (known_levels or {}).get(s) or {}
            stop = st.get("stop") or lv.get("stop")
            target = next((t[1] for t in (st.get("targets") or []) if t[0] == "2R"), None) or lv.get("target")
            qty = float(int(float(h["qty"])))
            if stop and target and qty >= 1:
                out.append(
                    Proposal(
                        pot,
                        s,
                        "sell",
                        qty,
                        "limit",
                        None,
                        round(float(target), 2),
                        round(float(stop), 2),
                        "re-attach stop and target (none working at Alpaca)",
                    )
                )
            elif notes is not None:
                notes.append(
                    f"ACTION NEEDED: {s} has no working stop at Alpaca and its original stop is not on record. "
                    "Set a stop for it by hand in Alpaca."
                )
    # 2. entries and staged top-ups
    # only real exits free a slot: a protective stop/target order (a "sell" with both legs) keeps the position open
    exits = sum(1 for p in out if p.side == "sell" and not (p.take_profit and p.stop_loss))
    waiting = set(open_buys or set()) - set(held)  # buys already working at Alpaca use a slot too (audit F8)
    open_slots = lim["max_positions"] - (len(held) - exits) - len(waiting)
    cash = pot_cash
    for s in ranks[: lim["candidates"]]:
        if s in waiting:
            continue
        if s in held:
            st = state.get(s, {})
            nxt = st.get("tranches_left", [])
            if pot == "long-term" and nxt and s not in {p.symbol for p in out}:
                when, px, q = nxt[0]
                d = daily.get(s)
                last = float(d["Close"].iloc[-1]) if d is not None and len(d) else None
                due = ("pullback" in when and last is not None and last <= px) or (
                    "quarterly" in when and (today - pd.Timestamp(st.get("opened", today))).days >= 90
                )
                if due and q * (last or px) <= cash:
                    out.append(
                        Proposal(
                            pot, s, "buy", q, "limit", round((last or px) * 1.002, 2), None, None, f"staged buy: {when}"
                        )
                    )
                    cash -= q * (last or px)
            continue
        if open_slots <= 0:
            break
        d = daily.get(s)
        if d is None or len(d) < 200:
            continue
        score = float(ranking.at[s, "score"])
        if pot == "long-term":
            a = AS.long_term(s, d, score, status, None, regime)
            setup = None
        else:
            setup = AS.detect_setup(d)
            a = AS.swing(s, d, score, status, setup, [], regime)
        if a.verdict != "BUY":
            continue
        plan = IP.build(
            s, d, pot, "BUY", pot_value, usd_per_gbp, setup=setup, fractionable=s in (fractionable or set())
        )
        if plan.action != "BUY" or plan.shares <= 0:
            continue
        qty = plan.tranches[0][2] if (pot == "long-term" and plan.tranches) else plan.shares
        # Alpaca accepts bracket orders (swing: stop + target attached) only for whole shares
        whole = pot == "swing" or s not in (fractionable or set())
        qty = float(int(qty)) if whole else round(qty, 4)
        cost = qty * plan.price
        if qty <= 0 or cost > cash:
            continue
        target = next((t[1] for t in plan.targets if t[0] == "2R"), None)
        out.append(
            Proposal(
                pot,
                s,
                "buy",
                qty,
                "limit",
                plan.entry_zone[1],
                take_profit=target if pot == "swing" else None,
                stop_loss=plan.stop if pot == "swing" else None,
                reason=f"{a.verdict} ({status}): {a.why}",
                plan={
                    "stop": plan.stop,
                    "targets": plan.targets,
                    "entry_zone": plan.entry_zone,
                    "tranches": plan.tranches,
                    "max_loss_usd": plan.max_loss_usd,
                    "reasons": plan.reasons,
                },
            )
        )
        cash -= cost
        open_slots -= 1
    return out


def save(proposals: list[Proposal], asof: str, notes: list[str], folder: Path | None = None) -> Path:
    folder = folder or FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    data = {
        "asof": asof,
        "created": str(pd.Timestamp.now(tz="UTC").floor("s")),
        "notes": notes,
        "mode": BR.settings()["mode"],
        "proposals": [asdict(p) for p in proposals],
    }
    path = folder / "proposals-latest.json"
    path.write_text(json.dumps(data, indent=1, default=str))
    (folder / f"proposals-{asof}.json").write_text(json.dumps(data, indent=1, default=str))
    return path


def load(folder: Path | None = None) -> dict:
    p = (folder or FOLDER) / "proposals-latest.json"
    return json.loads(p.read_text()) if p.is_file() else {}


def plan_id(asof: str, p: dict) -> str:
    return f"{asof}:{p['pot']}:{p['symbol']}:{p['side']}"


def load_state(folder: Path | None = None) -> dict:
    p = (folder or FOLDER) / "state.json"
    return json.loads(p.read_text()) if p.is_file() else {"long-term": {}, "swing": {}}


def update_state(
    state: dict, pots: dict[str, dict], proposals_done: list[dict], today, known_levels: dict | None = None
) -> dict:
    """Keep the plan (opened date, stop, targets, staged buys left) for every position actually held.

    A plan is parked under "_pending" when its buy is sent and moves to the pot when the position first APPEARS, so
    an order that fills a day or more later keeps its plan (audit F3). A held position with no plan at all still gets
    an opened date (from its first fill), so its time stop works, and its stop and target from the original Alpaca
    order when those are known."""
    day = str(pd.Timestamp(today).date())
    pend_all = state.setdefault("_pending", {})
    for pot, led in pots.items():
        st = state.setdefault(pot, {})
        pend = pend_all.setdefault(pot, {})
        for p in proposals_done:
            if p["pot"] != pot or p["side"] != "buy":
                continue
            plan, sym = p.get("plan") or {}, p["symbol"]
            if plan.get("stop") is not None:  # a new entry (staged top-ups carry no stop)
                if sym not in st:
                    pend[sym] = {
                        "sent": day,
                        "stop": plan.get("stop"),
                        "targets": plan.get("targets"),
                        "tranches_left": (plan.get("tranches") or [])[1:],
                    }
            elif sym in st and st[sym].get("tranches_left"):
                st[sym]["tranches_left"] = st[sym]["tranches_left"][1:]
        for sym, pos in led["positions"].items():
            if sym in st:
                continue
            src = pend.pop(sym, None)
            lv = (known_levels or {}).get(sym) or {}
            if src is None and pot == "swing" and lv.get("stop"):
                src = {"stop": lv["stop"], "targets": [["2R", lv["target"], 2.0]] if lv.get("target") else []}
            src = dict(src or {})
            src.pop("sent", None)
            st[sym] = {"opened": pos.get("opened") or day, "tranches_left": [], **src}
        for sym in list(st):
            if sym not in led["positions"]:
                del st[sym]
        for sym in list(pend):  # a buy that never filled: forget its plan after ten days
            if (pd.Timestamp(day) - pd.Timestamp(pend[sym].get("sent", day))).days > 10:
                del pend[sym]
    return state


def write_orders_log(orders: list[dict], folder: Path | None = None) -> Path:
    """The lasting record of what went to Alpaca (audit G3): one row per order and per stop/target leg, copied from
    Alpaca's own history each evening and committed with the rest of research/orders/."""
    rows = []
    for o in orders:
        for x, parent in [(o, "")] + [(leg, o.get("id") or "") for leg in (o.get("legs") or [])]:
            rows.append(
                {
                    "submitted_at": x.get("submitted_at"),
                    "symbol": x.get("symbol"),
                    "side": x.get("side"),
                    "qty": x.get("qty"),
                    "type": x.get("type"),
                    "order_class": x.get("order_class"),
                    "limit_price": x.get("limit_price"),
                    "stop_price": x.get("stop_price"),
                    "time_in_force": x.get("time_in_force"),
                    "status": x.get("status"),
                    "filled_qty": x.get("filled_qty"),
                    "filled_avg_price": x.get("filled_avg_price"),
                    "filled_at": x.get("filled_at"),
                    "pot": BR.pot_of(o.get("client_order_id")) or "not Aurum",
                    "client_order_id": x.get("client_order_id"),
                    "id": x.get("id"),
                    "parent_id": parent,
                }
            )
    folder = folder or FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "orders-log.csv"
    cols = list(rows[0]) if rows else ["submitted_at", "symbol", "side", "status"]
    pd.DataFrame(rows, columns=cols).sort_values("submitted_at", na_position="last").to_csv(path, index=False)
    return path


def levels_from_orders(orders: list[dict]) -> dict[str, dict]:
    """{symbol: {stop, target}} for swing positions, from the newest Alpaca order that carried both: a bracket buy's
    legs, or a re-attached stop/target pair."""
    out: dict[str, tuple[str, dict]] = {}
    for o in orders:
        if BR.pot_of(o.get("client_order_id")) != "swing":
            continue
        src = {"legs": o.get("legs")} if o.get("side") == "buy" else o
        target, stop = BR.protection_levels(src)
        when = str(o.get("submitted_at") or "")
        if stop and (o["symbol"] not in out or when > out[o["symbol"]][0]):
            out[o["symbol"]] = (when, {"stop": stop, "target": target})
    return {k: v[1] for k, v in out.items()}


def approve(p: dict, asof: str, broker, latest_trade=None, market_open: bool | None = None) -> str:
    """Send one approved proposal through every broker check and say, in words, what happened. Never raises: a failed
    price lookup or a blocked order becomes a message for the owner (this is the Approve button's whole job)."""
    req = Proposal(**{k: p[k] for k in Proposal.__dataclass_fields__}).request(plan_id(asof, p))
    # price for the safety checks: the latest trade if there is one, otherwise the close the proposal was prepared
    # from, dated at that close (so the freshness check still applies honestly while the market is open)
    price, when, src = None, None, ""
    try:
        lt = latest_trade(p["symbol"]) if latest_trade else {}
        if lt.get("price") and lt["price"] == lt["price"] and lt.get("time"):
            price, when, src = float(lt["price"]), lt["time"], "latest IEX trade"
    except Exception as e:
        src = f"latest price unavailable ({type(e).__name__}); "
    if price is None:
        ref = (p.get("plan") or {}).get("reference_price") or p.get("limit_price")
        if not ref:
            return src + "blocked: no price to check the order against"
        price, when = float(ref), pd.Timestamp(f"{asof} 21:00", tz="UTC")
        src += f"used the {asof} close"
    try:
        send = broker.submit_exit if (p["side"] == "sell" and p["type"] == "market") else broker.submit
        res = send(req, float(price), when, approved=True, market_open=market_open)
        return f"sent to Alpaca (paper), status {res.get('status', '?')} · price check: {src}"
    except BR.OrderBlocked as e:
        return f"blocked: {e} · price check: {src}"
    except BR.BrokerError as e:
        return f"failed: {e}"
    except Exception as e:
        return f"failed: {type(e).__name__}: {str(e)[:200]}"


def settings(cfg: dict = CFG) -> dict:
    return cfg.get("experiment", {}) or {}
