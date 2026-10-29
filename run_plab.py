"""Portfolio research lab: entries, scaling, stops, sizing and risk rules tested in one account
(EXP-032 ... EXP-036; brief of 2026-10-29; rules in research/experiments/README.md, 'Research lab').

    python run_plab.py --set core              # GLD SLV GDX NEM AEM WPM from 2006
    python run_plab.py --set other             # eight precious-metal assets never used in design
    python run_plab.py --set core --fill close
    AURUM_OFFLINE=1 python run_plab.py --set core   # synthetic: checks the code only

Output: research/experiments/results/<date-time>-plab-<set>-<real|synthetic>[...]/ with summary.md, CSVs and charts.
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
from aurum.config import CFG, code_fingerprint, config_hash, cost_bps, git_commit
from aurum.lab import CRISES, SETS, LabCtx, periods
from aurum.plab import PortCtx, build_port_variants, extra_stats, rolling_window_returns
from aurum.portfolio import simulate_portfolio
from run_experiments import RESULTS, compare
from run_lab import STARTS, lab_verdict, load_shared, window_stats


def as_sim(pr) -> S.SimResult:
    d = pr.daily.copy()
    d["invested"] = (d["exposure"] > 1e-9).astype(float)
    d["shares"] = np.nan
    empty = pd.DataFrame(columns=["entry_date", "exit_reason", "pnl", "ret", "days", "entry_value"])
    return S.SimResult(d, empty)


def run_variant(v, pc: PortCtx, prices, costs, rf, scfg, mult=1.0, target=None, start=None, horizon=None):
    tgt = v.target(pc) if target is None else target
    sched = v.schedule or scfg.get("rebalance", "daily")
    if v.initial_only:
        tgt = tgt.where(pd.Series(np.arange(len(tgt)) == 0, index=tgt.index), np.nan)
    else:
        tgt = tgt.where(S.rebalance_days(tgt.index, sched), np.nan)
    if start is not None:
        tgt = tgt.loc[start:]
        if horizon:
            tgt = tgt.iloc[:horizon]
        if v.initial_only:
            tgt.iloc[0] = v.target(pc).loc[tgt.index[0]]
    return simulate_portfolio(
        {t: prices[t].loc[tgt.index[0] : tgt.index[-1]] for t in pc.tickers},
        tgt,
        cost_bps={t: costs[t] * mult for t in pc.tickers},
        cash_rate=rf,
        band=scfg.get("rebalance_band", 0.05) * pc.sleeve,  # the band is in sleeve units, as in the paper trader
        fill=scfg.get("fill", "open"),
        overlay=v.overlay() if v.overlay else None,
    )


def regimes(pc: PortCtx, shared) -> pd.DataFrame:
    """Descriptive market states from GLD (trend) and gold implied volatility (or GLD's realised vol)."""
    g = pc.ctxs.get("GLD") or next(iter(pc.ctxs.values()))
    c = g.close.reindex(pc.index)
    ma, r6 = c.rolling(200).mean(), c.pct_change(126)
    trend = pd.Series("sideways", index=pc.index)
    trend[(c > ma) & (r6 > 0.05)] = "bull"
    trend[(c < ma) & (r6 < -0.05)] = "bear"
    trend[ma.isna()] = np.nan
    vol = shared.get("gvz")
    vol = g.on_index(vol) if vol is not None else g.vol21 * 100
    vol = vol.reindex(pc.index)
    lo, hi = vol.quantile([1 / 3, 2 / 3])
    vreg = pd.Series("medium vol", index=pc.index)
    vreg[vol <= lo] = "low vol"
    vreg[vol >= hi] = "high vol"
    vreg[vol.isna()] = np.nan
    vlm = pd.DataFrame({t: x.prices["Volume"].reindex(pc.index) for t, x in pc.ctxs.items()})
    rel = (vlm / vlm.rolling(252, min_periods=60).median()).median(axis=1)
    liq = pd.Series(np.where(rel < 0.7, "thin volume", "normal volume"), index=pc.index).where(rel.notna())
    return pd.DataFrame({"trend": trend, "volatility": vreg, "liquidity": liq})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=list(SETS), default="core")
    ap.add_argument("--start")
    ap.add_argument("--fill", choices=["open", "close"])
    args = ap.parse_args()
    cfg = copy.deepcopy(CFG)
    if args.fill:
        cfg["strategy"]["fill"] = args.fill
    scfg = cfg["strategy"]
    start = args.start or STARTS[args.set]
    run_at = datetime.now(timezone.utc)
    tag = "synthetic" if cfg.get("offline") else "real"
    out = RESULTS / f"{run_at:%Y-%m-%d-%H%M}-plab-{args.set}-{tag}{'-' + args.fill + 'fill' if args.fill else ''}"
    out.mkdir(parents=True, exist_ok=True)

    print(f"Loading shared inputs from {start} ...", flush=True)
    shared = load_shared(cfg, start)
    ctxs, prices, costs = {}, {}, {}
    for t in SETS[args.set]:
        try:
            p = data.daily_prices_from(t, start, cfg).iloc[21:]
        except Exception as exc:
            data.log_event("error", f"plab:{t}", f"prices unavailable, ticker dropped ({exc})")
            continue
        prices[t], costs[t] = p, cost_bps(t, cfg)
        ctxs[t] = LabCtx(t, p, None, cfg, shared)
    pc = PortCtx(ctxs, cfg)
    shared["_sleeve"] = pc.sleeve
    idx = pc.index
    rf = data.cash_rate(idx, cfg)
    for c in ctxs.values():
        c.rf = rf
    print(f"Portfolio of {len(ctxs)} assets from {idx[0].date()}, {len(idx)} days", flush=True)

    variants = build_port_variants()
    sims, failed = {}, {}
    for v in variants:
        try:
            tgt = v.target(pc)
            sims[v.name] = {
                m: as_sim(run_variant(v, pc, prices, costs, rf, scfg, mult, target=tgt))
                for m, mult in (("net", 1.0), ("gross", 0.0), ("x2", 2.0))
            }
            print(f"  {v.exp} {v.name}: done", flush=True)
        except Exception as exc:
            failed[v.name] = f"{type(exc).__name__}: {exc}"
            print(f"  !! {v.name} failed: {exc}", flush=True)
    variants = [v for v in variants if v.name not in failed]
    if "traded" in failed:
        raise SystemExit("baseline failed")

    # parity reference: the old engine (independent sleeves that are never rebalanced against each other)
    sl = {}
    for mode, mult in (("net", 1.0), ("gross", 0.0), ("x2", 2.0)):
        legs = {}
        for t, c in ctxs.items():
            w = c.weight().reindex(idx).where(S.rebalance_days(idx, scfg.get("rebalance", "daily")))
            legs[t] = S.simulate_weights(
                prices[t].reindex(idx),
                w,
                cost_bps=costs[t] * mult,
                cash_rate=rf,
                band=scfg.get("rebalance_band", 0.05),
                fill=scfg.get("fill", "open"),
            )
        sl[mode] = combine_sleeves(legs, {t: pc.sleeve for t in legs}, rf)
    sims["sleeve_engine"] = sl

    class _Ref:  # minimal variant record for the parity row
        exp, name, description, trial = "REF", "sleeve_engine", "Same rule, old engine: independent sleeves", False

    variants.insert(1, _Ref)
    per = periods(idx[0])
    if idx[0] >= per["pre"][1]:
        per.pop("pre")

    lo, hi = per["dev"]
    trials = [v.name for v in variants if v.trial]
    dev = pd.DataFrame({n: slice_sim(sims[n]["net"], lo, hi).daily["ret"] for n in sims})
    dev_ex = dev.sub(risk_free_daily(rf, dev.index), axis=0)
    trial_sr = [dev_ex[c].mean() / dev_ex[c].std(ddof=1) for c in trials]
    pbo = stats.probability_of_backtest_overfitting(dev_ex[trials]) if len(trials) > 2 else {}

    rows, crisis_rows, extra_rows = [], [], []
    for v in variants:
        r = {"exp": v.exp, "variant": v.name, "description": v.description, "trial": v.trial}
        cmp = {}
        for p, (a, b) in per.items():
            for mode in ("net", "x2"):
                cmp[(p, mode)] = compare(sims[v.name][mode], sims["traded"][mode], rf, a, b, cfg)
            bh = compare(sims[v.name]["net"], sims["buy_hold"]["net"], rf, a, b, cfg)
            for kk in (
                "cagr",
                "volatility",
                "sharpe",
                "sortino",
                "max_drawdown",
                "calmar",
                "turnover_per_year",
                "costs_per_year",
                "d_sharpe",
                "share_better",
                "dd_rel",
            ):
                r[f"{p}_{kk}"] = cmp[(p, "net")][kk]
            r[f"{p}_x2_d_sharpe"] = cmp[(p, "x2")]["d_sharpe"]
            r[f"{p}_vs_bh_d_sharpe"] = bh["d_sharpe"]
            ex = extra_stats(slice_sim(sims[v.name]["net"], a, b).daily["ret"])
            extra_rows.append({"variant": v.name, "period": p, **ex})
        full = performance(sims[v.name]["net"], rf)
        r.update(
            {
                f"full_{kk}": full.get(kk)
                for kk in (
                    "cagr",
                    "volatility",
                    "sharpe",
                    "sortino",
                    "max_drawdown",
                    "avg_exposure",
                    "turnover_per_year",
                    "costs_per_year",
                )
            }
        )
        extra_rows.append({"variant": v.name, "period": "full", **extra_stats(sims[v.name]["net"].daily["ret"])})
        r["dsr_dev"] = stats.deflated_sharpe(dev_ex[v.name], trial_sr) if v.trial else np.nan
        if v.name == "traded":
            r["verdict"] = "baseline"
        elif not v.trial:
            r["verdict"] = "reference" if v.exp == "REF" else "descriptive"
        else:
            r["verdict"] = lab_verdict(
                cmp[("dev", "net")],
                cmp[("dev", "x2")],
                cmp.get(("holdout", "net")),
                cmp.get(("pre", "net")),
                r["dsr_dev"],
            )
        rows.append(r)
        for wname, (a, b) in CRISES.items():
            ret, mdd = window_stats(sims[v.name]["net"], a, b)
            crisis_rows.append({"variant": v.name, "window": wname, "return": ret, "max_drawdown": mdd})
    table = pd.DataFrame(rows)
    table.to_csv(out / "variants.csv", index=False)
    extra = pd.DataFrame(extra_rows)
    extra.to_csv(out / "extra_stats.csv", index=False)
    crises = pd.DataFrame(crisis_rows)
    crises.to_csv(out / "crises.csv", index=False)

    # regimes (descriptive)
    reg = regimes(pc, shared)
    reg_rows = []
    for name in ("traded", "buy_hold", "equal_rebalanced", "trend_exit_200", "breaker_15"):
        if name not in sims:
            continue
        r_ = sims[name]["net"].daily["ret"]
        for col in reg:
            for state, g in r_.groupby(reg[col].reindex(r_.index)):
                reg_rows.append(
                    {
                        "variant": name,
                        "dimension": col,
                        "state": state,
                        "days": len(g),
                        "ann_return": g.mean() * 252,
                        "ann_vol": g.std() * np.sqrt(252),
                    }
                )
    regt = pd.DataFrame(reg_rows)
    regt.to_csv(out / "regimes.csv", index=False)

    # DCA vs lump sum over many start dates (3-year horizons, monthly starts)
    vmap = {v.name: v for v in variants if hasattr(v, "target")}
    starts = [d for d in pd.date_range(idx[0] + pd.Timedelta(days=30), idx[-1] - pd.Timedelta(days=3 * 365), freq="MS")]
    dca_rows = []
    base_tgt = vmap["traded"].target(pc)
    from aurum.plab import months_since_start

    for s0 in starts:
        s0 = idx[idx >= s0][0]
        lump = run_variant(vmap["traded"], pc, prices, costs, rf, scfg, target=base_tgt, start=s0, horizon=756)
        sub = base_tgt.loc[s0:].iloc[:756]
        m = months_since_start(sub.index)
        dca_t = sub.mul(np.minimum(1.0, (m + 1) / 12.0), axis=0)
        dca = run_variant(vmap["traded"], pc, prices, costs, rf, scfg, target=dca_t, start=s0, horizon=756)
        a_, b_ = lump.daily["value"].iloc[-1], dca.daily["value"].iloc[-1]
        dd_l = (lump.daily["value"] / lump.daily["value"].cummax() - 1).min()
        dd_d = (dca.daily["value"] / dca.daily["value"].cummax() - 1).min()
        dca_rows.append(
            {"start": s0.date(), "lump_3y": a_ - 1, "dca_3y": b_ - 1, "lump_maxdd": dd_l, "dca_maxdd": dd_d}
        )
    dcat = pd.DataFrame(dca_rows)
    dcat.to_csv(out / "dca_vs_lump.csv", index=False)

    # robustness grid (descriptive): target vol x band x volatility window, net of costs
    grid_rows = []
    for tv in (0.10, 0.125, 0.15, 0.175, 0.20):
        for band in (0.0, 0.025, 0.05, 0.10):
            for win in ("10", "sizing", "63"):
                tgt = pc.base(tv, vol=win)
                tgt = tgt.where(S.rebalance_days(idx, scfg.get("rebalance", "daily")), np.nan)
                prr = simulate_portfolio(
                    prices, tgt, cost_bps=costs, cash_rate=rf, band=band * pc.sleeve, fill=scfg.get("fill", "open")
                )
                sim = as_sim(prr)
                g = {"target_vol": tv, "band": band, "vol_window": "21" if win == "sizing" else win}
                for p, (a, b) in per.items():
                    perf = performance(slice_sim(sim, a, b), rf)
                    g[f"{p}_sharpe"], g[f"{p}_cagr"], g[f"{p}_maxdd"] = (
                        perf.get("sharpe"),
                        perf.get("cagr"),
                        perf.get("max_drawdown"),
                    )
                pf = performance(sim, rf)
                g["full_sharpe"], g["full_cagr"], g["full_maxdd"] = (
                    pf.get("sharpe"),
                    pf.get("cagr"),
                    pf.get("max_drawdown"),
                )
                g["turnover"] = pf.get("turnover_per_year")
                grid_rows.append(g)
    grid = pd.DataFrame(grid_rows)
    grid.to_csv(out / "robustness_grid.csv", index=False)
    cost_rows = []
    for bps in (0, 5, 10, 25, 50):
        prr = simulate_portfolio(
            prices,
            base_tgt.where(S.rebalance_days(idx, scfg.get("rebalance", "daily")), np.nan),
            cost_bps={t: bps for t in pc.tickers},
            cash_rate=rf,
            band=scfg.get("rebalance_band", 0.05) * pc.sleeve,
            fill=scfg.get("fill", "open"),
        )
        pf = performance(as_sim(prr), rf)
        cost_rows.append({"cost_bps": bps, "full_cagr": pf.get("cagr"), "full_sharpe": pf.get("sharpe")})
    costt = pd.DataFrame(cost_rows)
    costt.to_csv(out / "cost_sensitivity.csv", index=False)

    # what "normal" looks like for paper trading: rolling-window returns of the traded rule
    base_ret = sims["traded"]["net"].daily["ret"]
    normal = []
    for days, label in ((21, "1 month"), (63, "3 months"), (126, "6 months"), (252, "1 year")):
        w = rolling_window_returns(base_ret, days)
        normal.append(
            {
                "window": label,
                "p05": w.quantile(0.05),
                "p25": w.quantile(0.25),
                "median": w.median(),
                "p75": w.quantile(0.75),
                "p95": w.quantile(0.95),
                "share_negative": float((w < 0).mean()),
                "p01": w.quantile(0.01),
            }
        )
    normt = pd.DataFrame(normal)
    normt.to_csv(out / "normal_ranges.csv", index=False)

    charts(out, sims, ["traded", "buy_hold", "equal_rebalanced", "sleeve_engine"])
    meta = {
        "run_at": run_at.isoformat(timespec="seconds"),
        "data": tag,
        "set": args.set,
        "tickers": pc.tickers,
        "portfolio_start": str(idx[0].date()),
        "periods": {k: [str(a.date()), str(b.date()) if b is not None else None] for k, (a, b) in per.items()},
        "fill": scfg.get("fill", "open"),
        "rebalance": scfg.get("rebalance", "daily"),
        "config_hash": config_hash(cfg),
        "code_fingerprint": code_fingerprint(),
        "git_commit": git_commit(),
        "data_fingerprint": data.data_fingerprint(prices),
        "n_trials": len(trials),
        "pbo_development": pbo,
        "failed_variants": failed,
        "data_events": data.DATA_EVENTS,
    }
    (out / "metadata.json").write_text(json.dumps(meta, indent=2, default=str))
    write_summary(out, table, extra, crises, regt, dcat, grid, costt, normt, meta)
    print(f"\nWrote {out}")


def charts(out, sims, names):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(2, 1, figsize=(10, 7), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    for n in names:
        if n not in sims:
            continue
        eq = (1 + sims[n]["net"].daily["ret"]).cumprod()
        ax[0].plot(eq.index, eq, label=n, lw=1.2)
        ax[1].plot(eq.index, eq / eq.cummax() - 1, lw=1)
    ax[0].set_yscale("log")
    ax[0].set_ylabel("Growth of 1 (log scale)")
    ax[0].legend()
    ax[1].set_ylabel("Drawdown")
    ax[0].set_title("Backtest, net of costs (historical simulation, not live results)")
    fig.tight_layout()
    fig.savefig(out / "equity_drawdown.png", dpi=110)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4))
    for n in ("traded", "buy_hold"):
        r = sims[n]["net"].daily["ret"]
        m = (1 + r).groupby([r.index.year, r.index.month]).prod() - 1
        ax.hist(m, bins=40, alpha=0.5, label=n)
    ax.set_xlabel("Monthly return")
    ax.legend()
    ax.set_title("Distribution of monthly returns (backtest)")
    fig.tight_layout()
    fig.savefig(out / "monthly_returns.png", dpi=110)
    plt.close(fig)


def write_summary(out, t, extra, crises, regt, dcat, grid, costt, normt, meta):
    def f(x, pct=False):
        if x is None or (isinstance(x, float) and not np.isfinite(x)):
            return "–"
        return f"{x:+.1%}" if pct else f"{x:+.2f}"

    P_ = list(meta["periods"])
    L = [f"# Portfolio lab: {meta['set']} set, {meta['run_at'][:16]} UTC ({meta['data']})", ""]
    if meta["data"] == "synthetic":
        L += ["> **SYNTHETIC DATA.** Checks that the code runs. These numbers say nothing about real markets.", ""]
    L += [
        f"Historical simulation (backtest), not live results. Assets: {', '.join(meta['tickers'])}; one account from "
        f"{meta['portfolio_start']}. Periods: "
        + "; ".join(f"{k} {a} → {b or 'now'}" for k, (a, b) in meta["periods"].items())
        + f". Orders fill at the next {meta['fill']}, decided {meta['rebalance']}; net of per-asset costs. Baseline = "
        f"`traded`. {meta['n_trials']} trial variants; PBO (development) "
        f"{meta['pbo_development'].get('pbo', float('nan')):.0%}.",
        "",
        "![equity and drawdown](equity_drawdown.png)",
        "",
        "## Return, risk and Sharpe by period",
        "",
        "| Exp | Variant | "
        + " | ".join(f"{p} CAGR / Sharpe / max DD" for p in P_)
        + " | Whole period | Exposure | Costs/yr |",
        "|---|---|" + "---|" * len(P_) + "---|---|---|",
    ]
    for _, r in t.iterrows():
        cells = " | ".join(
            f"{f(r[f'{p}_cagr'], True)} / {f(r[f'{p}_sharpe'])} / {f(r[f'{p}_max_drawdown'], True)}" for p in P_
        )
        L.append(
            f"| {r['exp']} | {r['variant']} | {cells} | {f(r['full_cagr'], True)} / {f(r['full_sharpe'])} / "
            f"{f(r['full_max_drawdown'], True)} | {r['full_avg_exposure']:.0%} | {r['full_costs_per_year']:.2%} |"
        )
    L += [
        "",
        "## Versus the traded rule (ΔSharpe; share of block-bootstrap resamples better)",
        "",
        "| Exp | Variant | " + " | ".join(f"{p} ΔSharpe (better)" for p in P_) + " | dev 2× cost | DSR | Verdict |",
        "|---|---|" + "---|" * len(P_) + "---|---|---|",
    ]
    for _, r in t.iterrows():
        cells = " | ".join(
            f"{f(r[f'{p}_d_sharpe'])} ({r[f'{p}_share_better']:.0%})"
            if np.isfinite(r[f"{p}_share_better"])
            else f"{f(r[f'{p}_d_sharpe'])}"
            for p in P_
        )
        dsr = f"{r['dsr_dev']:.2f}" if np.isfinite(r["dsr_dev"]) else "–"
        L.append(f"| {r['exp']} | {r['variant']} | {cells} | {f(r['dev_x2_d_sharpe'])} | {dsr} | {r['verdict']} |")
    e = extra[extra["period"] == "full"].set_index("variant")
    L += [
        "",
        "## Consistency and tails (whole period, monthly returns)",
        "",
        "| Variant | Months up | Profit factor | Avg up month | Avg down month | Worst month | Worst day | "
        "CVaR 5% (day) | Longest time below peak | Time below peak |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for n, r in e.iterrows():
        L.append(
            f"| {n} | {r['months_positive']:.0%} | {r['profit_factor_monthly']:.2f} | {f(r['avg_up_month'], True)} | "
            f"{f(r['avg_down_month'], True)} | {f(r['worst_month'], True)} | {f(r['worst_day'], True)} | "
            f"{f(r['cvar_5_daily'], True)} | {int(r['longest_underwater_days'])} days | {r['time_underwater']:.0%} |"
        )
    show = [
        v
        for v in ("traded", "buy_hold", "equal_rebalanced", "trend_exit_200", "breaker_15", "miners_cap_40")
        if v in set(crises["variant"])
    ]
    L += [
        "",
        "## Stress windows (return / worst fall)",
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
    L += [
        "",
        "## Market regimes (annualised mean return / volatility; descriptive, regimes defined on GLD and GVZ)",
        "",
    ]
    piv = regt.assign(cell=lambda d: d.apply(lambda x: f"{x['ann_return']:+.1%} / {x['ann_vol']:.0%}", axis=1))
    for dim in piv["dimension"].unique():
        sub = piv[piv["dimension"] == dim].pivot(index="state", columns="variant", values="cell")
        days = piv[piv["dimension"] == dim].groupby("state")["days"].first()
        L += [
            f"**{dim}**",
            "",
            "| State | days | " + " | ".join(sub.columns) + " |",
            "|---|---|" + "---|" * len(sub.columns),
        ]
        for s_, r in sub.iterrows():
            L.append(f"| {s_} | {days[s_]} | " + " | ".join(str(x) for x in r) + " |")
        L.append("")
    if len(dcat):
        better = (dcat["dca_3y"] > dcat["lump_3y"]).mean()
        L += [
            "## Investing all at once vs over 12 months (3-year outcomes from every monthly start)",
            "",
            f"{len(dcat)} start dates. Spreading the start over 12 months ended ahead in **{better:.0%}** of them. "
            f"Average 3-year return: lump sum {dcat['lump_3y'].mean():+.1%}, spread {dcat['dca_3y'].mean():+.1%}; "
            f"worst: lump sum {dcat['lump_3y'].min():+.1%}, spread {dcat['dca_3y'].min():+.1%}; average worst fall: "
            f"lump sum {dcat['lump_maxdd'].mean():+.1%}, spread {dcat['dca_maxdd'].mean():+.1%}.",
            "",
        ]
    L += [
        "## Robustness: Sharpe for nearby settings (whole period, net)",
        "",
        "Rows: volatility target; columns: rebalance band. One table per volatility window. The current setting is "
        "15% / 5 points / 21 days.",
        "",
    ]
    for win in ("10", "21", "63"):
        g = grid[grid["vol_window"] == win].pivot(index="target_vol", columns="band", values="full_sharpe")
        L += [
            f"**{win}-day volatility**",
            "",
            "| Target vol | " + " | ".join(f"band {b:g}" for b in g.columns) + " |",
            "|---|" + "---|" * len(g.columns),
        ]
        for tv, r in g.iterrows():
            L.append(f"| {tv:.1%} | " + " | ".join(f"{x:.2f}" for x in r) + " |")
        L.append("")
    L += ["## Cost sensitivity (same one-way cost on every asset)", "", "| bps | CAGR | Sharpe |", "|---|---|---|"]
    L += [f"| {int(r['cost_bps'])} | {f(r['full_cagr'], True)} | {f(r['full_sharpe'])} |" for _, r in costt.iterrows()]
    L += [
        "",
        "## What normal looks like (traded rule, every rolling window in the history)",
        "",
        "| Window | 1st pct | 5th pct | 25th | median | 75th | 95th | Share of windows with a loss |",
        "|---|---|---|---|---|---|---|---|",
    ]
    L += [
        f"| {r['window']} | {f(r['p01'], True)} | {f(r['p05'], True)} | {f(r['p25'], True)} | {f(r['median'], True)} | "
        f"{f(r['p75'], True)} | {f(r['p95'], True)} | {r['share_negative']:.0%} |"
        for _, r in normt.iterrows()
    ]
    L += ["", "![monthly returns](monthly_returns.png)", ""]
    if meta["failed_variants"]:
        L += ["**Variants dropped because they raised errors:**", ""] + [
            f"- `{k}`: {v}" for k, v in meta["failed_variants"].items()
        ]
    bad = [x for x in meta["data_events"] if x.get("level") == "error"]
    if bad:
        L += ["", "**Data problems:**", ""] + [f"- {x['source']}: {x['message']}" for x in bad]
    L += ["", "Verdicts are proposals. A change is only adopted when recorded in research/decisions.md."]
    (out / "summary.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
