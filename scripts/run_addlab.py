"""EXP-053 on real data (run on GitHub by the swing-lab workflow with `--exp 053`): add to swing winners or not.

Same trades as EXP-052 (`scripts/run_swinglab.py`). Writes research/experiments/results/<time>-addlab-real/.
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

from aurum import swinglab as SL  # noqa: E402
from aurum import universe as U  # noqa: E402

HALVES = ("2020-12-31", "2021-01-01")
RECENT = "2024-01-01"


def score_exp053(row, o, h, lo, c, ti, C, stop) -> None:
    for name, frac in SL.ADD_VARIANTS.items():
        for order in ("conservative", "optimistic"):
            ret, kind, added = SL.simulate_add(o, h, lo, c, ti, C, stop, frac, order=order)
            suffix = "" if order == "conservative" else "_opt"
            row[name + suffix] = ret
            row[name + suffix + "_exit"] = kind
            row[name + suffix + "_added"] = added


def main():
    t0 = time.time()
    import run_swinglab as RS
    from run_factorlab import N_STOCKS, panels

    snap = U.load()
    if snap is None:
        raise SystemExit("no universe snapshot: run the data-foundation workflow first")
    a = snap.assets
    stocks = a[(a["kind"] == "stock") & a["eligible"]].sort_values("dollar_volume_20d", ascending=False)
    p = panels(list(stocks.index[:N_STOCKS]))
    tr = RS.trades_for(p, score_exp053)
    names = list(SL.ADD_VARIANTS)
    desc = {}
    for n in names:
        r = tr[n]
        desc[n] = {
            "mean": float(r.mean()),
            "median": float(r.median()),
            "win_rate": float((r > 0).mean()),
            "avg_win": float(r[r > 0].mean()),
            "avg_loss": float(r[r <= 0].mean()),
            "worst": float(r.min()),
            "best": float(r.max()),
            "added": float(tr[n + "_added"].mean()),
            "exits": {k: round(float(v), 3) for k, v in tr[n + "_exit"].value_counts(normalize=True).items()},
        }
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
            and desc[b]["worst"] >= desc[names[0]]["worst"] - 1e-12
        )
        pairs[b] = {"conservative": cons, "optimistic": opt, "passes": bool(ok)}
    winners = [b for b in pairs if pairs[b]["passes"]]
    choice = max(winners, key=lambda b: pairs[b]["conservative"]["t"]) if winners else names[0]
    out = ROOT / "research" / "experiments" / "results" / f"{pd.Timestamp.now(tz='UTC'):%Y-%m-%d-%H%M}-addlab-real"
    out.mkdir(parents=True, exist_ok=True)
    tr.to_csv(out / "trades.csv", index=False)
    (out / "stats.json").write_text(json.dumps({"describe": desc, "pairs": pairs, "choice": choice}, indent=1))

    def pc(x):
        return "-" if x is None or not np.isfinite(x) else f"{x:+.2%}"

    lines = [
        "# EXP-053 results: add to swing winners or not",
        "",
        f"Run {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M} UTC. {len(tr)} trades (same entries as EXP-052). Profit per "
        "trade as a share of the original position's value, after 5 bps per fill. Same-day ties: stop first.",
        "",
        "| Variant | Mean | Median | Win rate | Avg win | Avg loss | Worst | Best | Added | Exits |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for n in names:
        s = desc[n]
        ex = ", ".join(f"{k} {v:.0%}" for k, v in sorted(s["exits"].items(), key=lambda kv: -kv[1]))
        lines.append(
            f"| {n} | {pc(s['mean'])} | {pc(s['median'])} | {s['win_rate']:.0%} | {pc(s['avg_win'])} | "
            f"{pc(s['avg_loss'])} | {pc(s['worst'])} | {pc(s['best'])} | {s['added']:.0%} | {ex} |"
        )
    lines += [
        "",
        "| Variant vs A | Mean difference | NW t | 2017-20 | 2021-26 | 2024+ | Optimistic | Passes |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for b, v in pairs.items():
        c, o = v["conservative"], v["optimistic"]
        lines.append(
            f"| {b} | {pc(c['mean_diff'])} | {c['t']:.2f} | {pc(c['first_half'])} | {pc(c['second_half'])} | "
            f"{pc(c['recent'])} | {pc(o['mean_diff'])} | **{'yes' if v['passes'] else 'no'}** |"
        )
    lines += ["", f"**Decision under the pre-registered rule: {choice}.**", "", f"Run time {time.time() - t0:.0f}s."]
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
