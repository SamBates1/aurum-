"""Daily read-only check of the Alpaca PAPER account (GitHub, after the US close).

Appends the account and pot values to research/orders/equity.csv and writes research/orders/monitor.md: pots,
reconciliation with Alpaca, drift against expectations and alerts. Places no orders and changes nothing.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from aurum import broker as BR  # noqa: E402
from aurum import monitoring as MO  # noqa: E402
from aurum.config import CFG  # noqa: E402
from aurum.providers import alpaca_keys  # noqa: E402


def main():
    if not alpaca_keys():
        print("No Alpaca keys: nothing to monitor")
        return
    b = BR.PaperBroker()
    acct = b.account()
    positions = b.positions()
    prices = {p["symbol"]: float(p.get("current_price") or 0) for p in positions}
    exp = CFG.get("experiment", {})
    pots = BR.ledgers_from_orders(b.orders("all", 500), exp.get("pots", {"long-term": 50_000, "swing": 50_000}))
    vals = {
        name: led["cash"] + sum(q["qty"] * prices.get(s, 0.0) for s, q in led["positions"].items())
        for name, led in pots.items()
    }
    today = pd.Timestamp.now(tz="America/New_York").date()
    f = BR.FOLDER / "equity.csv"
    eq = pd.read_csv(f, index_col=0, parse_dates=True) if f.is_file() else pd.DataFrame()
    eq.loc[pd.Timestamp(today), "account"] = float(acct["equity"] or 0)
    for k, v in vals.items():
        eq.loc[pd.Timestamp(today), k] = v
    eq.sort_index().to_csv(f)
    diff = BR.reconcile(pots, positions)
    alerts = MO.drift_check(eq["account"], expected_vol=0.15, expected_max_dd=-0.25) if "account" in eq else []
    lines = [
        "# Paper account monitor (PAPER TRADING, read-only)",
        "",
        f"{today}: account ${float(acct['equity'] or 0):,.2f}, cash ${float(acct['cash'] or 0):,.2f}, "
        f"{len(positions)} positions. Paper orders {'ON' if BR.settings()['enabled'] else 'OFF'}.",
        "",
        "| Pot | Value | Cash | Positions | Realised P&L |",
        "|---|---|---|---|---|",
    ]
    for name, led in pots.items():
        lines.append(
            f"| {name} | ${vals[name]:,.2f} | ${led['cash']:,.2f} | {len(led['positions'])} | ${led['realised']:,.2f} |"
        )
    lines += ["", "Reconciliation: " + ("Aurum's records match Alpaca." if not diff else "; ".join(diff)), ""]
    lines += [f"- {a.level.upper()}: {a.text}" for a in alerts] or ["No alerts."]
    (BR.FOLDER / "monitor.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
