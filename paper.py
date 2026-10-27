"""Local paper-trading portfolio: simulated money, stored in a JSON ledger.

Risk rules:
  * Long-only. BUY opens/tops up, SELL closes, HOLD does nothing.
  * Position size = max_position_pct scaled down by volatility
    (target_vol / asset_vol), so a volatile miner gets less money than GLD.
  * Every position has a stop-loss `stop_atr_mult` ATRs below entry.
"""
import json
from datetime import datetime
from pathlib import Path

from .config import CFG, ROOT


class PaperPortfolio:
    def __init__(self, path: str | Path | None = None, cfg: dict = CFG):
        self.cfg = cfg["paper"]
        self.path = Path(path or ROOT / self.cfg["ledger_path"])
        if self.path.exists():
            self.state = json.loads(self.path.read_text())
        else:
            self.state = {"cash": float(self.cfg["starting_cash"]), "positions": {}, "trades": [], "history": []}

    # --- persistence -------------------------------------------------------
    def save(self):
        self.path.write_text(json.dumps(self.state, indent=2, default=str))

    def reset(self):
        self.state = {"cash": float(self.cfg["starting_cash"]), "positions": {}, "trades": [], "history": []}
        self.save()

    # --- valuation ---------------------------------------------------------
    def equity(self, prices: dict[str, float]) -> float:
        pos = self.state["positions"]
        return self.state["cash"] + sum(p["qty"] * prices.get(t, p["avg_price"]) for t, p in pos.items())

    def mark(self, prices: dict[str, float]):
        self.state["history"].append({"time": datetime.now().isoformat(timespec="seconds"),
                                      "equity": round(self.equity(prices), 2)})

    # --- trading -----------------------------------------------------------
    def _trade(self, ticker, side, qty, price, reason):
        cost = qty * price
        if side == "BUY":
            self.state["cash"] -= cost
        else:
            self.state["cash"] += cost
        self.state["trades"].append({"time": datetime.now().isoformat(timespec="seconds"), "ticker": ticker,
                                     "side": side, "qty": round(qty, 4), "price": round(price, 4), "reason": reason})

    def target_weight(self, ann_vol: float) -> float:
        if not ann_vol or ann_vol <= 0:
            return self.cfg["max_position_pct"]
        return min(self.cfg["max_position_pct"], self.cfg["max_position_pct"] * self.cfg["target_vol"] / ann_vol)

    def apply(self, ticker: str, decision: str, price: float, ann_vol: float, atr_value: float,
              prices: dict[str, float]) -> str | None:
        """Act on one signal. Returns a description of any trade made."""
        pos = self.state["positions"].get(ticker)

        if pos and price <= pos["stop"]:
            self._trade(ticker, "SELL", pos["qty"], price, f"stop-loss hit at {pos['stop']:.2f}")
            del self.state["positions"][ticker]
            return f"STOP {ticker} @ {price:.2f}"

        if decision == "SELL" and pos:
            self._trade(ticker, "SELL", pos["qty"], price, "signal SELL")
            del self.state["positions"][ticker]
            return f"SELL {ticker} {pos['qty']:.4f} @ {price:.2f}"

        if decision == "BUY":
            equity = self.equity(prices)
            target_value = equity * self.target_weight(ann_vol)
            current_value = pos["qty"] * price if pos else 0.0
            add_value = min(target_value - current_value, self.state["cash"])
            if add_value < 0.02 * equity:  # ignore tiny top-ups
                return None
            qty = add_value / price
            self._trade(ticker, "BUY", qty, price, "signal BUY")
            if pos:
                new_qty = pos["qty"] + qty
                pos["avg_price"] = (pos["avg_price"] * pos["qty"] + price * qty) / new_qty
                pos["qty"] = new_qty
            else:
                pos = {"qty": qty, "avg_price": price}
                self.state["positions"][ticker] = pos
            pos["stop"] = price - self.cfg["stop_atr_mult"] * atr_value
            return f"BUY {ticker} {qty:.4f} @ {price:.2f}"
        return None
