"""The 50/50 long-term vs swing experiment (D-042, D-045): turns each evening's scans into order proposals for the
two pots in the Alpaca PAPER account.

Each evening, for each pot:
  1. Exits first: a held position whose assessment turned to SELL, that fell out of the scanner's top ranks, or (swing)
     that has been held longer than the time stop. Swing entries carry their own stop and target with Alpaca (bracket
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
            time_in_force="day",
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
) -> list[Proposal]:
    """Order proposals for one pot. `held`: {symbol: {qty, cost}}; `state`: what was planned per held symbol."""
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
            elif lim["exit_rank"] and pos_rank.get(s, 10**6) >= lim["exit_rank"]:
                reason = f"fell out of the scanner's top {lim['exit_rank']}"
        else:
            opened = pd.Timestamp(st.get("opened", today))
            if (today - opened).days >= lim["time_stop_days"]:
                reason = f"time stop: held {(today - opened).days} days without reaching the target"
        if reason:
            out.append(Proposal(pot, s, "sell", round(float(h["qty"]), 4), "market", None, None, None, reason))
    # 2. entries and staged top-ups
    open_slots = lim["max_positions"] - (len(held) - sum(1 for p in out if p.side == "sell"))
    cash = pot_cash
    for s in ranks[: lim["candidates"]]:
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


def update_state(state: dict, pots: dict[str, dict], proposals_done: list[dict], today) -> dict:
    """Keep plan details for positions that are actually held (after fills), drop the rest."""
    for pot, led in pots.items():
        st = state.setdefault(pot, {})
        for p in proposals_done:
            if p["pot"] == pot and p["side"] == "buy" and p.get("plan"):
                tr = p["plan"].get("tranches") or []
                st.setdefault(
                    p["symbol"],
                    {
                        "opened": str(pd.Timestamp(today).date()),
                        "stop": p["plan"].get("stop"),
                        "targets": p["plan"].get("targets"),
                        "tranches_left": tr[1:],
                    },
                )
            elif p["pot"] == pot and p["side"] == "buy" and p["symbol"] in st and st[p["symbol"]].get("tranches_left"):
                st[p["symbol"]]["tranches_left"] = st[p["symbol"]]["tranches_left"][1:]
        for s in list(st):
            if s not in led["positions"]:
                del st[s]
    return state


def settings(cfg: dict = CFG) -> dict:
    return cfg.get("experiment", {}) or {}
