"""EXP-051 on real data (run on GitHub by the factor-lab workflow).

Universe: the 1,000 largest eligible US stocks in research/universe/assets.csv; daily SIP prices from Alpaca since
2016; point-in-time ROIC and free-cash-flow yield from SEC filings at each month end. Writes
research/experiments/results/<time>-factorlab-real/ (summary.md, stats.csv, per-signal period returns).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from aurum import factorlab as FL  # noqa: E402
from aurum import sec  # noqa: E402
from aurum import universe as U  # noqa: E402
from aurum.providers import get_provider  # noqa: E402

N_STOCKS = 1000
START = "2016-01-01"
HALVES = ("2020-12-31", "2021-01-01")
RECENT = "2024-01-01"


def panels(symbols: list[str]) -> FL.Panels:
    p = get_provider()
    bars = p.daily_many(symbols, start=START)
    fr = {}
    for k in ("Open", "High", "Low", "Close", "Volume"):
        df = pd.DataFrame({s: b[k] for s, b in bars.items() if len(b)})
        df.index = pd.DatetimeIndex(df.index.tz_convert("America/New_York").date)
        fr[k] = df.sort_index()
    return FL.Panels(fr["Open"], fr["High"], fr["Low"], fr["Close"], fr["Volume"])


def fundamental_panels(p: FL.Panels) -> tuple[dict[str, pd.DataFrame], dict]:
    """Month-end point-in-time ROIC and FCF yield, forward-filled to daily rows (known from that month end)."""
    tmap = sec.ticker_map()
    month_ends = FL.rank_days(p.close.index, "monthly")
    roic = pd.DataFrame(np.nan, index=month_ends, columns=p.close.columns)
    fcfy = roic.copy()
    found, failed = 0, 0
    for s in p.close.columns:
        cik = tmap.get(s.upper())
        if cik is None:
            continue
        try:
            t = sec.facts_table(sec.company_facts(cik))
        except Exception:
            failed += 1
            continue
        if not len(t):
            continue
        found += 1
        for d in month_ends:
            px = p.close.at[d, s]
            m = sec.metrics(t, d, float(px) if np.isfinite(px) else None)
            roic.at[d, s] = m.get("roic") if m.get("roic") is not None else np.nan
            fcfy.at[d, s] = m.get("fcf_yield") if m.get("fcf_yield") is not None else np.nan
    daily = {k: v.reindex(p.close.index, method="ffill") for k, v in (("roic", roic), ("fcf_yield", fcfy))}
    return daily, {"sec_found": found, "sec_failed": failed}


def main():
    t0 = time.time()
    snap = U.load()
    if snap is None:
        raise SystemExit("no universe snapshot: run the data-foundation workflow first")
    a = snap.assets
    stocks = a[(a["kind"] == "stock") & a["eligible"]].sort_values("dollar_volume_20d", ascending=False)
    symbols = list(stocks.index[:N_STOCKS])
    p = panels(symbols)
    try:
        fund, info = fundamental_panels(p)
        p.fundamentals = fund
    except Exception as exc:  # EXP-051a: price signals only (amendment of 2026-10-30)
        print(f"SEC accounts unavailable ({exc}): running the price-based signals only (EXP-051a)")
        info = {"sec_found": 0, "sec_failed": 0, "sec_error": str(exc)[:200]}
    stats, returns = {}, {}
    for name, sig in FL.long_term_signals(p).items():
        res = FL.backtest(p, sig, "monthly", hold=1, cost_bps=10, start="2017-01-01")
        returns[name] = res
        stats[name] = FL.judge(res, "monthly", HALVES, RECENT) | {"family": "long-term"}
    for name, sig in FL.swing_signals(p).items():
        res = FL.backtest(p, sig, "weekly", hold=4, cost_bps=15, start="2017-01-01")
        returns[name] = res
        stats[name] = FL.judge(res, "weekly", HALVES, RECENT) | {"family": "swing"}
    stats = FL.verdicts(stats)
    out = ROOT / "research" / "experiments" / "results" / f"{pd.Timestamp.now(tz='UTC'):%Y-%m-%d-%H%M}-factorlab-real"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(stats).T.to_csv(out / "stats.csv")
    for k, r in returns.items():
        r.to_csv(out / f"returns-{k}.csv")

    def f(x, pct=True):
        return (
            "-" if x is None or (isinstance(x, float) and not np.isfinite(x)) else (f"{x:+.1%}" if pct else f"{x:.2f}")
        )

    part = "EXP-051a (price signals)" if not p.fundamentals else "EXP-051"
    lines = [
        f"# {part} results: stock signals vs holding every stock equally",
        "",
        f"Run {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M} UTC. {p.close.shape[1]} stocks with prices "
        f"({p.close.index[0]} to {p.close.index[-1]}), Alpaca SIP daily, adjusted. SEC accounts found for "
        f"{info['sec_found']} companies ({info['sec_failed']} failed). Tests from 2017 (one year of history first).",
        "",
        "**Survivorship bias:** today's survivors only; long-only results are flattered. The pass bar is 3% a year.",
        "",
        "| Signal | Family | Extra return / yr after costs | NW t | 2017-20 | 2021-26 | 2024+ | Turnover / period "
        "| Verdict |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for k, s in stats.items():
        lines.append(
            f"| {k} | {s['family']} | {f(s.get('excess_per_year'))} | {f(s.get('t'), False)} | "
            f"{f(s.get('first_half'))} | {f(s.get('second_half'))} | {f(s.get('recent'))} | "
            f"{f(s.get('turnover'), False)} | **{s.get('verdict')}** |"
        )
    lines += [
        "",
        "Pass rule (pre-registered): extra return at least 3% a year after costs, Newey-West t at least 2, positive in "
        "both halves and since 2024, and a Benjamini-Hochberg discovery at 10% across all signals.",
        "",
        f"Run time {time.time() - t0:.0f}s.",
    ]
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    (out / "metadata.json").write_text(json.dumps({"symbols": symbols, **info}, indent=1))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
