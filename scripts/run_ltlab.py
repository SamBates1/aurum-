"""EXP-054 on real data (run on GitHub by the swing-lab workflow with exp=054): a loss limit for long-term holdings.

Same universe and prices as EXP-051. Writes research/experiments/results/<time>-ltlab-real/.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import pandas as pd  # noqa: E402

from aurum import ltlab as LL  # noqa: E402
from aurum import universe as U  # noqa: E402

START = "2017-01-01"
HALF = "2021-01-01"


def main():
    t0 = time.time()
    from run_factorlab import N_STOCKS, panels

    snap = U.load()
    if snap is None:
        raise SystemExit("no universe snapshot: run the data-foundation workflow first")
    a = snap.assets
    stocks = a[(a["kind"] == "stock") & a["eligible"]].sort_values("dollar_volume_20d", ascending=False)
    p = panels(list(stocks.index[:N_STOCKS]))
    rank = LL.momentum_rank(p.close, p.volume)
    level = LL.plan_level(p.high, p.low, p.close)
    res = {v: LL.simulate(p.open, p.close, rank, level, v, START) for v in LL.VARIANTS}
    rows, st = [], {}
    for v, r in res.items():
        full = LL.stats(r.equity)
        h1 = LL.stats(r.equity[r.equity.index < pd.Timestamp(HALF)])
        h2 = LL.stats(r.equity[r.equity.index >= pd.Timestamp(HALF)])
        tr = pd.DataFrame(r.trades)
        st[v] = {"full": full, "h1": h1, "h2": h2}
        rows.append(
            {
                "v": v,
                **full,
                "dd1": h1["max_dd"],
                "dd2": h2["max_dd"],
                "trades": len(tr),
                "limit_exits": int((tr["why"] == "loss limit").sum()) if len(tr) else 0,
                "worst": float(tr["ret"].min()) if len(tr) else float("nan"),
                "invested": r.invested,
            }
        )
    base = LL.VARIANTS[0]
    verdict = {
        v: LL.passes(st[base]["full"], st[v]["full"], st[base]["h1"], st[v]["h1"], st[base]["h2"], st[v]["h2"])
        for v in LL.VARIANTS[1:]
    }
    winners = [v for v, ok in verdict.items() if ok]
    choice = max(winners, key=lambda v: st[v]["full"]["max_dd"]) if winners else base
    out = ROOT / "research" / "experiments" / "results" / f"{pd.Timestamp.now(tz='UTC'):%Y-%m-%d-%H%M}-ltlab-real"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({v: r.equity for v, r in res.items()}).to_csv(out / "equity.csv")
    for v, r in res.items():
        pd.DataFrame(r.trades).to_csv(out / f"trades-{v}.csv", index=False)
    (out / "stats.json").write_text(json.dumps({"stats": st, "passes": verdict, "choice": choice}, indent=1))
    lines = [
        "# EXP-054 results: a loss limit for long-term stock holdings",
        "",
        f"Run {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M} UTC. {p.close.shape[1]} stocks, Alpaca daily adjusted prices "
        f"to {p.close.index[-1].date()}, results from {START}. Up to {LL.MAX_POS} stocks by 12-1 momentum, monthly; "
        "10 bps per fill; cash earns nothing.",
        "",
        "**Survivorship bias:** today's survivors only. It flatters every variant's return and understates what a "
        "loss limit would have saved (collapsed, delisted stocks are missing).",
        "",
        "| Variant | Growth a year | Worst fall | Sharpe | Worst fall 2017-20 | Worst fall 2021-26 | Trades | "
        "Loss-limit exits | Worst holding | Invested | Passes |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        ok = "control" if r["v"] == base else ("**yes**" if verdict[r["v"]] else "**no**")
        lines.append(
            f"| {r['v']} | {r['cagr']:+.1%} | {r['max_dd']:.1%} | {r['sharpe']:.2f} | {r['dd1']:.1%} | "
            f"{r['dd2']:.1%} | {r['trades']} | {r['limit_exits']} | {r['worst']:+.1%} | {r['invested']:.0%} | {ok} |"
        )
    lines += [
        "",
        f"**Decision under the pre-registered rule: {choice}.**",
        "",
        "Pass rule: worst fall at least 20% smaller than the control's, growth no more than 1.0 point a year lower, "
        "and the worst fall not larger than the control's in either half.",
        "",
        f"Run time {time.time() - t0:.0f}s.",
    ]
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
