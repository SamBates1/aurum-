"""Full research study: strategy vs benchmarks, model diagnostics, robustness.

    python run_research.py                 # real data (needs internet)
    AURUM_OFFLINE=1 python run_research.py # synthetic data, for checking the code only

Outputs
    results/<timestamp>/   every table as CSV, charts as PNG, metadata.json (git-ignored)
    reports/latest/        report.md + charts, small enough to commit

Research discipline
    * Every choice (features, thresholds, costs, model parameters) is fixed in
      config.yaml BEFORE looking at results. The threshold grid below is
      reported for transparency, not used to pick parameters.
    * Results are split into a development period and an untouched holdout
      (research.holdout_start). Only the holdout is a clean out-of-sample test
      of choices made on the development period.
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from aurum import benchmarks, data, model, stats
from aurum import strategy as S
from aurum.backtest import combine_sleeves, performance, relative, risk_free_daily, slice_sim
from aurum.config import CFG, ROOT, all_tickers, config_hash, cost_bps, is_equity
from aurum.features import atr as atr_fn
from aurum.pipeline import research

PERIODS = ("development", "holdout", "full")


def period_bounds(eval_start, holdout_start):
    h = pd.Timestamp(holdout_start)
    return {"development": (eval_start, h - pd.Timedelta(days=1)), "holdout": (h, None), "full": (eval_start, None)}


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def grouped_permutation_importance(X, y, groups, horizon, cfg, dev_end, seed, eval_years=2, repeats=5) -> pd.DataFrame:
    """AUC lost when each feature family is shuffled, measured on the last
    `eval_years` of the development period with a model trained before it."""
    Xv, yv = model.usable(X.loc[:dev_end], y.loc[:dev_end])
    split = Xv.index[-1] - pd.DateOffset(years=eval_years)
    tr_mask = Xv.index < split
    n_tr = int(tr_mask.sum()) - horizon  # purge
    if n_tr < 500:
        return pd.DataFrame()
    m = model.make_model(cfg["model"].get("random_state", 0)).fit(Xv.iloc[:n_tr], yv.iloc[:n_tr])
    Xte, yte = Xv.loc[~tr_mask], yv.loc[~tr_mask]
    from sklearn.metrics import roc_auc_score

    base = roc_auc_score(yte, m.predict_proba(Xte)[:, 1])
    rng = np.random.default_rng(seed)
    rows = []
    for g, cols in groups.items():
        cols = [c for c in cols if c in Xte.columns]
        if not cols:
            continue
        drops = []
        for _ in range(repeats):
            Xp = Xte.copy()
            perm = rng.permutation(len(Xp))
            Xp[cols] = Xp[cols].to_numpy()[perm]  # shuffle the family jointly, keeping its internal structure
            drops.append(base - roc_auc_score(yte, m.predict_proba(Xp)[:, 1]))
        rows.append(
            {
                "group": g,
                "n_features": len(cols),
                "auc_drop": float(np.mean(drops)),
                "auc_drop_sd": float(np.std(drops)),
                "base_auc": base,
                "eval_from": Xte.index[0].date(),
                "eval_to": Xte.index[-1].date(),
            }
        )
    return pd.DataFrame(rows)


def analyse_ticker(t, macro, cfg, gdx_prices=None):
    scfg, rcfg, mcfg = cfg["strategy"], cfg["research"], cfg["model"]
    res = research(t, macro, cfg)
    tech_cols = res.groups["technical"]
    wf_tech = model.walk_forward(
        res.X[tech_cols],
        res.y,
        mcfg["horizon_days"],
        mcfg["min_train_days"],
        mcfg["retrain_every_days"],
        mcfg.get("random_state", 0),
    )
    atr = atr_fn(res.prices)
    start = res.eval_start
    bounds = period_bounds(start, rcfg["holdout_start"])
    sims = benchmarks.run_all(
        res.prices, res.X, res.score, res.wf.probs, wf_tech.probs, atr, res.rf, scfg, cost_bps(t, cfg), start
    )
    if gdx_prices is not None and is_equity(t, cfg):
        g = gdx_prices.loc[start:]
        sims["miner_index_hold"] = S.simulate(
            g,
            pd.Series(S.BUY, index=g.index, dtype=object),
            res.X["vol_21"],
            atr,
            cost_bps=cost_bps(cfg["universe"]["miner_benchmark"], cfg),
            cash_rate=res.rf,
            stop_atr_mult=None,
            fixed_exposure=1.0,
        )

    perf_rows, boot_rows, model_rows = [], [], []
    for period, (lo, hi) in bounds.items():
        if hi is not None and hi < lo:
            continue
        sliced = {k: slice_sim(v, lo, hi) for k, v in sims.items()}
        for name, sim in sliced.items():
            if len(sim.daily) < 2:
                continue
            row = {"ticker": t, "period": period, "strategy": name, **performance(sim, res.rf)}
            row.update({f"vs_buy_hold_{k}": v for k, v in relative(sim, sliced["buy_hold"]).items()})
            perf_rows.append(row)
        ex = sliced["strategy"].daily["ret"] - risk_free_daily(res.rf, sliced["strategy"].daily.index)
        for bench in ("buy_hold", "vol_sized_hold", "sma_trend"):
            bex = sliced[bench].daily["ret"] - risk_free_daily(res.rf, sliced[bench].daily.index)
            b = stats.bootstrap_sharpe(ex, bex, rcfg["bootstrap_block_days"], rcfg["bootstrap_reps"], rcfg["seed"])
            if b:
                boot_rows.append({"ticker": t, "period": period, "vs": bench, **b})
        for label, probs in (("ml_all_features", res.wf.probs), ("ml_technical_only", wf_tech.probs)):
            m = model.classification_metrics(probs.loc[lo:hi], res.y.loc[lo:hi])
            model_rows.append({"ticker": t, "period": period, "model": label, **m})

    # cost sensitivity (full OOS and holdout), same signals, different cost assumptions
    cost_rows = []
    dec = S.decisions(res.score, scfg["buy_above"], scfg["sell_below"])
    for bps in cfg["costs"]["sensitivity_bps"]:
        sim = S.simulate(
            res.prices.loc[start:],
            dec,
            res.X["vol_21"],
            atr,
            cost_bps=bps,
            cash_rate=res.rf,
            target_vol=scfg["target_vol"],
            stop_atr_mult=scfg["stop_atr_mult"],
        )
        for period in ("full", "holdout"):
            lo, hi = bounds[period]
            p = performance(slice_sim(sim, lo, hi), res.rf)
            cost_rows.append(
                {
                    "ticker": t,
                    "cost_bps": bps,
                    "period": period,
                    "cagr": p.get("cagr"),
                    "sharpe": p.get("sharpe"),
                    "costs_per_year": p.get("costs_per_year"),
                }
            )

    # threshold grid: development period only, reported for transparency, never used to choose
    grid_rows = []
    dlo, dhi = bounds["development"]
    for b in rcfg["threshold_grid"]:
        sim = S.simulate(
            res.prices.loc[start:],
            S.decisions(res.score, b, -b),
            res.X["vol_21"],
            atr,
            cost_bps=cost_bps(t, cfg),
            cash_rate=res.rf,
            target_vol=scfg["target_vol"],
            stop_atr_mult=scfg["stop_atr_mult"],
        )
        p = performance(slice_sim(sim, dlo, dhi), res.rf)
        grid_rows.append(
            {
                "ticker": t,
                "buy_above": b,
                "sell_below": -b,
                "sharpe": p.get("sharpe"),
                "cagr": p.get("cagr"),
                "trades": p.get("trades"),
                "chosen_in_config": b == scfg["buy_above"],
            }
        )

    # regimes over the full OOS period
    regime_rows = []
    rets = {k: sims[k].daily["ret"] for k in ("strategy", "buy_hold", "vol_sized_hold")}
    for rname, labels in stats.make_regimes(res.prices["Close"], macro).items():
        tbl = stats.regime_table(rets, labels)
        for regime, r in tbl.iterrows():
            regime_rows.append({"ticker": t, "regime_type": rname, "regime": regime, **r.to_dict()})

    imp = grouped_permutation_importance(res.X, res.y, res.groups, mcfg["horizon_days"], cfg, dhi, rcfg["seed"])
    if len(imp):
        imp.insert(0, "ticker", t)
    folds = res.wf.folds.assign(ticker=t)
    calib = model.calibration_table(res.wf.probs.loc[dlo:dhi], res.y.loc[dlo:dhi]).assign(
        ticker=t, period="development"
    )
    yearly = stats.yearly_returns({k: sims[k].daily["ret"] for k in ("strategy", "buy_hold")}).assign(ticker=t)
    return dict(
        res=res,
        sims=sims,
        perf=perf_rows,
        boot=boot_rows,
        model=model_rows,
        cost=cost_rows,
        grid=grid_rows,
        regime=regime_rows,
        importance=imp,
        folds=folds,
        calib=calib,
        yearly=yearly,
    )


# ---------------------------------------------------------------------------
# charts
# ---------------------------------------------------------------------------
def charts(out: Path, per: dict, portfolio: dict, tables: dict, cfg, label: str):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "figure.dpi": 110,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.3,
            "font.size": 9,
        }
    )
    colors = {
        "strategy": "#B8860B",
        "buy_hold": "#555555",
        "vol_sized_hold": "#8FA3BF",
        "sma_trend": "#4C9F70",
        "momentum": "#9C6ADE",
        "cash": "#BBBBBB",
    }
    hold = pd.Timestamp(cfg["research"]["holdout_start"])
    files = []

    def finish(fig, name, title):
        fig.suptitle(f"{title}\n{label}", fontsize=10)
        fig.tight_layout()
        fig.savefig(out / name)
        plt.close(fig)
        files.append(name)

    # portfolio equity and drawdown
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    for name, sim in portfolio.items():
        eq = (1 + sim.daily["ret"]).cumprod()
        a1.plot(
            eq.index, eq, label=name.replace("_", " "), color=colors.get(name), lw=1.6 if name == "strategy" else 1.1
        )
        a2.plot(eq.index, eq / eq.cummax() - 1, color=colors.get(name), lw=1)
    for a in (a1, a2):
        a.axvline(hold, color="k", ls="--", lw=0.8)
    a1.text(hold, a1.get_ylim()[1], " holdout →", va="top", fontsize=8)
    a1.set_ylabel("growth of 1")
    a2.set_ylabel("drawdown")
    a1.legend(frameon=False, ncol=3)
    finish(fig, "portfolio_equity.png", "Equal-sleeve portfolio, after costs")

    # per-ticker equity
    tick = list(per)
    fig, axes = plt.subplots(int(np.ceil(len(tick) / 2)), 2, figsize=(10, 2.6 * np.ceil(len(tick) / 2)), squeeze=False)
    for ax, t in zip(axes.flat, tick):
        for name in ("strategy", "buy_hold", "vol_sized_hold", "sma_trend"):
            eq = (1 + per[t]["sims"][name].daily["ret"]).cumprod()
            ax.plot(
                eq.index, eq, color=colors[name], lw=1.4 if name == "strategy" else 0.9, label=name.replace("_", " ")
            )
        ax.axvline(hold, color="k", ls="--", lw=0.7)
        ax.set_title(t, fontsize=9)
        ax.set_yscale("log")
    for ax in list(axes.flat)[len(tick) :]:
        ax.axis("off")
    axes.flat[0].legend(frameon=False, fontsize=7)
    finish(fig, "equity_by_ticker.png", "Strategy vs benchmarks by ticker (log scale, after costs)")

    # cost sensitivity
    cs = tables["cost_sensitivity"]
    cs = cs[cs["period"] == "full"].pivot(index="cost_bps", columns="ticker", values="sharpe")
    fig, ax = plt.subplots(figsize=(7, 3.5))
    cs.plot(ax=ax, marker="o")
    ax.axhline(0, color="k", lw=0.7)
    ax.set_xlabel("one-way cost per trade (bps)")
    ax.set_ylabel("Sharpe ratio")
    finish(fig, "cost_sensitivity.png", "Strategy Sharpe vs trading-cost assumption (full out-of-sample period)")

    # calibration
    cal = tables["calibration"]
    fig, ax = plt.subplots(figsize=(5, 4.5))
    ax.plot([0, 1], [0, 1], "k--", lw=0.8, label="perfect calibration")
    for t, g in cal.groupby("ticker"):
        ax.plot(g["mean_pred"], g["freq_up"], marker="o", ms=3, lw=1, label=t)
    ax.set_xlabel("predicted P(up)")
    ax.set_ylabel("observed frequency of up")
    ax.legend(frameon=False, fontsize=7)
    finish(fig, "calibration.png", "Model calibration (development period, out-of-sample)")

    # fold AUC
    folds = tables["folds"]
    fig, ax = plt.subplots(figsize=(9, 3.2))
    for t, g in folds.groupby("ticker"):
        ax.plot(pd.to_datetime(g["test_start"]), g["auc"], marker=".", lw=0.8, label=t)
    ax.axhline(0.5, color="k", lw=0.8)
    ax.set_ylabel("AUC per walk-forward fold")
    ax.legend(frameon=False, ncol=6, fontsize=7)
    finish(fig, "fold_auc.png", "Out-of-sample AUC by walk-forward fold (0.5 = coin flip)")

    # importance
    imp = tables["feature_importance"]
    if len(imp):
        fig, ax = plt.subplots(figsize=(7, 3.5))
        imp.pivot(index="ticker", columns="group", values="auc_drop").plot.bar(ax=ax)
        ax.axhline(0, color="k", lw=0.7)
        ax.set_ylabel("AUC lost when shuffled")
        finish(fig, "feature_importance.png", "Grouped permutation importance (late development period)")

    # regimes (portfolio-level average across tickers)
    rg = tables["regimes"]
    if len(rg):
        agg = rg.groupby(["regime_type", "regime"])[["strategy", "buy_hold"]].mean()
        fig, ax = plt.subplots(figsize=(8, 3.8))
        agg.plot.bar(ax=ax, color=[colors["strategy"], colors["buy_hold"]])
        ax.axhline(0, color="k", lw=0.7)
        ax.set_ylabel("annualised mean return")
        ax.set_xlabel("")
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
        finish(fig, "regimes.png", "Return by market regime (average across tickers)")
    return files


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
def md_table(df: pd.DataFrame, floatfmt="{:.3f}", pct=()) -> str:
    def fmt(c, v):
        if isinstance(v, (float, np.floating)):
            if not np.isfinite(v):
                return "–"
            return f"{v:.1%}" if c in pct else floatfmt.format(v)
        return str(v)

    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(fmt(c, r[c]) for c in cols) + " |")
    return "\n".join(lines)


def write_report(out: Path, tables: dict, meta: dict, files: list[str], cfg) -> str:
    synthetic = meta["offline"]
    P = tables["portfolio"]
    keep = [
        "strategy",
        "buy_hold",
        "vol_sized_hold",
        "sma_trend",
        "momentum",
        "technical_only",
        "ml_only",
        "ml_no_macro",
        "cash",
    ]
    cols = [
        "strategy",
        "cagr",
        "volatility",
        "sharpe",
        "sortino",
        "max_drawdown",
        "calmar",
        "time_in_market",
        "trades",
        "costs_per_year",
    ]
    pct = {"cagr", "volatility", "max_drawdown", "time_in_market", "costs_per_year", "total_return"}
    parts = [
        "# Aurum research report\n",
        f"**Generated:** {meta['run_at']} · **commit:** `{meta['git_commit']}` · **config:** `{meta['config_hash']}`\n",
    ]
    if synthetic:
        parts.append(
            "> ⚠️ **SYNTHETIC DATA.** This run used generated prices (offline mode) to check the code. "
            "None of these numbers describe real markets. Run `python run_research.py` with internet access "
            "for real results.\n"
        )
    dev_end = pd.Timestamp(cfg["research"]["holdout_start"]) - pd.Timedelta(days=1)
    universe = ", ".join(meta["tickers"])
    parts.append(
        "\n## Setup\n"
        f"* Universe: {universe}. Out-of-sample period starts {meta['eval_start']} "
        f"(after {cfg['model']['min_train_days']} training days).\n"
        f"* **Development:** {meta['eval_start']} → {dev_end:%Y-%m-%d}. "
        f"**Untouched holdout:** {cfg['research']['holdout_start']} → {meta['data_end']}.\n"
        f"* Decisions at the close, filled at the next open. Costs per ticker (one-way bps): "
        f"{cfg['costs']['per_ticker']}.\n"
        f"* Cash and the Sharpe risk-free rate use the 3-month T-bill, lagged {cfg['macro']['fred_lag_days']} "
        "business days.\n"
        "* All parameters were fixed in `config.yaml` before this run; nothing below was tuned on the holdout.\n"
    )
    for period in ("holdout", "development"):
        sub = (
            P[P["period"] == period]
            .set_index("strategy")
            .reindex([k for k in keep if k in set(P["strategy"])])
            .reset_index()
        )
        parts.append(
            f"\n## Portfolio results: {period}\n\nEqual sleeves across tickers (each capped at "
            f"{cfg['strategy']['max_position_pct']:.0%}), after costs.\n\n" + md_table(sub[cols], pct=pct) + "\n"
        )
    B = tables["bootstrap_portfolio"]
    if len(B):
        parts.append(
            "\n## Uncertainty (stationary block bootstrap, 90% intervals)\n\n"
            "Descriptive intervals, not a formal significance test. Overlapping labels and many "
            "comparisons mean a single good number can easily be luck.\n\n"
            + md_table(
                B[
                    [
                        "period",
                        "vs",
                        "sharpe",
                        "sharpe_p05",
                        "sharpe_p95",
                        "sharpe_diff",
                        "diff_p05",
                        "diff_p95",
                        "share_resamples_better",
                    ]
                ]
            )
            + "\n"
        )
    M = tables["model_metrics"]
    if len(M):
        m = M[M["period"] == "holdout"][
            [
                "ticker",
                "model",
                "n",
                "auc",
                "accuracy",
                "base_rate",
                "brier",
                "brier_baseline",
                "log_loss",
                "log_loss_baseline",
            ]
        ]
        parts.append(
            "\n## Model quality: holdout\n\nAUC 0.5 = coin flip. Brier/log loss below their "
            "baseline (a constant forecast at the base rate) means the probabilities add information.\n\n"
            + md_table(m)
            + "\n"
        )
    T = tables["performance"]
    hs = T[(T["period"] == "holdout") & (T["strategy"].isin(["strategy", "buy_hold", "vol_sized_hold"]))]
    parts.append(
        "\n## By ticker: holdout\n\n"
        + md_table(hs[["ticker", "strategy", "cagr", "sharpe", "max_drawdown", "trades"]], pct=pct)
        + "\n"
    )
    for f in files:
        parts.append(f"\n![{f}]({f})\n")
    if meta["data_events"]:
        parts.append(
            "\n## Data warnings during this run\n\n"
            + "\n".join(f"* `{e['level']}` {e['source']}: {e['message']}" for e in meta["data_events"])
            + "\n"
        )
    parts.append("""
## Known limitations
* **Survivorship:** the universe was chosen today. Miners that failed or were acquired before today are absent.
* **Macro vintages:** FRED values are the latest revision, lagged for publication delay. Market-based series
  (TIPS yields, breakevens, T-bills) are rarely revised, but this is not a true point-in-time (ALFRED) dataset.
* **Sentiment and fundamentals** have no free point-in-time history, so they are excluded from all backtests
  and carry zero weight in live decisions by default.
* **Execution:** fills at the next open with a flat cost assumption; real spreads widen in stress and large
  orders move prices. See the cost-sensitivity chart.
* **Multiple comparisons:** several strategies and tickers are compared; the best of many will look good by chance.
""")
    text = "\n".join(parts)
    (out / "report.md").write_text(text)
    return text


def main():
    cfg = CFG
    run_at = datetime.now(timezone.utc)
    out = ROOT / "results" / run_at.strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    print(f"Writing results to {out}")
    macro = data.macro_daily(cfg)
    tickers = all_tickers(cfg)
    gdx = data.daily_prices(cfg["universe"]["miner_benchmark"], cfg=cfg)
    per = {}
    for t in tickers:
        print(f"Researching {t} ...", flush=True)
        try:
            per[t] = analyse_ticker(t, macro, cfg, gdx)
        except Exception as exc:
            data.log_event("error", t, f"research failed, excluded from report: {exc}")
    if not per:
        sys.exit("No ticker could be researched; see warnings above.")

    def cat(key):
        frames = [pd.DataFrame(v[key]) if isinstance(v[key], list) else v[key] for v in per.values()]
        frames = [f for f in frames if len(f)]
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    tables = {
        "performance": cat("perf"),
        "bootstrap": cat("boot"),
        "model_metrics": cat("model"),
        "cost_sensitivity": cat("cost"),
        "threshold_grid": cat("grid"),
        "regimes": cat("regime"),
        "feature_importance": cat("importance"),
        "folds": cat("folds"),
        "calibration": cat("calib"),
        "yearly": cat("yearly"),
    }

    # portfolio: equal sleeves, every strategy run through the same sleeve weights
    w = S.sleeve_weight(len(per), cfg["strategy"]["max_position_pct"])
    rf = next(iter(per.values()))["res"].rf
    names = [
        "strategy",
        "buy_hold",
        "vol_sized_hold",
        "sma_trend",
        "momentum",
        "technical_only",
        "ml_only",
        "ml_no_macro",
        "cash",
    ]
    portfolio = {
        n: combine_sleeves({t: v["sims"][n] for t, v in per.items() if n in v["sims"]}, {t: w for t in per}, rf)
        for n in names
    }
    start = max(v["res"].eval_start for v in per.values())
    prow, brow = [], []
    for period, (lo, hi) in period_bounds(start, cfg["research"]["holdout_start"]).items():
        sl = {n: slice_sim(s, lo, hi) for n, s in portfolio.items()}
        for n, s in sl.items():
            prow.append(
                {
                    "period": period,
                    "strategy": n,
                    **performance(s, rf),
                    **{f"vs_buy_hold_{k}": v for k, v in relative(s, sl["buy_hold"]).items()},
                }
            )
        ex = sl["strategy"].daily["ret"] - risk_free_daily(rf, sl["strategy"].daily.index)
        for bench in ("buy_hold", "vol_sized_hold", "sma_trend"):
            bex = sl[bench].daily["ret"] - risk_free_daily(rf, sl[bench].daily.index)
            b = stats.bootstrap_sharpe(
                ex,
                bex,
                cfg["research"]["bootstrap_block_days"],
                cfg["research"]["bootstrap_reps"],
                cfg["research"]["seed"],
            )
            if b:
                brow.append({"period": period, "vs": bench, **b})
    tables["portfolio"] = pd.DataFrame(prow)
    tables["bootstrap_portfolio"] = pd.DataFrame(brow)

    for name, df in tables.items():
        df.to_csv(out / f"{name}.csv", index=False)

    import sklearn

    first = next(iter(per.values()))["res"]
    meta = {
        "run_at": run_at.isoformat(timespec="seconds"),
        "git_commit": git_commit(),
        "config_hash": config_hash(cfg),
        "offline": bool(cfg.get("offline")),
        "tickers": list(per),
        "eval_start": str(start.date()),
        "data_end": str(first.prices.index[-1].date()),
        "config": cfg,
        "model_params": model.MODEL_PARAMS,
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "sklearn": sklearn.__version__,
        "data_sources": {t: data.cache_info(t) for t in list(per) + [cfg["universe"]["miner_benchmark"]]},
        "data_events": data.DATA_EVENTS,
    }
    (out / "metadata.json").write_text(json.dumps(meta, indent=2, default=str))
    label = (
        "SYNTHETIC DATA – not real results"
        if meta["offline"]
        else f"Yahoo Finance + FRED, retrieved {run_at:%Y-%m-%d}; costs and fills are assumptions"
    )
    files = charts(
        out,
        per,
        {k: portfolio[k] for k in ("strategy", "buy_hold", "vol_sized_hold", "sma_trend", "cash")},
        tables,
        cfg,
        label,
    )
    report = write_report(out, tables, meta, files, cfg)

    latest = ROOT / "reports" / ("latest-synthetic" if meta["offline"] else "latest")
    if latest.exists():
        shutil.rmtree(latest)
    latest.mkdir(parents=True)
    for f in files + [
        "report.md",
        "portfolio.csv",
        "performance.csv",
        "model_metrics.csv",
        "cost_sensitivity.csv",
        "bootstrap_portfolio.csv",
    ]:
        shutil.copy(out / f, latest / f)
    (latest / "metadata.json").write_text(
        json.dumps({k: v for k, v in meta.items() if k != "config"}, indent=2, default=str)
    )
    print("\n" + report.split("## By ticker")[0])
    print(f"Full results: {out}\nCommittable summary: {latest}")


if __name__ == "__main__":
    main()
