"""EXP-052 on real data (run on GitHub by the swing-lab workflow): single 2R target vs a ladder of profit-taking.

Same universe and prices as EXP-051 (`scripts/run_factorlab.py`). Writes
research/experiments/results/<time>-swinglab-real/ (summary.md, trades.csv, stats.json).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from aurum import factorlab as FL  # noqa: E402
from aurum import investplan as IP  # noqa: E402
from aurum import swinglab as SL  # noqa: E402
from aurum import universe as U  # noqa: E402

START_TRADES = "2017-01-01"
HALVES = ("2020-12-31", "2021-01-01")
RECENT = "2024-01-01"


LIVE = "--live" in sys.argv  # corrected re-run (audit, D-048): the live scanner's filters and the live entry order


def live_mask(p: FL.Panels) -> pd.DataFrame:
    """Where a stock passes the live swing scanner's own filters (scanner.DEFAULTS['swing']) on each day: price at
    least $10, at least $20M traded a day (20-day average), and ATR(14) between 1% and 6% of the price."""
    prev = p.close.shift(1)
    tr = np.maximum(p.high - p.low, np.maximum((p.high - prev).abs(), (p.low - prev).abs()))
    atr_pct = tr.rolling(14).mean() / p.close  # the same simple average the scanner uses (indicators._atr)
    dollar = (p.close * p.volume).rolling(20).mean()
    return (p.close >= 10.0) & (dollar >= 20e6) & (atr_pct >= 0.01) & (atr_pct <= 0.06)


def trades_for(p: FL.Panels, score=None, live: bool = False) -> pd.DataFrame:
    """One row per trade; `score(row, o, h, lo, c, ti, C, stop)` fills the variant columns (default: EXP-052).

    live=False is the original test: any of the 1,000 stocks, bought at the next open if it is within 0.25 ATR of the
    close. live=True is what the account does: only stocks passing the live scanner's filters, bought with a one-day
    limit order at close + 0.25 ATR (fills at the open when the open is at or below the limit, however far below;
    otherwise at the limit if the day trades down to it; otherwise no trade). Each row also carries `bench`: the
    equal-weight return of every stock in the test over the same 28 days, open to open."""
    score = score or score_exp052
    sig = FL.swing_signals(p)["trend_strength"]
    if live:
        sig = sig.where(live_mask(p))
    bench_cache: dict = {}

    def bench(entry_day) -> float:
        if entry_day not in bench_cache:
            i0 = p.open.index.get_loc(entry_day)
            i1 = min(int(p.open.index.searchsorted(entry_day + pd.Timedelta(days=SL.TIME_STOP_DAYS))), len(p.open) - 1)
            r = (p.open.iloc[i1] / p.open.iloc[i0] - 1).replace([np.inf, -np.inf], np.nan).dropna()
            bench_cache[entry_day] = float(r.mean()) if len(r) else np.nan
        return bench_cache[entry_day]

    fridays = FL.rank_days(p.close.index, "weekly")
    fridays = fridays[fridays >= pd.Timestamp(START_TRADES)]
    frames: dict[str, pd.DataFrame] = {}
    busy_until: dict[str, pd.Timestamp] = {}
    rows, skipped = [], {"no_next_day": 0, "outside_entry_zone": 0, "bad_levels": 0, "already_held": 0}
    for d, s in SL.entries(sig, fridays):
        if s in busy_until and d < busy_until[s]:
            skipped["already_held"] += 1
            continue
        if s not in frames:
            frames[s] = pd.DataFrame(
                {"Open": p.open[s], "High": p.high[s], "Low": p.low[s], "Close": p.close[s], "Volume": p.volume[s]}
            ).dropna(subset=["Open", "High", "Low", "Close"])
        df = frames[s]
        pos = df.index.searchsorted(d, side="right")  # first bar after the signal day
        if pos >= len(df) or df.index[pos - 1] != d:
            skipped["no_next_day"] += 1
            continue
        try:
            L = IP._levels(df.iloc[max(0, pos - 300) : pos])
        except Exception:
            skipped["bad_levels"] += 1
            continue
        C, atr, sup = L["close"], L["atr"], L["support"]
        if not (np.isfinite(atr) and atr > 0):
            skipped["bad_levels"] += 1
            continue
        stop = max((sup - 0.25 * atr) if sup else C - 2 * atr, C - 2 * atr)  # the live swing rule (investplan.build)
        if not (0 < stop < C):
            skipped["bad_levels"] += 1
            continue
        fut = df.iloc[pos:]
        open0, entry_px = float(fut["Open"].iloc[0]), None
        if live:
            limit = C + 0.25 * atr
            if open0 <= limit:
                entry_px = open0
            elif float(fut["Low"].iloc[0]) <= limit:
                entry_px = limit
        elif abs(open0 - C) <= 0.25 * atr:
            entry_px = open0
        if entry_px is None:
            skipped["outside_entry_zone"] += 1
            continue
        entry_day = fut.index[0]
        t_idx = int(fut.index.searchsorted(entry_day + pd.Timedelta(days=SL.TIME_STOP_DAYS)))
        window = fut.iloc[: t_idx + 1]
        o, h, lo, c = (window[k].to_numpy(float).copy() for k in ("Open", "High", "Low", "Close"))
        o[0] = entry_px  # the simulators take the entry price from the first open
        ti = t_idx if t_idx < len(window) else None
        row = {"week": d, "symbol": s, "entry_day": entry_day, "ref": C, "stop": stop, "R_pct": (C - stop) / C}
        row["bench"] = bench(entry_day)
        score(row, o, h, lo, c, ti, C, stop)
        rows.append(row)
        busy_until[s] = window.index[-1]
    out = pd.DataFrame(rows)
    out.attrs["skipped"] = skipped
    return out


def score_exp052(row, o, h, lo, c, ti, C, stop) -> None:
    for name, v in SL.VARIANTS.items():
        for order in ("conservative", "optimistic"):
            tr = SL.simulate(o, h, lo, c, ti, C, stop, v["targets"], v["breakeven"], order)
            suffix = "" if order == "conservative" else "_opt"
            row[name + suffix] = tr.ret
            row[name + suffix + "_R"] = tr.r_multiple
            row[name + suffix + "_exit"] = tr.exit_kind


def describe(tr: pd.DataFrame, name: str) -> dict:
    r = tr[name]
    exits = tr[name + "_exit"].value_counts(normalize=True).to_dict()
    weekly = r.groupby(tr["week"]).mean()
    return {
        "mean_ret": float(r.mean()),
        "median_ret": float(r.median()),
        "mean_R": float(tr[name + "_R"].mean()),
        "win_rate": float((r > 0).mean()),
        "avg_win": float(r[r > 0].mean()),
        "avg_loss": float(r[r <= 0].mean()),
        "worst": float(r.min()),
        "best": float(r.max()),
        "exits": {k: round(float(v), 3) for k, v in exits.items()},
        "weekly_sum": float(weekly.sum()),
    }


def main():
    t0 = time.time()
    from run_factorlab import N_STOCKS, panels

    snap = U.load()
    if snap is None:
        raise SystemExit("no universe snapshot: run the data-foundation workflow first")
    a = snap.assets
    stocks = a[(a["kind"] == "stock") & a["eligible"]].sort_values("dollar_volume_20d", ascending=False)
    symbols = list(stocks.index[:N_STOCKS])
    p = panels(symbols)
    tr = trades_for(p, live=LIVE)
    names = list(SL.VARIANTS)
    desc = {n: describe(tr, n) for n in names} | {n + "_opt": describe(tr, n + "_opt") for n in names}
    pairs = {}
    for b in names[1:]:
        cons = SL.paired_stats(tr, names[0], b, HALVES, RECENT)
        opt = SL.paired_stats(tr, names[0] + "_opt", b + "_opt", HALVES, RECENT)
        ok = (
            cons["mean_diff"] > 0
            and cons["t"] >= 2.0
            and cons["first_half"] > 0
            and cons["second_half"] > 0
            and cons["recent"] >= 0
            and opt["mean_diff"] > 0
        )
        pairs[b] = {"conservative": cons, "optimistic": opt, "passes": bool(ok)}
    winners = [b for b in pairs if pairs[b]["passes"]]
    choice = max(winners, key=lambda b: pairs[b]["conservative"]["t"]) if winners else names[0]

    out = (
        ROOT
        / "research"
        / "experiments"
        / "results"
        / f"{pd.Timestamp.now(tz='UTC'):%Y-%m-%d-%H%M}-swinglab-{'live' if LIVE else 'real'}"
    )
    out.mkdir(parents=True, exist_ok=True)
    tr.to_csv(out / "trades.csv", index=False)
    (out / "stats.json").write_text(
        json.dumps({"describe": desc, "pairs": pairs, "choice": choice, "skipped": tr.attrs["skipped"]}, indent=1)
    )

    def pc(x):
        return "-" if x is None or not np.isfinite(x) else f"{x:+.2%}"

    lines = [
        "# EXP-052 results: one 2R target vs a profit-taking ladder (swing trades)",
        "",
        f"Run {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M} UTC. {p.close.shape[1]} stocks, Alpaca daily adjusted prices "
        f"to {p.close.index[-1]}. {len(tr)} trades from {START_TRADES} (top {SL.TOP_N} `trend_strength` each Friday); "
        f"skipped: {tr.attrs['skipped']}. Costs 5 bps per fill. Same-day stop and target: stop first.",
        "",
        "**Survivorship bias:** today's survivors only; it flatters every variant equally (same entries).",
        "",
        (
            "**Corrected re-run (audit, D-048):** only stocks passing the live swing scanner's filters (price at least "
            "$10, $20M a day, ATR 1-6%), entered with the live one-day limit order. Original pass rule, unchanged."
            if LIVE
            else "Original test: any of the 1,000 stocks, entered at the next open within 0.25 ATR of the close."
        ),
        "",
        f"**Against simply holding:** the single-target trades averaged {tr[names[0]].mean():+.2%} each; every stock "
        f"in the test, held for the same 28 days, averaged {tr['bench'].mean():+.2%}. Trades are often shorter than "
        "28 days, so this is a rough comparison, not a test.",
        "",
        "| Variant | Mean per trade | Median | Mean R | Win rate | Avg win | Avg loss | Worst | Exits |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for n in names:
        s = desc[n]
        ex = ", ".join(f"{k} {v:.0%}" for k, v in sorted(s["exits"].items(), key=lambda kv: -kv[1]))
        lines.append(
            f"| {n} | {pc(s['mean_ret'])} | {pc(s['median_ret'])} | {s['mean_R']:+.2f} | {s['win_rate']:.0%} | "
            f"{pc(s['avg_win'])} | {pc(s['avg_loss'])} | {pc(s['worst'])} | {ex} |"
        )
    lines += [
        "",
        "## Paired comparison with A (per trade, weekly averages)",
        "",
        "| Variant | Mean difference | NW t | 2017-20 | 2021-26 | 2024+ | Optimistic ordering | Passes |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for b, v in pairs.items():
        c, o = v["conservative"], v["optimistic"]
        lines.append(
            f"| {b} | {pc(c['mean_diff'])} | {c['t']:.2f} | {pc(c['first_half'])} | {pc(c['second_half'])} | "
            f"{pc(c['recent'])} | {pc(o['mean_diff'])} | **{'yes' if v['passes'] else 'no'}** |"
        )
    lines += [
        "",
        f"**Decision under the pre-registered rule: {choice}.**",
        "",
        "Pass rule: mean difference > 0 with NW t >= 2, positive in both halves, not negative since 2024, and still "
        "positive with the optimistic ordering.",
        "",
        f"Run time {time.time() - t0:.0f}s.",
    ]
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
