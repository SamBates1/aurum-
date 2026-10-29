"""Run every pre-registered experiment (research/experiments/EXP-*.md) against the baseline.

    python run_experiments.py               # real data, full settings (slow: roughly 20-40 min)
    python run_experiments.py --quick       # fewer retrains, for a fast check
    AURUM_OFFLINE=1 python run_experiments.py --quick   # synthetic data: tests the code only

Identical tickers, dates, costs, fills and accounting for every variant. Each is run
net of costs, gross (0 bps) and at 2x costs. Verdicts follow the acceptance rules in
research/experiments/README.md, which were written before any results existed.

Output: research/experiments/results/<date>-<real|synthetic>/  (summary.md, CSVs, metadata)
Synthetic runs are git-ignored; real runs are meant to be committed.

Progress is checkpointed after each ticker (research/experiments/results/.checkpoints/, git-ignored):
if the run is interrupted, run the same command again and it continues where it stopped.
"""

from __future__ import annotations

import argparse
import copy
import json
import pickle
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from aurum import data, stats
from aurum import strategy as S
from aurum.backtest import combine_sleeves, performance, risk_free_daily, slice_sim
from aurum.config import CFG, ROOT, all_tickers, code_fingerprint, config_hash, cost_bps, git_commit, is_equity
from aurum.experiments import Context, build_variants
from aurum.pipeline import research

RESULTS = ROOT / "research" / "experiments" / "results"


def verdict(dev: dict, dev2x: dict, hold: dict, dsr: float) -> str:
    """Acceptance rules from research/experiments/README.md (pre-registered)."""
    d_sh, share, dd_rel = dev["d_sharpe"], dev["share_better"], dev["dd_rel"]
    signal_path = d_sh >= 0.10 and share >= 0.80 and dev2x["d_sharpe"] >= 0.0
    risk_path = dd_rel >= 0.20 and d_sh >= -0.05 and dev2x["d_sharpe"] >= -0.05
    if (signal_path or risk_path) and dsr >= 0.50:
        if signal_path:
            holds = hold["d_sharpe"] >= 0.0
        else:
            holds = hold["dd_rel"] >= 0.0 and hold["d_sharpe"] >= -0.10
        return "KEEP (held on holdout)" if holds else "REJECT (failed on holdout)"
    if d_sh < 0 and dd_rel < 0.20:
        return "REJECT"
    return "INCONCLUSIVE"


def compare(variant: S.SimResult, base: S.SimResult, rf, lo, hi, cfg) -> dict:
    v, b = slice_sim(variant, lo, hi), slice_sim(base, lo, hi)
    pv, pb = performance(v, rf), performance(b, rf)
    ex_v = v.daily["ret"] - risk_free_daily(rf, v.daily.index)
    ex_b = b.daily["ret"] - risk_free_daily(rf, b.daily.index)
    rc = cfg["research"]
    boot = stats.bootstrap_sharpe(ex_v, ex_b, rc["bootstrap_block_days"], rc["bootstrap_reps"], rc["seed"])
    # drawdown per unit of volatility, so merely holding more cash doesn't count as better risk control
    mdd_v = abs(pv.get("max_drawdown", np.nan)) / (pv.get("volatility") or np.nan)
    mdd_b = abs(pb.get("max_drawdown", np.nan)) / (pb.get("volatility") or np.nan)
    return {
        **{
            k: pv.get(k)
            for k in (
                "cagr",
                "volatility",
                "sharpe",
                "sortino",
                "max_drawdown",
                "calmar",
                "trades",
                "time_in_market",
                "turnover_per_year",
                "costs_per_year",
            )
        },
        "d_sharpe": (pv.get("sharpe") or np.nan) - (pb.get("sharpe") or np.nan),
        "share_better": boot.get("share_resamples_better", np.nan),
        "diff_p05": boot.get("diff_p05", np.nan),
        "diff_p95": boot.get("diff_p95", np.nan),
        "dd_rel": 1 - mdd_v / mdd_b if mdd_b else np.nan,
        "psr": stats.probabilistic_sharpe(ex_v),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="retrain yearly and use fewer bootstrap draws")
    ap.add_argument("--tickers", nargs="*", help="subset of tickers")
    ap.add_argument("--baseline", default="baseline", help="variant every other variant is compared with")
    ap.add_argument("--exps", help="comma-separated experiment IDs to run (BASE/REF rows always included)")
    ap.add_argument(
        "--fill", choices=["open", "close"], help="override order fills (EXP-010: 'close' = next-day close)"
    )
    args = ap.parse_args()
    cfg = copy.deepcopy(CFG)
    if args.quick:
        cfg["model"]["retrain_every_days"] = 252
        cfg["research"]["bootstrap_reps"] = 200
    if args.fill:
        cfg["strategy"]["fill"] = args.fill
    run_at = datetime.now(timezone.utc)
    tag = "synthetic" if cfg.get("offline") else "real"
    suffix = ("-quick" if args.quick else "") + (f"-{args.fill}fill" if args.fill else "")
    suffix += f"-vs-{args.baseline}" if args.baseline != "baseline" else ""
    out = RESULTS / f"{run_at:%Y-%m-%d-%H%M}-{tag}{suffix}"  # time in the name: runs never overwrite each other
    out.mkdir(parents=True, exist_ok=True)

    variants = build_variants()
    if args.exps:
        keep = set(args.exps.split(","))
        variants = [v for v in variants if v.exp in keep or v.exp in ("BASE", "REF") or v.name == args.baseline]
    if args.baseline not in [v.name for v in variants]:
        raise SystemExit(f"baseline variant {args.baseline!r} not found")
    tickers = args.tickers or all_tickers(cfg)
    macro = data.macro_daily(cfg)
    gdx = data.daily_prices(cfg["universe"]["miner_benchmark"], cfg=cfg)["Close"]
    # cross-ticker inputs for stage 3-4 variants (ranking, implied volatility); all point-in-time
    xs_closes = pd.DataFrame({t: data.daily_prices(t, cfg=cfg)["Close"] for t in all_tickers(cfg)}).sort_index()
    try:
        gvz = data.daily_prices("^GVZ", cfg=cfg)["Close"] if not cfg.get("offline") else None
    except Exception as exc:
        data.log_event("error", "GVZ", f"unavailable, GVZ variants will be dropped ({exc})")
        gvz = None
    from aurum.volatility import realised_21d

    extras = {"xs_closes": xs_closes, "gvz": gvz, "gld_vol": realised_21d(xs_closes[cfg["universe"]["core"][0]])}
    sims = {v.name: {m: {} for m in ("net", "gross", "x2")} for v in variants}
    rf = None
    failed: dict[str, str] = {}  # variant -> error; a failing variant is dropped, never silently replaced
    # Progress is saved after each ticker, so an interrupted run (e.g. a Codespaces timeout)
    # resumes where it stopped. Checkpoints are keyed by config, so changed settings start afresh.
    import hashlib

    vkey = hashlib.sha256(",".join(v.name for v in variants).encode()).hexdigest()[:8]
    # audit 2026-10-29: the key now includes the code fingerprint, so changed code never reuses old checkpoints
    ckpt = (
        RESULTS
        / ".checkpoints"
        / f"{tag}{'-quick' if args.quick else ''}-{config_hash(cfg)}-{code_fingerprint()}-{vkey}"
    )
    ckpt.mkdir(parents=True, exist_ok=True)
    started = time.time()
    for n_done, t in enumerate(tickers):
        path = ckpt / f"{t}.pkl"
        if path.exists():
            saved = pickle.loads(path.read_bytes())
            print(f"[{t}] loaded from checkpoint (already done)", flush=True)
        else:
            print(f"[{t}] research ...", flush=True)
            res = research(t, macro, cfg)
            ctx = Context(t, res, cfg, gdx_close=gdx, is_equity=is_equity(t, cfg), extras=extras)
            base_cost = cost_bps(t, cfg)
            saved = {"rf": res.rf, "sims": {}, "failed": {}}
            for v in variants:
                print(f"[{t}]   {v.exp} {v.name}", flush=True)
                try:
                    saved["sims"][v.name] = {
                        mode: v.run(ctx, k) for mode, k in (("net", base_cost), ("gross", 0.0), ("x2", 2 * base_cost))
                    }
                except Exception as exc:  # record and carry on: one broken variant must not lose the whole run
                    saved["failed"][v.name] = f"{t}: {type(exc).__name__}: {exc}"
                    print(f"[{t}]   !! {v.name} failed: {exc}", flush=True)
            path.write_bytes(pickle.dumps(saved))
            mins = (time.time() - started) / 60
            left = len(tickers) - n_done - 1
            print(f"[{t}] saved. {mins:.0f} min elapsed, {left} ticker(s) left", flush=True)
        rf = saved["rf"] if rf is None else rf
        failed.update(saved["failed"])
        for name, by_mode in saved["sims"].items():
            for mode, sim in by_mode.items():
                sims[name][mode][t] = sim
    for name, err in failed.items():
        print(f"Dropping variant {name} (failed on {err})")
    if args.baseline in failed:
        raise SystemExit("The baseline itself failed; see the error above.")
    variants = [v for v in variants if v.name not in failed]
    sims = {k: v for k, v in sims.items() if k not in failed}

    weight = S.sleeve_weight(len(tickers), cfg["strategy"]["max_position_pct"])
    port = {name: {m: combine_sleeves(d[m], {t: weight for t in d[m]}, rf) for m in d} for name, d in sims.items()}
    start = port[args.baseline]["net"].daily.index[0]  # common out-of-sample start across tickers
    hold_start = pd.Timestamp(cfg["research"]["holdout_start"])
    periods = {"development": (start, hold_start - pd.Timedelta(days=1)), "holdout": (hold_start, None)}

    # overfitting statistics across ALL variants tried (development period, net)
    lo, hi = periods["development"]
    dev_rets = pd.DataFrame({n: slice_sim(p["net"], lo, hi).daily["ret"] for n, p in port.items()})
    dev_ex = dev_rets.sub(risk_free_daily(rf, dev_rets.index), axis=0)
    # reference rows (exp "REF", e.g. buy & hold) are shown for comparison but are not trials
    trial_cols = [v.name for v in variants if v.exp != "REF"]
    trial_sr = [dev_ex[c].mean() / dev_ex[c].std(ddof=1) for c in trial_cols]
    pbo = stats.probability_of_backtest_overfitting(dev_ex[trial_cols])

    rows = []
    for v in variants:
        r = {"exp": v.exp, "variant": v.name, "description": v.description, "applies_to": v.applies_to}
        res_p = {}
        for period, (a, b) in periods.items():
            for mode in ("net", "gross", "x2"):
                res_p[(period, mode)] = compare(port[v.name][mode], port[args.baseline][mode], rf, a, b, cfg)
        for (period, mode), d in res_p.items():
            for k, val in d.items():
                r[f"{period}_{mode}_{k}"] = val
        if "buy_hold" in port:  # profit check: how does each variant compare with simply holding?
            for period, (a, b) in periods.items():
                vb = compare(port[v.name]["net"], port["buy_hold"]["net"], rf, a, b, cfg)
                r[f"{period}_net_vs_bh_d_sharpe"] = vb["d_sharpe"]
                r[f"{period}_net_vs_bh_d_cagr"] = (vb["cagr"] or np.nan) - (
                    performance(slice_sim(port["buy_hold"]["net"], a, b), rf).get("cagr") or np.nan
                )
        r["dsr_dev"] = stats.deflated_sharpe(dev_ex[v.name], trial_sr)
        r["verdict"] = (
            "baseline"
            if v.name == args.baseline
            else "reference"
            if v.exp == "REF"
            else verdict(
                res_p[("development", "net")], res_p[("development", "x2")], res_p[("holdout", "net")], r["dsr_dev"]
            )
        )
        rows.append(r)
    table = pd.DataFrame(rows)
    table.to_csv(out / "variants.csv", index=False)

    per_ticker = pd.DataFrame(
        [
            {
                "variant": n,
                "ticker": t,
                "dev_net_sharpe": performance(slice_sim(s, *periods["development"]), rf).get("sharpe"),
                "hold_net_sharpe": performance(slice_sim(s, *periods["holdout"]), rf).get("sharpe"),
            }
            for n, d in sims.items()
            for t, s in d["net"].items()
        ]
    )
    per_ticker.to_csv(out / "per_ticker.csv", index=False)

    meta = {
        "run_at": run_at.isoformat(timespec="seconds"),
        "data": tag,
        "quick": args.quick,
        "tickers": tickers,
        "config_hash": config_hash(cfg),
        "code_fingerprint": code_fingerprint(),
        "git_commit": git_commit(),
        "data_fingerprint": data.data_fingerprint({t: xs_closes[t].dropna() for t in xs_closes}),
        "n_trials": len([v for v in variants if v.exp != "REF"]),
        "fill": cfg["strategy"].get("fill", "open"),
        "pbo_development": pbo,
        "development": [str(periods["development"][0].date()), str(periods["development"][1].date())],
        "holdout_start": str(hold_start.date()),
        "data_events": data.DATA_EVENTS,
        "failed_variants": failed,
        "baseline": args.baseline,
    }
    (out / "metadata.json").write_text(json.dumps(meta, indent=2, default=str))
    write_summary(out, table, meta)
    print(f"\nWrote {out}")


def write_summary(out: Path, t: pd.DataFrame, meta: dict):
    def f(x, pct=False):
        if x is None or (isinstance(x, float) and not np.isfinite(x)):
            return "–"
        return f"{x:+.1%}" if pct else f"{x:+.2f}"

    lines = [f"# Experiment results: {meta['run_at'][:10]} ({meta['data']}{', quick' if meta['quick'] else ''})", ""]
    if meta["data"] == "synthetic":
        lines += ["> **SYNTHETIC DATA.** Checks that the code runs. These numbers say nothing about real markets.", ""]
    pbo = meta["pbo_development"]
    lines += [
        f"Tickers: {', '.join(meta['tickers'])}. Development {meta['development'][0]} → {meta['development'][1]}; "
        f"holdout from {meta['holdout_start']}. Config `{meta['config_hash']}`, orders filled at the next "
        f"{meta.get('fill', 'open')}. {meta['n_trials']} variants tried (reference rows excluded).",
        "",
        "**Probability of backtest overfitting across all variants (development):** "
        f"{pbo.get('pbo', float('nan')):.0%} "
        f"({pbo.get('n_splits', 0)} CSCV splits). Around 50% means picking the best-looking variant is no better "
        "than chance.",
        "",
        f"Portfolio level, net of costs. ΔSharpe is vs the baseline (`{meta.get('baseline', 'baseline')}`) "
        "over identical dates; 'better' is the share of "
        "block-bootstrap resamples in which the variant beat the baseline; DSR is the deflated Sharpe ratio "
        "(probability the Sharpe is real after allowing for all variants tried).",
        "",
        "| Exp | Variant | Dev Sharpe | Dev ΔSharpe | better | Dev ΔSharpe 2× cost | Dev max DD | Holdout ΔSharpe | "
        "DSR | Verdict |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for _, r in t.iterrows():
        lines.append(
            f"| {r['exp']} | {r['variant']} | {f(r['development_net_sharpe'])} | "
            f"{f(r['development_net_d_sharpe'])} | {r['development_net_share_better']:.0%} | "
            f"{f(r['development_x2_d_sharpe'])} | {f(r['development_net_max_drawdown'], True)} | "
            f"{f(r['holdout_net_d_sharpe'])} | {r['dsr_dev']:.2f} | {r['verdict']} |"
            if np.isfinite(r["development_net_share_better"])
            else f"| {r['exp']} | {r['variant']} | {f(r['development_net_sharpe'])} | – | – | – | "
            f"{f(r['development_net_max_drawdown'], True)} | – | {r['dsr_dev']:.2f} | {r['verdict']} |"
        )
    if "development_net_vs_bh_d_sharpe" in t:
        lines += [
            "",
            "## Profit check: every variant vs simply holding (buy & hold), net of costs",
            "",
            "| Exp | Variant | Dev CAGR | Dev Sharpe | Dev max DD | Dev ΔSharpe vs B&H | Dev ΔCAGR vs B&H | "
            "Holdout CAGR | Holdout max DD | Holdout ΔSharpe vs B&H |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
        for _, r in t.iterrows():
            lines.append(
                f"| {r['exp']} | {r['variant']} | {f(r['development_net_cagr'], True)} | "
                f"{f(r['development_net_sharpe'])} | {f(r['development_net_max_drawdown'], True)} | "
                f"{f(r['development_net_vs_bh_d_sharpe'])} | {f(r['development_net_vs_bh_d_cagr'], True)} | "
                f"{f(r['holdout_net_cagr'], True)} | {f(r['holdout_net_max_drawdown'], True)} | "
                f"{f(r['holdout_net_vs_bh_d_sharpe'])} |"
            )
    if meta.get("failed_variants"):
        lines += ["", "**Variants dropped because they raised errors (fix and re-run):**", ""]
        lines += [f"- `{k}`: {v}" for k, v in meta["failed_variants"].items()]
    lines += ["", "Verdicts are proposals. A change is only adopted when recorded in research/decisions.md."]
    (out / "summary.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
