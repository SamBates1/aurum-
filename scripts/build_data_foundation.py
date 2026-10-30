"""Platform phase 1 on real data (run on GitHub by the data-foundation workflow).

1. Universe: every active US stock/ETF Alpaca lists, liquidity from 90 days of daily bars, eligibility with reasons,
   changes since the last snapshot -> research/universe/ (assets.csv, snapshot.json, coverage.md).
2. SEC accounts: point-in-time metrics for the watchlist companies plus a sample of eligible stocks, as known today
   and as known one year ago (shows the no-hindsight rule working) -> research/universe/fundamentals-check.md.
3. Pound/dollar rate and the next Fed meetings and earnings dates for the watchlist.
Nothing here places an order; Alpaca is called read-only.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from aurum import events as EV  # noqa: E402
from aurum import fx, sec  # noqa: E402
from aurum import universe as U  # noqa: E402
from aurum.config import CFG  # noqa: E402
from aurum.providers import get_provider  # noqa: E402


def build_universe() -> U.Snapshot:
    p = get_provider()
    if p.name != "Alpaca":
        raise SystemExit("Alpaca keys are needed for the universe (set ALPACA_API_KEY / ALPACA_SECRET_KEY)")
    t0 = time.time()
    table = U.from_alpaca_assets(p.assets())
    candidates = [s for s, r in table.iterrows() if r["tradable"] and r["exchange"] in U.EXCHANGES and "/" not in s]
    bars = p.daily_many(candidates, days=90)
    liq = U.liquidity(bars, pd.Timestamp.now(tz="UTC"))
    snap = U.Snapshot(U.assess(table, liq), pd.Timestamp.now(tz="UTC").floor("s"), "Alpaca asset list + SIP daily bars")
    old = U.load()
    ch = U.changes(old.assets if old else None, snap.assets)
    U.save(snap)
    (U.FOLDER / "coverage.md").write_text(
        U.coverage_report(snap, ch) + f"\nBuilt in {time.time() - t0:.0f}s; {len(bars):,} symbols returned bars.\n"
    )
    print(U.coverage_report(snap, ch))
    return snap


def fundamentals_check(snap: U.Snapshot) -> None:
    wl = list(CFG.get("watchlist", {}).get("stocks", []))
    a = snap.assets
    big = a[(a["kind"] == "stock") & a["eligible"]].sort_values("dollar_volume_20d", ascending=False)
    sample = list(dict.fromkeys(wl + list(big.index[:40])))
    tmap = sec.ticker_map()
    now = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
    year_ago = now - pd.DateOffset(years=1)
    lines = [
        "# SEC fundamentals check (point-in-time)",
        "",
        f"Run {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M} UTC. Each row uses only filings that reached the SEC by the "
        "date shown. 'A year ago' shows what was knowable then (no hindsight).",
        "",
        "| Ticker | Known on | Latest year end | Filed | Revenue growth | Net margin | ROIC | FCF margin | Debt/equity "
        "| P/E | Missing |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    def pct(x):
        return f"{x:+.1%}" if isinstance(x, float) else "-"

    found = 0
    for s in sample:
        if s not in tmap:
            lines.append(f"| {s} | - | - | - | - | - | - | - | - | - | not an SEC filer |")
            continue
        try:
            t = sec.facts_table(sec.company_facts(tmap[s]))
        except Exception as exc:
            lines.append(f"| {s} | - | - | - | - | - | - | - | - | - | error: {str(exc)[:60]} |")
            continue
        found += 1
        price = float(a.at[s, "price"]) if s in a.index and pd.notna(a.at[s, "price"]) else None
        for label, when, px in (("today", now, price), ("a year ago", year_ago, None)):
            m = sec.metrics(t, when, px)
            de, pe = m.get("debt_to_equity"), m.get("pe")
            cells = [
                s,
                label,
                m.get("period_end") or "-",
                m.get("filed") or "-",
                pct(m.get("revenue_growth")),
                pct(m.get("net_margin")),
                pct(m.get("roic")),
                pct(m.get("fcf_margin")),
                f"{de:.2f}" if isinstance(de, float) else "-",
                f"{pe:.1f}" if isinstance(pe, float) else "-",
                ", ".join(m["missing"]) or "-",
            ]
            lines.append("| " + " | ".join(cells) + " |")
    lines += ["", f"{found} of {len(sample)} tickers found at the SEC."]
    (U.FOLDER / "fundamentals-check.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:30]))


def calendar_and_fx() -> None:
    r = fx.rate()
    today = pd.Timestamp.now(tz="UTC").tz_localize(None)
    lines = [
        "# Calendar and currency check",
        "",
        f"Pound/dollar: {r.label}.",
        "",
        "| Date | Event | Confirmed | Source |",
        "|---|---|---|---|",
    ]
    evs = EV.fomc_events(today, today + pd.Timedelta(days=120))
    for s in CFG.get("watchlist", {}).get("stocks", []):
        evs += [e for e in EV.company_events(s) if today <= pd.Timestamp(e.date) <= today + pd.Timedelta(days=120)]
    for e in sorted(evs, key=lambda x: x.date):
        lines.append(f"| {e.date} | {e.text} | {'yes' if e.confirmed else 'expected'} | {e.source} |")
    (U.FOLDER / "calendar-check.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    import traceback

    U.FOLDER.mkdir(parents=True, exist_ok=True)
    try:
        snap = build_universe()
    except Exception:  # keep the reason: GitHub logs are not readable from the build machine
        (U.FOLDER / "build-error.txt").write_text(traceback.format_exc()[-4000:])
        raise
    for step in (fundamentals_check, calendar_and_fx):
        try:
            step(snap) if step is fundamentals_check else step()
        except Exception as exc:  # report and continue: one source failing must not hide the others
            print(f"{step.__name__} failed: {exc}")
            (U.FOLDER / f"{step.__name__}-error.txt").write_text(str(exc)[:2000])
