"""Strategy Designer on real data, run on GitHub's machines ("designer:" line in research/experiments/RUN).

    python run_designer.py                 # every saved strategy: backtest, Fair Test, charts, reproduction check
    python run_designer.py --ids a,b       # only these strategy ids

Writes:
  research/fairtests/<date>-<id>-<hash>.md/.json     one Fair Test report per strategy (real data only)
  research/designer/<date>-<time>-real/summary.md     results, reproduction check against EXP-045's code path,
                                                      decision charts (HTML, last three years) and metadata
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from aurum import data
from aurum import designer as D
from aurum import designer_charts as DC
from aurum import engine as E
from aurum import fairtest as FT
from aurum import registry as R
from aurum import spec as SP
from aurum import strategy as S
from aurum import xlab as X
from aurum.config import CFG, ROOT, code_fingerprint, config_hash, git_commit

OUT = ROOT / "research" / "designer"


def reproduction_check(lib: dict, prices: dict, rf) -> list[dict]:
    """The designer engine must give exactly the same account values as the code that produced EXP-045."""
    idx = X.common_index({t: prices[t] for t in ("SPY", "GLD")})
    p2 = {t: prices[t].reindex(idx) for t in ("SPY", "GLD")}
    base = pd.DataFrame({"SPY": 0.7, "GLD": 0.3}, index=idx)
    first = idx.to_series().groupby([idx.year, idx.month]).transform("min") == idx.to_series()
    cap = pd.DataFrame({t: S.vol_target_weight(X.realised_21d(p2[t]["Close"]), 0.20) for t in ("SPY", "GLD")})
    trend = X.above_sma(p2["SPY"]["Close"], 200).fillna(1.0)
    ref = {
        "spy-gld-70-30-monthly": (base.where(first, np.nan), 0.0),
        "spy-gld-70-30-risk-cap": (base * cap, 0.05),
        "example-70-30-spy-trend-filter": (base.assign(SPY=0.7 * trend), 0.05),
    }
    out = []
    for sid, (tgt, band) in ref.items():
        if sid not in lib:
            continue
        a = E.run_spec(lib[sid], p2, rf, capital=1.0, index=idx).daily["value"]
        b = X.run(p2, tgt, rf, band=band, fill="open").daily["value"]
        diff = float(np.max(np.abs(a.to_numpy() - b.to_numpy())))
        out.append({"strategy": sid, "max_abs_difference": diff, "identical": diff < 1e-9})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", help="comma-separated strategy ids (default: all saved strategies)")
    args = ap.parse_args()
    cfg = CFG
    real = not cfg.get("offline")
    lib = SP.library()
    ids = args.ids.split(",") if args.ids else list(lib)
    run_at = datetime.now(timezone.utc)
    out = OUT / f"{run_at:%Y-%m-%d-%H%M}-{'real' if real else 'synthetic'}"
    if not real:
        out = ROOT / "logs" / "designer-synthetic" / out.name
    out.mkdir(parents=True, exist_ok=True)
    tickers = sorted({t for i in ids for t in SP.assets_needed(lib[i])} | {"SPY", "GLD"})
    prices, errors = D.load_prices(tickers, SP.DEFAULT_START, cfg)
    if errors:
        print("Data errors:", errors)
        sys.exit(1)
    allidx = None
    for p in prices.values():
        allidx = p.index if allidx is None else allidx.union(p.index)
    rf = data.cash_rate(allidx, cfg)
    label = D.data_label(prices, cfg)
    print(label)

    rep = reproduction_check(lib, prices, rf)
    for r in rep:
        print(
            f"reproduction {r['strategy']}: max difference {r['max_abs_difference']:.2e} -> "
            f"{'IDENTICAL' if r['identical'] else 'DIFFERENT'}"
        )

    reg = R.Registry(Path(tempfile.mkdtemp()) / "registry.sqlite", cfg)
    spy = E.run_spec(lib["spy-buy-and-hold"], prices, rf) if "spy-buy-and-hold" in lib else None
    mix = E.run_spec(lib["spy-gld-70-30-monthly"], prices, rf) if "spy-gld-70-30-monthly" in lib else None
    lines = [
        f"# Strategy Designer results ({run_at:%Y-%m-%d %H:%M} UTC, {'real data' if real else 'SYNTHETIC data'})",
        "",
        f"{label}. Every number is a historical backtest net of costs (one account, next-open "
        "fills, T-bill on cash, no borrowing).",
        f"Code {code_fingerprint()}, commit {git_commit()}, config {config_hash()}.",
        "",
        "## Reproduction check (designer engine vs the EXP-045 code path)",
        "| Strategy | Max difference in account value | Result |",
        "|---|---|---|",
    ]
    lines += [
        f"| {r['strategy']} | {r['max_abs_difference']:.2e} | {'identical' if r['identical'] else '**DIFFERENT**'} |"
        for r in rep
    ]
    lines += [
        "",
        "## Results (full history and by period)",
        "| Strategy | Period | Dates | CAGR | Sharpe | Worst fall | Volatility | Costs/yr | Orders/yr |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    meta = {
        "run_at": run_at.isoformat(),
        "data_label": label,
        "code": code_fingerprint(),
        "commit": git_commit(),
        "data": data.data_fingerprint(prices),
        "strategies": {},
    }
    for sid in ids:
        s = lib[sid]
        run = E.run_spec(s, prices, rf)
        idx = run.daily.index
        per = {"full": (None, None), **{k: v for k, v in FT.periods(idx).items()}}
        for pn, (lo, hi) in per.items():
            sm = E.summary(run, lo, hi)
            if "cagr" not in sm:
                continue
            lines.append(
                f"| {s['name']} | {pn} | {sm['start']} to {sm['end']} | {sm['cagr']:.1%} | "
                f"{sm['sharpe']:.2f} | {sm['max_drawdown']:.1%} | "
                f"{sm['volatility']:.1%} | {sm['costs_per_year']:.2%} | {sm['orders_per_year']:.1f} |"
            )
        meta["strategies"][sid] = {
            "spec_hash": SP.spec_hash(s),
            "summary": {k: str(v) for k, v in E.summary(run).items()},
        }
        if sid != "spy-buy-and-hold":
            res = FT.run_fair_test(s, prices, rf, registry=reg, library=lib, cfg=cfg, data_label=label)
            path = FT.save_report(res) if real else FT.save_report(res, out / "fairtests")
            print(f"Fair Test {sid}: {res['status'].upper()} ({res['explanation']}) -> {path}")
            meta["strategies"][sid]["fair_test"] = {
                "status": res["status"],
                "explanation": res["explanation"],
                "report": str(path.relative_to(ROOT)),
            }
        focus = "GLD" if s["sizing"]["method"] != "fixed" else s["universe"][0]
        bench = {
            n: r
            for n, r in (("SPY buy & hold", spy), ("70/30 monthly", mix))
            if r is not None and SP.spec_hash(r.spec) != SP.spec_hash(s)
        }
        fig = DC.decision_chart(run, focus, bench, start=idx[-1] - pd.DateOffset(years=3), data_label=label)
        fig.write_html(out / f"chart-{sid}.html", include_plotlyjs="cdn")
    lines += ["", "## Fair Test verdicts", "| Strategy | Verdict | Why | Report |", "|---|---|---|---|"]
    for sid, m in meta["strategies"].items():
        if "fair_test" in m:
            ft = m["fair_test"]
            lines.append(
                f"| {lib[sid]['name']} | **{ft['status'].upper()}** | {ft['explanation']} | "
                f"[{Path(ft['report']).name}](../../../{ft['report']}) |"
            )
    lines += [
        "",
        "## Downturns",
        "| Strategy | 2008-09 recession | 2020 Covid crash | 2022 rate rises |",
        "|---|---|---|---|",
    ]
    for sid in ids:
        run = E.run_spec(lib[sid], prices, rf)
        cells = []
        for a, b in (("2007-12-01", "2009-06-30"), ("2020-02-01", "2020-04-30"), ("2022-01-01", "2022-10-31")):
            ret, mdd = E.window_return(run, a, b)
            cells.append(f"{ret:+.1%} (worst {mdd:.1%})")
        lines.append(f"| {lib[sid]['name']} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "Decision charts (last three years, open in a browser): "
        + ", ".join(f"[{p.name}]({p.name})" for p in sorted(out.glob("chart-*.html"))),
    ]
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    (out / "metadata.json").write_text(json.dumps(meta, indent=1, default=str))
    print(f"Wrote {out / 'summary.md'}")
    if not all(r["identical"] for r in rep):
        sys.exit(2)


if __name__ == "__main__":
    main()
