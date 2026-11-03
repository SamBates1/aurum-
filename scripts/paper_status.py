"""Read-only snapshot of the Alpaca PAPER account: status, cash, open orders, recent orders and positions.

Writes research/orders/status.md. Places, changes and cancels nothing. Keys come from the repository secrets and are
never written anywhere.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from aurum import broker as BR  # noqa: E402
from aurum import experiment as EX  # noqa: E402
from aurum.providers import alpaca_keys  # noqa: E402


def main(b: BR.PaperBroker | None = None) -> str:
    if b is None and not alpaca_keys():
        return "No Alpaca keys"
    b = b or BR.PaperBroker()
    a = b.account()
    open_o = b.orders("open", 500)
    all_o = b.orders("all", 100)
    pos = b.positions()
    props = EX.load()
    ids = (
        {
            EX.Proposal(**{k: p[k] for k in EX.Proposal.__dataclass_fields__})
            .request(EX.plan_id(props["asof"], p))
            .client_id(): p
            for p in props.get("proposals", [])
        }
        if props
        else {}
    )
    lines = [
        "# Paper account status (PAPER TRADING, read-only)",
        "",
        f"Checked {pd.Timestamp.now(tz='Europe/London'):%a %d %b %Y %H:%M} UK. Account {a.get('status')}: equity "
        f"${float(a.get('equity') or 0):,.2f}, cash ${float(a.get('cash') or 0):,.2f}, buying power "
        f"${float(a.get('buying_power') or 0):,.2f}.",
        "",
        f"**Open orders: {len(open_o)}** · positions: {len(pos)} · of the {len(ids)} latest proposals, "
        f"{sum(1 for o in all_o if o.get('client_order_id') in ids)} were sent.",
        "",
        "| Symbol | Side | Qty | Type | Limit | Stop / target | Status | Pot | Submitted (UTC) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for o in all_o:
        legs = o.get("legs") or []
        st = " / ".join(str(x.get("stop_price") or x.get("limit_price") or "") for x in legs) or "-"
        lines.append(
            f"| {o.get('symbol')} | {o.get('side')} | {o.get('qty')} | {o.get('type')} | "
            f"{o.get('limit_price') or '-'} | "
            f"{st} | {o.get('status')} | {BR.pot_of(o.get('client_order_id')) or 'not Aurum'} | "
            f"{str(o.get('submitted_at') or '')[:16]} |"
        )
    if not all_o:
        lines.append("| - | - | - | - | - | - | no orders in the account | - | - |")
    lines += [
        "",
        "## Positions",
        "",
        "| Symbol | Pot | Qty | Avg cost | Now | Value | P&L | P&L % |",
        "|---|---|---|---|---|---|---|---|",
    ]
    pot_by_sym = {}
    for o in all_o:
        if o.get("side") == "buy" and BR.pot_of(o.get("client_order_id")):
            pot_by_sym.setdefault(o.get("symbol"), BR.pot_of(o.get("client_order_id")))
    tot = {}
    for q in sorted(pos, key=lambda x: x.get("symbol")):
        pot = pot_by_sym.get(q.get("symbol"), "not Aurum")
        mv, pl = float(q.get("market_value") or 0), float(q.get("unrealized_pl") or 0)
        t = tot.setdefault(pot, [0.0, 0.0])
        t[0] += mv
        t[1] += pl
        lines.append(
            f"| {q.get('symbol')} | {pot} | {float(q.get('qty') or 0):g} | "
            f"${float(q.get('avg_entry_price') or 0):,.2f} | "
            f"${float(q.get('current_price') or 0):,.2f} | ${mv:,.2f} | ${pl:,.2f} | "
            f"{float(q.get('unrealized_plpc') or 0):+.1%} |"
        )
    pots = BR.ledgers_from_orders(all_o, EX.settings().get("pots", {"long-term": 50_000, "swing": 50_000}))
    lines += [
        "",
        "## Pots",
        "",
        "| Pot | Cash | Positions value | Total | Unrealised P&L | Realised P&L |",
        "|---|---|---|---|---|---|",
    ]
    for name, led in pots.items():
        mv, pl = tot.get(name, [0.0, 0.0])
        lines.append(
            f"| {name} | ${led['cash']:,.2f} | ${mv:,.2f} | ${led['cash'] + mv:,.2f} | ${pl:,.2f} | "
            f"${led['realised']:,.2f} |"
        )
    text = "\n".join(lines) + "\n"
    (BR.FOLDER).mkdir(parents=True, exist_ok=True)
    (BR.FOLDER / "status.md").write_text(text)
    print(text)
    return text


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # keep the reason (keys are redacted by the broker); GitHub logs are not readable here
        BR.FOLDER.mkdir(parents=True, exist_ok=True)
        msg = str(exc)[:500]
        hint = (
            " The Alpaca keys stored on GitHub were rejected: update ALPACA_API_KEY / ALPACA_SECRET_KEY in the "
            "repository secrets."
            if ("401" in msg or "403" in msg or "unauthorized" in msg.lower())
            else ""
        )
        (BR.FOLDER / "status.md").write_text(
            f"# Paper account status\n\nCheck failed: {type(exc).__name__}: {msg}.{hint}\n"
        )
        print(msg)
