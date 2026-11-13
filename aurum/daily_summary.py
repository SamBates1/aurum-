"""The "Today" summary of the Alpaca PAPER account: one short answer to "how is it doing and what needs me?".

Pure functions, so the nightly monitor (research/orders/today.md) and the Portfolio page show the same thing:
  - the account and each pot, today and since the start, against SPY bought with the same money on the same day
  - what was bought and sold since the last recorded close
  - held positions close to their stop
  - what is waiting for the owner (orders to approve, "ACTION NEEDED" notes)
The SPY comparison is a yardstick, not a test: ten days of results say nothing about skill.
"""

from __future__ import annotations

import pandas as pd

from . import broker as BR

START = "2026-11-02"  # first day the experiment's orders filled
NEAR_STOP = 0.03  # a position within 3% of its stop is listed


def _ny_dates(idx) -> pd.DatetimeIndex:
    idx = pd.DatetimeIndex(idx)
    if idx.tz is not None:
        idx = idx.tz_convert("America/New_York").tz_localize(None)
    return idx.normalize()


def spy_benchmark(spy: pd.DataFrame, start: str = START, money: float = 100_000.0) -> pd.Series:
    """Value of `money` put into SPY at the open of `start`, at each later close (whole history, no costs)."""
    df = spy.copy()
    df.index = _ny_dates(df.index)
    df = df[df.index >= pd.Timestamp(start)]
    if df.empty:
        return pd.Series(dtype=float)
    return money * df["Close"] / float(df["Open"].iloc[0])


def fills_since(orders: list[dict], since: pd.Timestamp) -> list[dict]:
    """Every Aurum fill (including stop and target legs) after `since`, oldest first."""
    out = []
    for o in orders:
        for x in [o, *(o.get("legs") or [])]:
            q = float(x.get("filled_qty") or 0)
            when = x.get("filled_at")
            if q <= 0 or not when or pd.Timestamp(when) <= since:
                continue
            kind = (
                "buy"
                if x.get("side") == "buy"
                else {"stop": "stop hit", "limit": "target hit"}.get(str(x.get("type")), "sold")
            )
            if x is o and x.get("side") == "sell" and str(x.get("type")) == "market":
                kind = "sold (time limit or exit)"
            out.append(
                {
                    "when": pd.Timestamp(when),
                    "pot": BR.pot_of(o.get("client_order_id")) or "not Aurum",
                    "symbol": x.get("symbol") or o.get("symbol"),
                    "what": kind,
                    "shares": q,
                    "price": float(x.get("filled_avg_price") or 0),
                }
            )
    return sorted(out, key=lambda r: r["when"])


def near_stops(positions: list[dict], open_orders: list[dict], within: float = NEAR_STOP) -> list[dict]:
    """Held positions whose price is within `within` of the stop working at Alpaca (closest first)."""
    stops = {}
    for o in open_orders:
        if o.get("side") == "sell":
            _, stop = BR.protection_levels(o)
            if stop:
                stops[o.get("symbol")] = stop
    out = []
    for p in positions:
        s, px = p.get("symbol"), float(p.get("current_price") or 0)
        if s in stops and px > 0:
            gap = px / stops[s] - 1
            if gap <= within:
                out.append({"symbol": s, "price": px, "stop": stops[s], "gap": gap})
    return sorted(out, key=lambda r: r["gap"])


def build(
    equity: pd.DataFrame,
    spy: pd.DataFrame | None,
    orders: list[dict],
    positions: list[dict],
    open_orders: list[dict],
    waiting: int = 0,
    notes: list[str] | None = None,
    start_cash: dict[str, float] | None = None,
) -> dict:
    """Everything the summary shows. `equity`: research/orders/equity.csv (columns account and one per pot)."""
    start_cash = start_cash or {"long-term": 50_000.0, "swing": 50_000.0}
    total0 = float(sum(start_cash.values()))
    eq = equity.sort_index()
    eq.index = _ny_dates(eq.index)
    last = eq.index[-1]
    prev = eq.index[-2] if len(eq) > 1 else None
    bench = spy_benchmark(spy, money=1.0) if spy is not None and len(spy) else pd.Series(dtype=float)

    def growth_at(day) -> float | None:
        if day is None or bench.empty:
            return None
        upto = bench[bench.index <= day]
        return float(upto.iloc[-1]) if len(upto) else None

    growth, growth_prev = growth_at(last), growth_at(prev)
    rows = []
    for col, money in [("account", total0), *start_cash.items()]:
        if col not in eq:
            continue
        v = float(eq[col].iloc[-1])
        rows.append(
            {
                "name": "whole account" if col == "account" else f"{col} pot",
                "value": v,
                "day": v - float(eq[col].iloc[-2]) if prev is not None else None,
                "since_start": v / money - 1,
                "spy_value": money * growth if growth else None,
                "spy_since_start": growth - 1 if growth else None,
                "vs_spy": (v / money - growth) if growth else None,
            }
        )
    since = (
        pd.Timestamp(f"{prev.date()} 16:00", tz="America/New_York")
        if prev is not None
        else pd.Timestamp(START, tz="America/New_York")
    )
    actions = [n for n in (notes or []) if n.startswith("ACTION NEEDED")]
    return {
        "date": last.date(),
        "days": int((eq.index >= pd.Timestamp(START)).sum()),
        "rows": rows,
        "spy_day": (growth / growth_prev - 1) if growth and growth_prev else None,
        "fills": fills_since(orders, since),
        "fills_since": since,
        "near_stops": near_stops(positions, open_orders),
        "waiting": int(waiting),
        "actions": actions,
    }


def _money(x: float | None, sign: bool = False) -> str:
    if x is None:
        return "-"
    return f"{'+' if sign and x >= 0 else '-' if x < 0 else ''}${abs(x):,.0f}"


def _pct(x: float | None) -> str:
    return "-" if x is None else f"{x:+.1%}"


def to_markdown(s: dict) -> str:
    lines = [
        f"# Today: Alpaca paper account, close of {s['date']} (PAPER TRADING)",
        "",
        "| | Value | Today | Since start | Same money in SPY | Ahead of / behind SPY |",
        "|---|---|---|---|---|---|",
    ]
    for r in s["rows"]:
        lines.append(
            f"| {r['name']} | {_money(r['value'])} | {_money(r['day'], True)} | {_pct(r['since_start'])} | "
            f"{_money(r['spy_value'])} ({_pct(r['spy_since_start'])}) | {_pct(r['vs_spy'])} |"
        )
    lines += [
        "",
        f"SPY bought at the open on {START}, no costs. {s['days']} trading days so far: far too few to say anything "
        "about skill (the account is a test of order handling, D-048).",
        "",
        "**Bought and sold since the last close:** "
        + (
            "; ".join(
                f"{f['what']} {f['symbol']} ({f['pot']}) {f['shares']:g} at ${f['price']:,.2f}" for f in s["fills"]
            )
            if s["fills"]
            else "nothing."
        ),
        "",
        f"**Within {NEAR_STOP:.0%} of their stop:** "
        + (
            "; ".join(
                f"{n['symbol']} ${n['price']:,.2f}, stop ${n['stop']:,.2f} ({n['gap']:.1%} above)"
                for n in s["near_stops"]
            )
            if s["near_stops"]
            else "none."
        ),
        "",
        "**Needs you:** "
        + (
            "; ".join(
                ([f"{s['waiting']} order(s) to approve on the Portfolio page"] if s["waiting"] else []) + s["actions"]
            )
            if s["waiting"] or s["actions"]
            else "nothing."
        ),
    ]
    return "\n".join(lines) + "\n"
