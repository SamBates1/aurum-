"""Evening run of the 50/50 experiment on the Alpaca PAPER account (GitHub, after the scanners).

Reads the paper account (orders, fills, positions), rebuilds the two pots, then proposes tomorrow's orders from the
latest scans. Manual mode (default): proposals wait for the owner's approval on the Portfolio page. Auto mode: they are
submitted through every independent check. Writes research/orders/ (proposals, state, experiment.md).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import json  # noqa: E402

import pandas as pd  # noqa: E402

from aurum import assessment as AS  # noqa: E402
from aurum import broker as BR  # noqa: E402
from aurum import experiment as EX  # noqa: E402
from aurum import fx  # noqa: E402
from aurum import scanner as SC  # noqa: E402
from aurum import universe as U  # noqa: E402
from aurum.providers import alpaca_keys, get_provider  # noqa: E402


def rankings() -> dict[str, tuple[pd.DataFrame | None, str]]:
    out = {}
    for pot in ("long-term", "swing"):
        f, m = SC.FOLDER / f"{pot}-latest.csv", SC.FOLDER / f"{pot}-latest.json"
        t = pd.read_csv(f, index_col="symbol") if f.is_file() else None
        status = json.loads(m.read_text()).get("evidence", "untested") if m.is_file() else "untested"
        out[pot] = (t, status)
    return out


def daily_frames(symbols: list[str]) -> dict[str, pd.DataFrame]:
    bars = get_provider().daily_many(symbols, days=420)
    out = {}
    now = pd.Timestamp.now(tz="America/New_York")
    for s, b in bars.items():
        d = b.copy()
        d.index = pd.DatetimeIndex(d.index.tz_convert("America/New_York").date)
        if len(d) and d.index[-1].date() >= now.date() and now.hour < 16:
            d = d.iloc[:-1]  # completed days only
        out[s] = d
    return out


def main(broker: BR.PaperBroker | None = None, frames=None) -> dict:
    if broker is None and not alpaca_keys():
        print("No Alpaca keys: experiment not run")
        return {}
    b = broker or BR.PaperBroker()
    cfg = EX.settings()
    today = pd.Timestamp.now(tz="America/New_York").normalize().tz_localize(None)
    orders = b.orders("all", 500)
    pots = BR.ledgers_from_orders(orders, cfg.get("pots", {"long-term": 50_000, "swing": 50_000}))
    positions = b.positions()
    prices = {p["symbol"]: float(p.get("current_price") or 0) for p in positions}
    diff = BR.reconcile(pots, positions)
    # which of yesterday's proposals actually went to Alpaca
    prev = EX.load()
    sent_ids = {o.get("client_order_id") for o in orders}
    done = [
        p
        for p in prev.get("proposals", [])
        if EX.Proposal(**{k: p[k] for k in EX.Proposal.__dataclass_fields__})
        .request(EX.plan_id(prev["asof"], p))
        .client_id()
        in sent_ids
    ]
    state = EX.update_state(EX.load_state(), pots, done, today)
    ranks = rankings()
    held_all = {s for led in pots.values() for s in led["positions"]}
    cands = set(held_all) | {"SPY"}
    for pot, (t, _) in ranks.items():
        if t is not None:
            cands |= set(t.index[: EX.LIMITS[pot]["candidates"]])
    daily = frames if frames is not None else daily_frames(sorted(cands))
    regime = AS.market_regime(daily["SPY"]) if "SPY" in daily else None
    try:
        rate = fx.rate()
    except Exception:
        rate = fx.Rate(fx.SYNTHETIC_RATE, "-", "assumed")
    snap = U.load()
    fractionable = (
        set(snap.assets.index[snap.assets["fractionable"].astype(str).str.lower() == "true"]) if snap else set()
    )
    proposals, notes = [], []
    for pot, led in pots.items():
        mv = sum(q["qty"] * prices.get(s, q["cost"] / max(q["qty"], 1e-9)) for s, q in led["positions"].items())
        t, status = ranks.get(pot, (None, "untested"))
        if t is None:
            notes.append(f"{pot}: no scan available")
            continue
        last = {s: daily[s]["Close"].iloc[-1] for s in daily if len(daily[s])}
        held = {s: q for s, q in led["positions"].items()}
        ps = EX.propose(
            pot,
            led["cash"] + mv,
            led["cash"],
            held,
            t,
            status,
            daily,
            rate.usd_per_gbp,
            state.get(pot, {}),
            today,
            regime,
            fractionable,
        )
        for p in ps:
            p.plan["reference_price"] = float(last.get(p.symbol, 0) or 0)
        proposals += ps
        notes.append(
            f"{pot}: value ${led['cash'] + mv:,.0f}, cash ${led['cash']:,.0f}, "
            f"{len(led['positions'])} positions, {len(ps)} proposals ({status})"
        )
    asof = str((max(d.index[-1] for d in daily.values() if len(d))).date()) if daily else str(today.date())
    if diff:
        notes.append("Reconciliation differences: " + "; ".join(diff))
    st = BR.settings()
    if st["enabled"] and st["mode"] == "auto":
        for p in proposals:
            try:
                b.submit(
                    p.request(EX.plan_id(asof, {"pot": p.pot, "symbol": p.symbol, "side": p.side})),
                    p.plan.get("reference_price") or 1.0,
                    pd.Timestamp.now(tz="UTC"),
                    approved=True,
                )
                p.status = "submitted"
            except BR.BrokerError as e:
                p.status = f"blocked: {e}"
    EX.save(proposals, asof, notes)
    (EX.FOLDER / "state.json").write_text(json.dumps(state, indent=1, default=str))
    lines = [
        "# Experiment: long-term vs swing (PAPER TRADING)",
        "",
        f"Prepared from the close of {asof}. Mode: {st['mode']}; paper orders {'ON' if st['enabled'] else 'OFF'}.",
        "",
    ]
    lines += [f"- {n}" for n in notes]
    lines += [
        "",
        "| Pot | Side | Symbol | Shares | Limit | Stop | Target | Status | Why |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for p in proposals:
        lines.append(
            f"| {p.pot} | {p.side} | {p.symbol} | {p.qty:g} | {p.limit_price or '-'} | {p.stop_loss or '-'} | "
            f"{p.take_profit or '-'} | {p.status} | {p.reason[:120].replace('|', '/')} |"
        )
    (EX.FOLDER / "experiment.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return {"proposals": proposals, "notes": notes}


if __name__ == "__main__":
    main()
