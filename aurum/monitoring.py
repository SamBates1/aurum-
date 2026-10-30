"""Monitoring (platform phase 10): watch open positions, grade recommendations, and check that paper results stay in
line with what the backtest led us to expect.

Position alerts: stop approached or hit, target reached, the assessment turned against the position (thesis
weakened), portfolio risk above its target, and a clearly better opportunity in the scanner. Alerts never change
or close a position: they appear on the dashboard and follow the approval rules.

Drift alarms: compare the paper account's realised volatility and fall from peak with the backtest's figures. A
breach means "investigate" (and possibly propose an experiment), never "modify the strategy automatically".
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

TRADING_DAYS = 252


@dataclass
class Alert:
    symbol: str | None
    kind: str  # stop, target, thesis, risk, opportunity, drift
    level: str  # info, warning, critical
    text: str


def position_alerts(
    positions: dict[str, dict],
    prices: dict[str, float],
    plans: dict[str, dict],
    verdicts: dict[str, str],
    atr: dict[str, float],
    scanner_scores: dict[str, float] | None = None,
    best_alternative: tuple[str, float] | None = None,
) -> list[Alert]:
    """positions: {symbol: {qty, cost}}; plans: {symbol: {stop, targets: [(label, price, R)]}};
    verdicts: the latest assessment verdict per held symbol."""
    out = []
    for s in positions:
        px = prices.get(s)
        pl = plans.get(s, {})
        if px is None:
            out.append(Alert(s, "data", "warning", f"No current price for {s}"))
            continue
        stop = pl.get("stop")
        if stop:
            if px <= stop:
                out.append(Alert(s, "stop", "critical", f"{s} at ${px:,.2f} is at or below its stop ${stop:,.2f}"))
            elif px - stop <= 0.5 * atr.get(s, 0.0):
                out.append(Alert(s, "stop", "warning", f"{s} is within half a daily range of its stop ${stop:,.2f}"))
        for label, tp, _ in pl.get("targets", []):
            if px >= tp:
                out.append(Alert(s, "target", "info", f"{s} reached its {label} target ${tp:,.2f}"))
                break
        v = verdicts.get(s)
        if v in ("SELL", "REDUCE", "AVOID"):
            out.append(Alert(s, "thesis", "warning", f"The assessment for {s} is now {v}: the case has weakened"))
        sc = (scanner_scores or {}).get(s)
        if best_alternative and sc is not None and sc < 50 and best_alternative[1] >= 85:
            out.append(
                Alert(
                    s,
                    "opportunity",
                    "info",
                    f"{s} now scores {sc:.0f}; {best_alternative[0]} scores {best_alternative[1]:.0f}",
                )
            )
    return out


def risk_alert(portfolio_vol: float | None, target: float = 0.15) -> list[Alert]:
    if portfolio_vol is not None and portfolio_vol > 1.2 * target:
        return [
            Alert(
                None,
                "risk",
                "warning",
                f"Portfolio volatility {portfolio_vol:.0%} is above {1.2 * target:.0%} (target {target:.0%})",
            )
        ]
    return []


def drift_check(
    paper_equity: pd.Series, expected_vol: float, expected_max_dd: float, min_days: int = 40
) -> list[Alert]:
    """Paper vs backtest: realised volatility more than 1.75x expected over 63 days, or a fall from peak more than
    1.25x the backtest's worst. Too little history = no verdict (said, not guessed)."""
    e = paper_equity.dropna()
    if len(e) < min_days:
        return [
            Alert(None, "drift", "info", f"Only {len(e)} days of paper results: too early to compare with the backtest")
        ]
    out = []
    r = e.pct_change().dropna()
    vol = float(r.tail(63).std() * np.sqrt(TRADING_DAYS))
    if vol > 1.75 * expected_vol:
        out.append(
            Alert(
                None,
                "drift",
                "warning",
                f"Paper volatility {vol:.0%} vs {expected_vol:.0%} expected: investigate (strategy unchanged)",
            )
        )
    dd = float((e / e.cummax() - 1).min())
    if dd < 1.25 * expected_max_dd:  # both negative
        out.append(
            Alert(
                None,
                "drift",
                "critical",
                f"Paper fall from peak {dd:.0%} vs backtest worst {expected_max_dd:.0%}: investigate",
            )
        )
    return out


def pot_stats(equity: pd.Series, trades: pd.DataFrame | None = None, benchmark: pd.Series | None = None) -> dict:
    """The experiment's scorecard for one pot: returns, drawdown, and trade statistics when trades are given
    (columns: pnl, days_held, cost)."""
    e = equity.dropna()
    out = {
        "start": float(e.iloc[0]),
        "now": float(e.iloc[-1]),
        "total_return": float(e.iloc[-1] / e.iloc[0] - 1),
        "max_drawdown": float((e / e.cummax() - 1).min()),
    }
    if benchmark is not None and len(benchmark.dropna()) > 1:
        b = benchmark.reindex(e.index).ffill().dropna()
        out["benchmark_return"] = float(b.iloc[-1] / b.iloc[0] - 1) if len(b) > 1 else None
    if trades is not None and len(trades):
        w, lo = trades[trades["pnl"] > 0], trades[trades["pnl"] <= 0]
        out |= {
            "trades": int(len(trades)),
            "win_rate": float(len(w) / len(trades)),
            "average_win": float(w["pnl"].mean()) if len(w) else 0.0,
            "average_loss": float(lo["pnl"].mean()) if len(lo) else 0.0,
            "profit_factor": float(w["pnl"].sum() / -lo["pnl"].sum()) if len(lo) and lo["pnl"].sum() < 0 else None,
            "average_days_held": float(trades["days_held"].mean()),
            "costs": float(trades.get("cost", pd.Series(0.0)).sum()),
        }
    return out
