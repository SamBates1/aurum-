"""Local paper-trading portfolio: simulated money in a JSON ledger.

It applies the same rules as the backtest (strategy.py):
  * Long-only. BUY enters if flat; BUY while already long does nothing
    (no averaging in, so position size and stop are fixed at entry).
  * SELL exits. HOLD does nothing.
  * Size = equity * sleeve weight * min(1, target_vol / volatility).
  * Stop = entry - stop_atr_mult * ATR. Stops only ever tighten. After a stop,
    the ticker waits for the signal to leave BUY before it can re-enter.
  * Costs are charged at the per-ticker rate from config.yaml.

Fills are simulated at the latest price the bot saw. Real fills differ
(spreads move, orders queue, prices gap), so paper results are an
approximation of live trading, not a reproduction of it.
This module never sends orders anywhere.
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

from . import safety
from . import strategy as S
from .config import CFG, ROOT, all_tickers, cost_bps


def _valid_price(p) -> bool:
    return isinstance(p, (int, float)) and math.isfinite(p) and p > 0


class PaperPortfolio:
    def __init__(self, path: str | Path | None = None, cfg: dict = CFG):
        self.cfg = cfg
        self.path = Path(path or ROOT / cfg["paper"]["ledger_path"])
        self.state = json.loads(self.path.read_text()) if self.path.exists() else self._fresh()
        self.state.setdefault("stopped_out", {})
        self.state.setdefault("fees", 0.0)
        self.state.setdefault("realised_pnl", 0.0)
        for p in self.state["positions"].values():  # migrate ledgers written by v0.1
            p.setdefault("entry_price", p.get("avg_price", 0.0))
            p.setdefault("entry_fee", 0.0)
            p.setdefault("last_price", p["entry_price"])

    def _fresh(self) -> dict:
        return {
            "cash": float(self.cfg["paper"]["starting_cash"]),
            "positions": {},
            "trades": [],
            "history": [],
            "stopped_out": {},
            "fees": 0.0,
            "realised_pnl": 0.0,
        }

    # --- persistence -------------------------------------------------------
    def save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, indent=2, default=str))
        tmp.replace(self.path)  # atomic: a crash mid-write can't corrupt the ledger

    def reset(self):
        self.state = self._fresh()
        self.save()

    # --- valuation ---------------------------------------------------------
    def mark_prices(self, prices: dict[str, float]):
        for t, p in self.state["positions"].items():
            if _valid_price(prices.get(t)):
                p["last_price"] = float(prices[t])

    def equity(self, prices: dict[str, float] | None = None) -> float:
        if prices:
            self.mark_prices(prices)
        return self.state["cash"] + sum(p["qty"] * p["last_price"] for p in self.state["positions"].values())

    def unrealised_pnl(self) -> float:
        return sum(
            p["qty"] * (p["last_price"] - p["entry_price"]) - p["entry_fee"] for p in self.state["positions"].values()
        )

    def mark(self, prices: dict[str, float]):
        self.state["history"].append(
            {"time": datetime.now().isoformat(timespec="seconds"), "equity": round(self.equity(prices), 2)}
        )

    # --- trading -----------------------------------------------------------
    def _log(self, ticker, side, qty, price, fee, reason, pnl=None):
        self.state["trades"].append(
            {
                "time": datetime.now().isoformat(timespec="seconds"),
                "ticker": ticker,
                "side": side,
                "qty": round(qty, 6),
                "price": round(price, 4),
                "fee": round(fee, 4),
                "pnl": None if pnl is None else round(pnl, 2),
                "reason": reason,
            }
        )

    def _close(self, ticker: str, price: float, reason: str) -> str:
        pos = self.state["positions"].pop(ticker)
        proceeds = pos["qty"] * price
        fee = proceeds * cost_bps(ticker, self.cfg) / 1e4
        pnl = proceeds - fee - pos["qty"] * pos["entry_price"] - pos["entry_fee"]
        self.state["cash"] += proceeds - fee
        self.state["fees"] += fee
        self.state["realised_pnl"] += pnl
        self._log(ticker, "SELL", pos["qty"], price, fee, reason, pnl)
        kind = "STOP" if reason.startswith("stop") else "SELL"
        return f"{kind} {ticker} {pos['qty']:.4f} @ {price:.2f} (P&L {pnl:+.2f})"

    def act(self, d, prices: dict[str, float]) -> str | None:
        """Execute a pipeline.Decision in whichever mode produced it."""
        if d.target_weight is not None:
            if not getattr(d, "rebalance_day", True):
                return None  # weekly rebalancing: no order on this day (D-022)
            bars = getattr(d, "bars", None)
            last_close = float(bars["Close"].iloc[-1]) if bars is not None and len(bars) else None
            return self.rebalance(
                d.ticker, d.target_weight, d.last_price, prices, d.tradeable, d=d, last_close=last_close
            )
        return self.apply(d.ticker, d.decision, d.last_price, d.ann_vol, d.atr, prices, d.tradeable)

    def rebalance(
        self,
        ticker: str,
        target_weight: float,
        price: float,
        prices: dict[str, float],
        tradeable: bool = True,
        d=None,
        last_close: float | None = None,
    ) -> str | None:
        """vol_hold mode: move the holding to target_weight x this ticker's sleeve of total equity,
        trading only if the current weight differs by more than the rebalance band (EXP-014 rule).
        No stop-loss in this mode, matching what was tested."""
        scfg = self.cfg["strategy"]
        if not _valid_price(price):
            return f"SKIP {ticker}: invalid price {price!r}"
        equity = self.equity(prices)
        sleeve = equity * S.sleeve_weight(len(all_tickers(self.cfg)), scfg["max_position_pct"])
        pos = self.state["positions"].get(ticker)
        held = pos["qty"] * price if pos else 0.0
        cur_w = held / sleeve if sleeve > 0 else 0.0
        w = max(0.0, min(1.0, float(target_weight)))
        if abs(w - cur_w) <= scfg.get("rebalance_band", 0.05) and (w == 0) == (cur_w == 0):
            return None
        c = cost_bps(ticker, self.cfg) / 1e4
        delta = (w - cur_w) * sleeve
        side = "BUY" if delta > 0 else "SELL"
        checks = safety.pre_trade_checks(
            ticker=ticker,
            side=side,
            target_weight=float(target_weight),
            price=price,
            last_close=last_close,
            tradeable=tradeable,
            state=self.state,
            cfg=self.cfg,
            cash_needed=min(delta, self.state["cash"]) if delta > 0 else 0.0,
        )
        planned = {
            "side": side,
            "notional": round(abs(delta), 2),
            "price": price,
            "from_weight": round(cur_w, 4),
            "to_weight": round(w, 4),
        }
        ok = safety.passed(checks)
        why = "; ".join(f"{x['check']}: {x['detail']}" for x in checks if not x["passed"])
        # a blocked order is logged once per day and reason, so a 60-second loop doesn't flood the log
        seen = self.state.setdefault("blocked_logged", {})
        key = f"{datetime.now().date()}|{ticker}|{','.join(x['check'] for x in checks if not x['passed'])}"
        if d is not None and (ok or key not in seen):
            safety.write_record(
                safety.decision_record(d, current_weight=cur_w, planned=planned, checks=checks, cfg=self.cfg), self.cfg
            )
            if not ok:
                seen[key] = True
                for k in sorted(seen)[:-50]:
                    seen.pop(k)
        if not ok:
            return f"BLOCKED {side} {ticker}: {why}"
        safety.record_order(self.state, ticker, f"{side} {cur_w:.0%}->{w:.0%}")
        if delta > 0:
            delta = min(delta, self.state["cash"]) / (1 + c)
            qty, fee = delta / price, delta * c
            self.state["cash"] -= delta + fee
            self.state["fees"] += fee
            if pos:
                pos["entry_price"] = (pos["entry_price"] * pos["qty"] + price * qty) / (pos["qty"] + qty)
                pos["entry_fee"] += fee
                pos["qty"] += qty
                pos["last_price"] = float(price)
            else:
                self.state["positions"][ticker] = {
                    "qty": qty,
                    "entry_price": float(price),
                    "entry_fee": fee,
                    "last_price": float(price),
                    "stop": 0.0,
                    "opened": datetime.now().isoformat(timespec="seconds"),
                }
            self._log(ticker, "BUY", qty, price, fee, f"rebalance {cur_w:.0%} -> {w:.0%}")
            return f"BUY {ticker} {qty:.4f} @ {price:.2f} (weight {cur_w:.0%} -> {w:.0%})"
        qty = min(-delta / price, pos["qty"])
        proceeds = qty * price
        fee = proceeds * c
        pnl = proceeds - fee - qty * pos["entry_price"] - pos["entry_fee"] * qty / pos["qty"]
        pos["entry_fee"] -= pos["entry_fee"] * qty / pos["qty"]
        pos["qty"] -= qty
        pos["last_price"] = float(price)
        self.state["cash"] += proceeds - fee
        self.state["fees"] += fee
        self.state["realised_pnl"] += pnl
        if pos["qty"] <= 1e-12:
            del self.state["positions"][ticker]
        self._log(ticker, "SELL", qty, price, fee, f"rebalance {cur_w:.0%} -> {w:.0%}", pnl)
        return f"SELL {ticker} {qty:.4f} @ {price:.2f} (weight {cur_w:.0%} -> {w:.0%})"

    def apply(
        self,
        ticker: str,
        decision: str,
        price: float,
        ann_vol: float,
        atr_value: float,
        prices: dict[str, float],
        tradeable: bool = True,
    ) -> str | None:
        """Act on one signal. Returns a description of any trade made."""
        scfg = self.cfg["strategy"]
        if not tradeable:
            return None
        if not _valid_price(price):
            return f"SKIP {ticker}: invalid price {price!r}"
        pos = self.state["positions"].get(ticker)
        if pos:
            pos["last_price"] = float(price)
            if price <= pos["stop"]:
                self.state["stopped_out"][ticker] = True
                return self._close(ticker, price, f"stop-loss hit at {pos['stop']:.2f}")
            if decision == S.SELL:
                return self._close(ticker, price, "signal SELL")
            return None  # BUY while long: no averaging in, so size and stop stay as set at entry

        # flat
        if decision != S.BUY:
            self.state["stopped_out"].pop(ticker, None)  # signal has reset
            return None
        if self.state["stopped_out"].get(ticker):
            return None  # wait for a fresh signal after a stop
        equity = self.equity(prices)
        weight = S.sleeve_weight(len(all_tickers(self.cfg)), scfg["max_position_pct"])
        exposure = S.target_exposure(ann_vol, scfg["target_vol"])
        c = cost_bps(ticker, self.cfg) / 1e4
        notional = min(equity * weight * exposure, self.state["cash"] / (1 + c))
        if notional <= 0.005 * equity:
            return None
        qty, fee = notional / price, notional * c
        self.state["cash"] -= notional + fee
        self.state["fees"] += fee
        stop = S.initial_stop(price, atr_value, scfg["stop_atr_mult"])
        self.state["positions"][ticker] = {
            "qty": qty,
            "entry_price": float(price),
            "entry_fee": fee,
            "last_price": float(price),
            "stop": stop,
            "opened": datetime.now().isoformat(timespec="seconds"),
        }
        self._log(ticker, "BUY", qty, price, fee, "signal BUY")
        return f"BUY {ticker} {qty:.4f} @ {price:.2f} (stop {stop:.2f})"
