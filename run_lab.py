"""Research lab: test the always-invested strategy on more history and new assets, and test the
stage 5-8 ideas against it (EXP-020 ... EXP-028; see research/experiments/README.md).

    python run_lab.py --set core               # GLD SLV GDX NEM AEM WPM from 2006 (adds 2006-2013)
    python run_lab.py --set other              # eight precious-metal assets never tested before
    python run_lab.py --set core --combine fv_rolling,cot_flow   # EXP-027, after results exist
    AURUM_OFFLINE=1 python run_lab.py --set core   # synthetic data: checks the code only

Output: research/experiments/results/<date-time>-lab-<set>-<real|synthetic>[...]/
"""

from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from aurum import data, stats
from aurum import strategy as S
from aurum.backtest import combine_sleeves, performance, risk_free_daily, slice_sim
from aurum.config import CFG, config_hash, cost_bps
from aurum.lab import CRISES, SETS, LabCtx, build_lab_variants, periods
from run_experiments import RESULTS, compare

STARTS = {"core": "2006-06-01", "other": "2010-01-01"}


def load_shared(cfg: dict, start: str) -> dict:
    """Cross-asset inputs. Anything that fails is None; variants needing it are dropped and listed."""
    lag = int(cfg["macro"].get("fred_lag_days", 2))
    sources = {
        "gld_close": lambda: data.daily_prices_from("GLD", start, cfg)["Close"],
        "gdx_close": lambda: data.daily_prices_from("GDX", start, cfg)["Close"],
        "gvz": lambda: None if cfg.get("offline") else data.daily_prices_from("^GVZ", start, cfg)["Close"],
        "gold": lambda: data.daily_prices_from("GC=F", start, cfg)["Close"],
        "dxy": lambda: data.daily_prices_from("DX-Y.NYB", start, cfg)["Close"],
        "real_yield": lambda: (
            data.publication_lag(data.fred("DFII10", cfg), lag)
            if not cfg.get("offline")
            else data.synthetic.macro(["real_yield_10y"])["real_yield_10y"]
        ),
        "epu": lambda: (
            data.publication_lag(data.fred("USEPUINDXD", cfg), lag)
            if not cfg.get("offline")
            else data.synthetic.macro(["epu"])["epu"].abs() * 100 + 100
        ),
        "gpr": lambda: data.gpr_daily(cfg),
        "cot_gold": lambda: data.cot_managed_money("gold", cfg),
        "cot_silver": lambda: data.cot_managed_money("silver", cfg),
    }
    shared = {}
    for k, fn in sources.items():
        try:
            shared[k] = fn()
            if shared[k] is not None:
                print(f"  loaded {k}: {len(shared[k])} rows from {shared[k].index[0].date()}", flush=True)
        except Exception as exc:
            data.log_event("error", f"lab:{k}", f"unavailable ({type(exc).__name__}: {exc})")
            print(f"  !! {k} unavailable: {exc}", flush=True)
            shared[k] = None
    return shared


def lab_verdict(dev: dict, dev2x: dict, hold: dict, pre: dict | None, dsr: float) -> str:
    """Pre-registered (README, 'Lab rules'): the usual development rules, then confirmation on BOTH
    the holdout and the pre-2013 period, which no earlier experiment used."""
    d_sh, share, dd_rel = dev["d_sharpe"], dev["share_better"], dev["dd_rel"]
    signal = d_sh >= 0.10 and share >= 0.80 and dev2x["d_sharpe"] >= 0.0
    risk = dd_rel >= 0.20 and d_sh >= -0.05 and dev2x["d_sharpe"] >= -0.05
    if (signal or risk) and dsr >= 0.50:

        def holds(p):
            if p is None:
                return False
            return p["d_sharpe"] >= 0.0 if signal else (p["dd_rel"] >= 0.0 and p["d_sharpe"] >= -0.10)

        h, p = holds(hold), holds(pre)
        if h and p:
            return "KEEP (held on holdout and pre-2013)"
        failed = " and ".join(n for n, ok in (("holdout", h), ("pre-2013", p)) if not ok)
        return f"REJECT (failed on {failed})"
    if d_sh < 0 and dd_rel < 0.20:
        return "REJECT"
    return "INCONCLUSIVE"


def window_stats(sim: S.SimResult, lo, hi) -> tuple[float, float]:
    d = sim.daily.loc[lo:hi]
    if len(d) < 5:
        return np.nan, np.nan
    eq = d["value"] / d["value"].iloc[0]
    return eq.iloc[-1] - 1, (eq / eq.cummax() - 1).min()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=list(SETS), default="core")
    ap.add_argument("--start", help="first date of data (default: core 2006-06-01, other 2010-01-01)")
    ap.add_argument("--tickers", nargs="*")
    ap.add_argument("--combine", help="EXP-027: comma-separated tilt names to combine")
    ap.add_argument("--fill", choices=["open", "close"])
    args = ap.parse_args()
    cfg = copy.deepcopy(CFG)
    if args.fill:
        cfg["strategy"]["fill"] = args.fill
    start = args.start or STARTS[args.set]
    tickers = args.tickers or SETS[args.set]
    run_at = datetime.now(timezone.utc)
    tag = "synthetic" if cfg.get("offline") else "real"
    suffix = (f"-{args.fill}fill" if args.fill else "") + ("-combo" if args.combine else "")
    out = RESULTS / f"{run_at:%Y-%m-%d-%H%M}-lab-{args.set}-{tag}{suffix}"
    out.mkdir(parents=True, exist_ok=True)

    print(f"Loading shared inputs from {start} ...", flush=True)
    shared = load_shared(cfg, start)
    variants = build_lab_variants(args.combine.split(",") if args.combine else None)
    scfg = cfg["strategy"]
    sims = {v.name: {m: {} for m in ("net", "gross", "x2")} for v in variants}
    failed: dict[str, str] = {}
    rf_all = None
    starts = {}
    for t in tickers:
        try:
            prices = data.daily_prices_from(t, start, cfg)
        except Exception as exc:
            data.log_event("error", f"lab:{t}", f"prices unavailable, ticker dropped ({exc})")
            print(f"[{t}] !! prices unavailable, ticker dropped: {exc}", flush=True)
            continue
        prices = prices.iloc[21:]  # first 21 days only warm up the volatility estimate
        rf = data.cash_rate(prices.index, cfg)
        rf_all = rf if rf_all is None else rf_all.combine_first(rf)
        ctx = LabCtx(t, prices, rf, cfg, shared)
        starts[t] = str(prices.index[0].date())
        k = cost_bps(t, cfg)
        print(f"[{t}] {len(prices)} days from {starts[t]}, cost {k:g} bps", flush=True)
        for v in variants:
            try:
                w = v.weight(ctx).reindex(prices.index)
                if v.every > 1:
                    w = w.where(np.arange(len(w)) % v.every == 0)
                cap = v.account / len(tickers) if v.account else None
                for mode, kk in (("net", k), ("gross", 0.0), ("x2", 2 * k)):
                    sims[v.name][mode][t] = S.simulate_weights(
                        prices,
                        w,
                        cost_bps=kk,
                        cash_rate=rf,
                        band=scfg.get("rebalance_band", 0.05),
                        fill=scfg.get("fill", "open"),
                        capital=cap,
                    )
            except Exception as exc:
                failed[v.name] = f"{t}: {type(exc).__name__}: {exc}"
                print(f"[{t}]   !! {v.name} failed: {exc}", flush=True)
    variants = [v for v in variants if v.name not in failed]
    if "vol_hold_gvz" in failed or not variants:
        raise SystemExit("The baseline failed; see errors above.")
    used = list(sims["vol_hold_gvz"]["net"])
    weight = S.sleeve_weight(len(used), scfg["max_position_pct"])
    port = {
        v.name: {m: combine_sleeves(sims[v.name][m], {t: weight for t in used}, rf_all) for m in sims[v.name]}
        for v in variants
    }
    first = port["vol_hold_gvz"]["net"].daily.index[0]
    per = periods(first)
    if first >= per["pre"][1]:
        per.pop("pre")
    rf = rf_all

    # overfitting statistics across trial variants, development period
    lo, hi = per["dev"]
    trials = [v.name for v in variants if v.trial]
    dev_ex = pd.DataFrame({n: slice_sim(port[n]["net"], lo, hi).daily["ret"] for n in port})
    dev_ex = dev_ex.sub(risk_free_daily(rf, dev_ex.index), axis=0)
    trial_sr = [dev_ex[c].mean() / dev_ex[c].std(ddof=1) for c in trials]
    pbo = stats.probability_of_backtest_overfitting(dev_ex[trials]) if len(trials) > 2 else {}

    rows, crisis_rows, yearly = [], [], {}
    for v in variants:
        r = {"exp": v.exp, "variant": v.name, "description": v.description, "trial": v.trial}
        cmp = {}
        for p, (a, b) in per.items():
            for mode in ("net", "x2"):
                cmp[(p, mode)] = compare(port[v.name][mode], port["vol_hold_gvz"][mode], rf, a, b, cfg)
            bh = compare(port[v.name]["net"], port["buy_hold"]["net"], rf, a, b, cfg)
            for kk in (
                "cagr",
                "volatility",
                "sharpe",
                "max_drawdown",
                "turnover_per_year",
                "costs_per_year",
                "d_sharpe",
                "share_better",
                "dd_rel",
            ):
                r[f"{p}_{kk}"] = cmp[(p, "net")][kk]
            r[f"{p}_x2_d_sharpe"] = cmp[(p, "x2")]["d_sharpe"]
            r[f"{p}_vs_bh_d_sharpe"] = bh["d_sharpe"]
            r[f"{p}_vs_bh_share_better"] = bh["share_better"]
        full = performance(port[v.name]["net"], rf)
        r.update({f"full_{kk}": full.get(kk) for kk in ("cagr", "volatility", "sharpe", "max_drawdown")})
        r["rebalances_per_year"] = np.mean(
            [len(getattr(s, "rebalances", [])) / (len(s.daily) / 252) for s in sims[v.name]["net"].values()]
        )
        r["dsr_dev"] = stats.deflated_sharpe(dev_ex[v.name], trial_sr) if v.trial else np.nan
        if v.name == "vol_hold_gvz":
            r["verdict"] = "baseline"
        elif not v.trial:
            r["verdict"] = "descriptive" if v.exp != "REF" else "reference"
        else:
            r["verdict"] = lab_verdict(
                cmp[("dev", "net")],
                cmp[("dev", "x2")],
                cmp.get(("holdout", "net")),
                cmp.get(("pre", "net")),
                r["dsr_dev"],
            )
        rows.append(r)
        for name, (a, b) in CRISES.items():
            ret, mdd = window_stats(port[v.name]["net"], a, b)
            crisis_rows.append({"variant": v.name, "window": name, "return": ret, "max_drawdown": mdd})
        d = port[v.name]["net"].daily
        yearly[v.name] = (1 + d["ret"]).groupby(d.index.year).prod() - 1
    table = pd.DataFrame(rows)
    table.to_csv(out / "variants.csv", index=False)
    crises = pd.DataFrame(crisis_rows)
    crises.to_csv(out / "crises.csv", index=False)
    years = pd.DataFrame(yearly)
    years.to_csv(out / "yearly.csv")

    meta = {
        "run_at": run_at.isoformat(timespec="seconds"),
        "data": tag,
        "set": args.set,
        "tickers": used,
        "ticker_starts": starts,
        "portfolio_start": str(first.date()),
        "periods": {
            k: [str(a.date()) if a is not None else None, str(b.date()) if b is not None else None]
            for k, (a, b) in per.items()
        },
        "fill": scfg.get("fill", "open"),
        "config_hash": config_hash(cfg),
        "n_trials": len(trials),
        "pbo_development": pbo,
        "failed_variants": failed,
        "combine": args.combine,
        "data_events": data.DATA_EVENTS,
    }
    (out / "metadata.json").write_text(json.dumps(meta, indent=2, default=str))
    write_summary(out, table, crises, years, meta)
    print(f"\nWrote {out}")


def write_summary(out, t: pd.DataFrame, crises: pd.DataFrame, years: pd.DataFrame, meta: dict):
    def f(x, pct=False):
        if x is None or (isinstance(x, float) and not np.isfinite(x)):
            return "–"
        return f"{x:+.1%}" if pct else f"{x:+.2f}"

    P = list(meta["periods"])
    L = [f"# Lab results: {meta['set']} set, {meta['run_at'][:16]} UTC ({meta['data']})", ""]
    if meta["data"] == "synthetic":
        L += ["> **SYNTHETIC DATA.** Checks that the code runs. These numbers say nothing about real markets.", ""]
    L += [
        f"Assets: {', '.join(meta['tickers'])}; portfolio from {meta['portfolio_start']} (common start). "
        f"Periods: " + "; ".join(f"{k} {a} → {b or 'now'}" for k, (a, b) in meta["periods"].items()) + ". "
        f"Orders fill at the next {meta['fill']}; net of costs; equal sleeves. Baseline = `vol_hold_gvz` "
        f"(the traded strategy). {meta['n_trials']} trial variants; PBO (development) "
        f"{meta['pbo_development'].get('pbo', float('nan')):.0%}.",
        "",
        "## Return, risk and Sharpe by period",
        "",
        "| Exp | Variant | " + " | ".join(f"{p} CAGR | {p} Sharpe | {p} max DD" for p in P) + " | Rebal./yr |",
        "|---|---|" + "---|---|---|" * len(P) + "---|",
    ]
    for _, r in t.iterrows():
        cells = " | ".join(
            f"{f(r[f'{p}_cagr'], True)} | {f(r[f'{p}_sharpe'])} | {f(r[f'{p}_max_drawdown'], True)}" for p in P
        )
        L.append(f"| {r['exp']} | {r['variant']} | {cells} | {r['rebalances_per_year']:.0f} |")
    L += [
        "",
        "## Versus the traded strategy (ΔSharpe; 'better' = share of block-bootstrap resamples)",
        "",
        "| Exp | Variant | "
        + " | ".join(f"{p} ΔSharpe | {p} better" for p in P)
        + " | dev ΔSharpe 2× cost | DSR | Verdict |",
        "|---|---|" + "---|---|" * len(P) + "---|---|---|",
    ]
    for _, r in t.iterrows():
        cells = " | ".join(
            f"{f(r[f'{p}_d_sharpe'])} | {r[f'{p}_share_better']:.0%}"
            if np.isfinite(r[f"{p}_share_better"])
            else f"{f(r[f'{p}_d_sharpe'])} | –"
            for p in P
        )
        dsr = f"{r['dsr_dev']:.2f}" if np.isfinite(r["dsr_dev"]) else "–"
        L.append(f"| {r['exp']} | {r['variant']} | {cells} | {f(r['dev_x2_d_sharpe'])} | {dsr} | {r['verdict']} |")
    L += [
        "",
        "## Versus simply holding (buy & hold): ΔSharpe and share of resamples better",
        "",
        "| Variant | " + " | ".join(f"{p} ΔSharpe | {p} better" for p in P) + " |",
        "|---|" + "---|---|" * len(P),
    ]
    for _, r in t.iterrows():
        cells = " | ".join(
            f"{f(r[f'{p}_vs_bh_d_sharpe'])} | "
            + (f"{r[f'{p}_vs_bh_share_better']:.0%}" if np.isfinite(r[f"{p}_vs_bh_share_better"]) else "–")
            for p in P
        )
        L.append(f"| {r['variant']} | {cells} |")
    show = [
        v
        for v in ("vol_hold_gvz", "vol_hold_21d", "buy_hold", "risk_10", "risk_20", "risk_25", "risk_30")
        if v in set(crises["variant"])
    ]
    L += [
        "",
        "## Stress windows (return / worst fall inside the window)",
        "",
        "| Window | " + " | ".join(show) + " |",
        "|---|" + "---|" * len(show),
    ]
    for w in crises["window"].unique():
        c = crises[crises["window"] == w].set_index("variant")
        L.append(
            f"| {w} | "
            + " | ".join(f"{f(c.loc[v, 'return'], True)} / {f(c.loc[v, 'max_drawdown'], True)}" for v in show)
            + " |"
        )
    cols = [v for v in ("vol_hold_gvz", "buy_hold", "risk_20", "risk_25") if v in years]
    L += ["", "## Calendar-year returns", "", "| Year | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for y, r in years[cols].iterrows():
        L.append(f"| {y} | " + " | ".join(f(r[c], True) for c in cols) + " |")
    if meta["failed_variants"]:
        L += ["", "**Variants dropped because they raised errors:**", ""]
        L += [f"- `{k}`: {v}" for k, v in meta["failed_variants"].items()]
    bad = [e for e in meta["data_events"] if e.get("level") == "error"]
    if bad:
        L += ["", "**Data problems:**", ""] + [f"- {e['source']}: {e['message']}" for e in bad]
    L += ["", "Verdicts are proposals. A change is only adopted when recorded in research/decisions.md."]
    (out / "summary.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
