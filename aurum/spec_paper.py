"""Paper trading of approved strategy definitions (Option 3, D-034: 70/30 main + risk-capped shadow).

Simulated money only. Nothing here can place a real order: there is no broker connection in this module.

Each strategy runs in its own JSON ledger (same format as aurum/paper.py, so the existing tools can read it) and
follows the backtest's timing exactly:

  1 after the US close, on completed daily bars, the SAME engine as the backtest (engine.compile_targets) gives the
    day's targets; if it is a rebalance day they are stored as a pending decision;
  2 at the first loop after the next session opens (09:30 New York or later), the pending targets are reviewed by the
    independent risk engine (aurum/risk.py), every order passes the safety checks (aurum/safety.py), and the orders
    fill at the latest price seen (Yahoo, about 15 minutes delayed), sells first, buys limited to the cash available;
  3 every decision, veto and order is written to the decision log with the strategy version (spec hash).

The paper trader refuses to run a strategy unless every eligibility gate passes (aurum/gates.py).
"""

from __future__ import annotations

from datetime import datetime, time, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import engine as E
from . import risk, safety
from . import spec as SP
from .config import CFG, ROOT
from .paper import PaperPortfolio

NY = "America/New_York"


def ny_now(now: datetime | None = None) -> pd.Timestamp:
    return pd.Timestamp(now or datetime.now(timezone.utc)).tz_convert(NY)


def session_open_after(decided: str, now: datetime | None = None) -> bool:
    """True once the next weekday session after the decision day has opened (09:30 New York)."""
    t = ny_now(now)
    d = pd.Timestamp(decided).date()
    return t.date() > d and t.weekday() < 5 and t.time() >= time(9, 30)


class SpecPaperTrader:
    def __init__(self, spec: dict, role: str, ledger: str | Path, cfg: dict = CFG):
        self.spec = SP.validate(spec)
        self.hash = SP.spec_hash(self.spec)
        self.role = role
        self.cfg = cfg
        self.book = PaperPortfolio(Path(ledger) if Path(ledger).is_absolute() else ROOT / ledger, cfg)
        st = self.book.state
        if st.get("spec_hash") and st["spec_hash"] != self.hash:
            st.setdefault("notes", []).append(
                f"{datetime.now():%Y-%m-%d %H:%M} strategy changed from {st['spec_hash']} to {self.hash}; ledger kept"
            )
        st["spec_hash"], st["strategy_id"], st["role"] = self.hash, self.spec["id"], role
        st.setdefault("pending", None)
        st.setdefault("last_decided", None)
        st.setdefault("peak_equity", float(st["cash"]))

    # ------------------------------------------------------------------------------------------------------------
    def cost(self, t: str) -> float:
        return self.spec["execution"]["costs_bps"][t] * self.spec["execution"]["cost_mult"] / 1e4

    def weights(self, prices: dict[str, float]) -> tuple[dict[str, float], float]:
        eq = self.book.equity(prices)
        pos = self.book.state["positions"]
        return {
            t: (pos[t]["qty"] * pos[t]["last_price"] / eq if t in pos and eq > 0 else 0.0)
            for t in self.spec["universe"]
        }, eq

    def decide(self, daily: dict[str, pd.DataFrame]) -> dict | None:
        """Step 1: after the close, on completed bars. Returns the pending decision if one was made."""
        comp = E.compile_targets(self.spec, daily)
        d = comp.index[-1]
        st = self.book.state
        if st["last_decided"] == str(d.date()):
            return None
        st["last_decided"] = str(d.date())
        # a brand-new account invests at its first decision, just as every backtest's first day is a rebalance day
        first = not st["trades"] and not st["positions"] and not st.get("pending")
        if not (bool(comp.rebalance.iloc[-1]) or first):
            return None
        tgt = {t: float(comp.raw_target[t].iloc[-1]) for t in self.spec["universe"]}
        why = E.explain_day(_Shim(self.spec, comp), d)
        st["pending"] = {"decided": str(d.date()), "targets": tgt, "signals": why["signals"]}
        safety.write_record(
            {
                "time": datetime.now().isoformat(timespec="seconds"),
                "kind": "decision",
                "strategy": self.spec["id"],
                "role": self.role,
                "spec_hash": self.hash,
                "data_as_of": str(d.date()),
                "targets": tgt,
                "signals": why["signals"],
                "assets": why["assets"],
                "fills": f"at the first price after the next session opens ({self.spec['execution']['fill']} in the "
                "backtest)",
            },
            self.cfg,
        )
        return st["pending"]

    def execute(
        self, live: dict[str, float], closes: dict[str, pd.Series], data_age_days: float, now: datetime | None = None
    ) -> list[str]:
        """Step 2: after the next open, trade toward the pending targets."""
        st = self.book.state
        p = st.get("pending")
        if not p or not session_open_after(p["decided"], now):
            return []
        today = str(ny_now(now).date())
        if p.get("last_attempt") == today:
            return []  # a blocked decision is retried once per day, not every loop
        p["last_attempt"] = today
        cur, eq = self.weights(live)
        st["peak_equity"] = max(float(st.get("peak_equity", eq)), eq)
        rev = risk.review(
            p["targets"],
            cur,
            equity=eq,
            peak_equity=st["peak_equity"],
            closes=closes,
            data_age_days=data_age_days,
            cfg=self.cfg,
        )
        band = self.spec["schedule"]["band"]
        orders = []
        for t in self.spec["universe"]:
            w, c = rev.approved.get(t, 0.0), cur.get(t, 0.0)
            if abs(w - c) > band or ((w == 0) != (c == 0) and abs(w - c) > 1e-9):
                orders.append((t, w, c))
        out, blocked = [], False
        min_val = risk.limits(self.cfg)["min_order_value"]
        for t, w, c in sorted(orders, key=lambda x: x[1] - x[2]):  # sells first
            price = live.get(t)
            side = "BUY" if w > c else "SELL"
            notional = abs(w - c) * eq
            if notional < min_val:
                continue
            last_close = float(closes[t].iloc[-1]) if t in closes and len(closes[t]) else None
            checks = safety.pre_trade_checks(
                ticker=t,
                side=side,
                target_weight=w,
                price=price if price is not None else float("nan"),
                last_close=last_close,
                tradeable=data_age_days <= safety_age(self.cfg),
                state=st,
                cfg=self.cfg,
                cash_needed=min(notional, st["cash"]) if side == "BUY" else 0.0,
            )
            ok = safety.passed(checks)
            rec = {
                "time": datetime.now().isoformat(timespec="seconds"),
                "kind": "order",
                "strategy": self.spec["id"],
                "role": self.role,
                "spec_hash": self.hash,
                "decided_on": p["decided"],
                "planned_order": {
                    "side": side,
                    "ticker": t,
                    "from_weight": round(c, 4),
                    "to_weight": round(w, 4),
                    "notional": round(notional, 2),
                    "price": price,
                },
                "risk_vetoes": rev.vetoes,
                "checks": checks,
                "allowed": ok,
            }
            safety.write_record(rec, self.cfg)
            if not ok:
                blocked = True
                out.append(
                    f"BLOCKED {side} {t}: "
                    + "; ".join(f"{x['check']}: {x['detail']}" for x in checks if not x["passed"])
                )
                continue
            safety.record_order(st, t, f"{side} {c:.0%}->{w:.0%}")
            out.append(
                self._fill(
                    t,
                    side,
                    notional,
                    float(price),
                    f"{self.spec['id']} rebalance {c:.0%} -> {w:.0%} (decided {p['decided']})",
                )
            )
        for v in rev.vetoes:
            out.append(f"RISK {v['rule']} {v['ticker']}: {v['detail']} ({v['action']})")
        if blocked or rev.halted:
            # keep the decision and retry on the next trading day (until a newer decision replaces it); EXP-044
            # found the strategy robust to one to five days' execution delay
            out.append(f"Decision of {p['decided']} kept: blocked orders will be retried tomorrow")
        else:
            st["pending"] = None
        st["last_executed"] = datetime.now().isoformat(timespec="seconds")
        return out

    def _fill(self, t: str, side: str, notional: float, price: float, reason: str) -> str:
        st, c = self.book.state, self.cost(t)
        pos = st["positions"].get(t)
        if side == "BUY":
            amt = min(notional, st["cash"]) / (1 + c)  # fee comes out of the planned purchase, as in the backtest
            qty, fee = amt / price, amt * c
            st["cash"] -= amt + fee
            st["fees"] += fee
            if pos:
                pos["entry_price"] = (pos["entry_price"] * pos["qty"] + price * qty) / (pos["qty"] + qty)
                pos["entry_fee"] += fee
                pos["qty"] += qty
                pos["last_price"] = price
            else:
                st["positions"][t] = {
                    "qty": qty,
                    "entry_price": price,
                    "entry_fee": fee,
                    "last_price": price,
                    "stop": 0.0,
                    "opened": datetime.now().isoformat(timespec="seconds"),
                }
            self.book._log(t, "BUY", qty, price, fee, reason)
            return f"BUY {t} ${amt:,.2f} ({qty:.4f} @ {price:.2f})"
        qty = min(notional / price, pos["qty"]) if pos else 0.0
        if qty <= 0:
            return f"SKIP SELL {t}: nothing held"
        proceeds = qty * price
        fee = proceeds * c
        pnl = proceeds - fee - qty * pos["entry_price"] - pos["entry_fee"] * qty / pos["qty"]
        pos["entry_fee"] -= pos["entry_fee"] * qty / pos["qty"]
        pos["qty"] -= qty
        pos["last_price"] = price
        st["cash"] += proceeds - fee
        st["fees"] += fee
        st["realised_pnl"] += pnl
        if pos["qty"] <= 1e-12:
            del st["positions"][t]
        self.book._log(t, "SELL", qty, price, fee, reason, pnl)
        return f"SELL {t} ${proceeds:,.2f} ({qty:.4f} @ {price:.2f})"

    def save(self, live: dict[str, float] | None = None):
        if live:
            self.book.mark(live)
            self.book.state["peak_equity"] = max(self.book.state.get("peak_equity", 0.0), self.book.equity(live))
        self.book.save()


class _Shim:
    """Just enough of a StrategyRun for engine.explain_day before any trade exists."""

    def __init__(self, spec, comp):
        self.spec, self.compiled = spec, comp
        self.result = type("R", (), {"weights": pd.DataFrame(np.nan, index=comp.index, columns=spec["universe"])})()
        self.trades = pd.DataFrame(columns=["decided"])


def safety_age(cfg: dict) -> float:
    return float(cfg["data"].get("max_stale_days", 4))


def configured(cfg: dict = CFG) -> list[dict]:
    """The strategies listed under paper.strategies, loaded and validated."""
    out = []
    for item in (cfg.get("paper", {}) or {}).get("strategies", []) or []:
        s = SP.load(ROOT / item["file"])
        out.append({"spec": s, "role": item.get("role", "shadow"), "ledger": item["ledger"]})
    return out
