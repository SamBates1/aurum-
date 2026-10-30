"""Run the three scanners on real data (GitHub, after each US close). Writes research/scanner/.

Stages and counts are recorded for each scanner (scanner.py). Prices: Alpaca SIP daily bars (read-only). Company
accounts: SEC, for the long-term shortlist only. Earnings dates: Yahoo, for the swing shortlist only. No orders.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from aurum import events as EV  # noqa: E402
from aurum import factorlab as FL  # noqa: E402
from aurum import scanner as SC  # noqa: E402
from aurum import sec  # noqa: E402
from aurum import universe as U  # noqa: E402
from aurum.indicators import compute  # noqa: E402
from aurum.providers import get_provider  # noqa: E402

TOP_SHOWN = 50


def panels(symbols: list[str]) -> FL.Panels:
    bars = get_provider().daily_many(symbols, days=320)
    fr = {}
    for k in ("Open", "High", "Low", "Close", "Volume"):
        df = pd.DataFrame({s: b[k] for s, b in bars.items() if len(b)})
        df.index = pd.DatetimeIndex(df.index.tz_convert("America/New_York").date)
        fr[k] = df.sort_index()
    return FL.Panels(fr["Open"], fr["High"], fr["Low"], fr["Close"], fr["Volume"])


def atr_pct_last(p: FL.Panels) -> pd.Series:
    out = {}
    for s in p.close.columns:
        f = pd.DataFrame({"High": p.high[s], "Low": p.low[s], "Close": p.close[s]}).dropna()
        out[s] = compute("atr_pct", f, {"n": 14}).iloc[-1] if len(f) > 20 else np.nan
    return pd.Series(out)


def add_fundamentals(p: FL.Panels, names: list[str]) -> int:
    """Latest point-in-time ROIC and FCF yield for `names` on the last day (other days NaN: rank uses the last day)."""
    d = p.close.index[-1]
    try:
        tmap = sec.ticker_map()
    except Exception as exc:  # SEC unreachable: rank on prices only and say so
        print(f"SEC accounts unavailable: {exc}")
        tmap = {}
    roic = pd.DataFrame(np.nan, index=p.close.index, columns=p.close.columns)
    fcfy = roic.copy()
    n = 0
    for s in names:
        cik = tmap.get(s.upper())
        if cik is None:
            continue
        try:
            m = sec.metrics(sec.facts_table(sec.company_facts(cik)), d, float(p.close.at[d, s]))
        except Exception:
            continue
        if m.get("roic") is not None:
            roic.at[d, s] = m["roic"]
        if m.get("fcf_yield") is not None:
            fcfy.at[d, s] = m["fcf_yield"]
        n += 1
    p.fundamentals = {"roic": roic, "fcf_yield": fcfy}
    return n


def run_one(name: str, snap: U.Snapshot, p: FL.Panels, atr: pd.Series, weights: dict) -> SC.ScanResult:
    cfg = SC.SCANNERS[name]
    res = SC.ScanResult(name, str(p.close.index[-1]))
    res.stages.append(("1. validate", int(snap.assets["eligible"].sum()), "eligible in the universe snapshot"))
    keep, notes = SC.fast_filter(snap.assets, cfg, atr)
    for stage, n, note in notes:
        res.stages.append((f"2. filter: {stage}", n, note))
    w = weights.get(name, {})
    table, used, status = SC.rank(name, p, keep, w, min_history=cfg["min_history"])
    res.stages.append(("3. analyse", len(table), f"{cfg['min_history']}+ days of history, signals computed"))
    if name == "long-term":
        short = list(table.index[: cfg["shortlist"]])
        got = add_fundamentals(p, short)
        table, used, status = SC.rank(name, p, pd.Index(short), w, min_history=cfg["min_history"])
        res.stages.append(
            ("3b. company accounts", got, f"SEC accounts for the top {len(short)}" if got else "SEC unavailable today")
        )
    res.stages.append(
        ("4. rank", len(table), "evidence-weighted" if status == "evidence" else "equal weights (untested)")
    )
    if name == "swing":
        today = p.close.index[-1]
        top = list(table.index[: TOP_SHOWN * 2])
        ev = {
            s: [
                e
                for e in EV.company_events(s)
                if pd.Timestamp(e.date) >= pd.Timestamp(today)
                and pd.Timestamp(e.date) <= pd.Timestamp(today) + pd.Timedelta(days=56)
            ]
            for s in top
        }
        table, dropped = SC.risk_check(table.loc[top], name, ev)
        res.stages.append(("5. risk check", len(table), f"{dropped} dropped: earnings within 8 weeks"))
    else:
        res.stages.append(("5. risk check", len(table), "portfolio checks added in phase 5"))
    res.ranking, res.weights, res.evidence = table.head(TOP_SHOWN * 2), used, status
    return res


def main():
    t0 = time.time()
    snap = U.load()
    if snap is None:
        raise SystemExit("no universe snapshot: run the data-foundation workflow first")
    union = set()
    for cfg in SC.SCANNERS.values():
        union |= set(SC.fast_filter(snap.assets, cfg)[0])
    p = panels(sorted(union))
    atr = atr_pct_last(p)
    weights = SC.load_weights()
    lines = [
        "# Scanner results",
        "",
        f"Close of {p.close.index[-1]}. Alpaca SIP daily prices, {p.close.shape[1]:,} "
        "instruments analysed. What the rules rank highest, not advice; nothing places an order.",
        "",
    ]
    for name in SC.SCANNERS:
        res = run_one(name, snap, p, atr, weights)
        SC.save(res)
        lines.append(res.summary())
        if res.ranking is not None and len(res.ranking):
            top = res.ranking.head(15)
            lines += [
                "| # | Symbol | Score | " + " | ".join(k for k in res.weights) + " |",
                "|---|---|---|" + "---|" * len(res.weights),
            ]
            for i, (s, r) in enumerate(top.iterrows(), 1):
                vals = " | ".join(
                    f"{r.get('rank_' + k, np.nan):.0%}" if pd.notna(r.get("rank_" + k)) else "-" for k in res.weights
                )
                lines.append(f"| {i} | {s} | {r['score']:.0f} | {vals} |")
            lines.append("")
    lines.append(f"Run time {time.time() - t0:.0f}s.")
    (SC.FOLDER / "latest.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    import traceback

    SC.FOLDER.mkdir(parents=True, exist_ok=True)
    try:
        main()
        (SC.FOLDER / "scan-error.txt").unlink(missing_ok=True)
    except Exception:
        (SC.FOLDER / "scan-error.txt").write_text(traceback.format_exc()[-4000:])
        raise
