"""Cross-asset research lab: EXP-037 ... EXP-044 (master brief Parts C, E, F, H; rules in each EXP file).

    python run_xlab.py --exp sp500      # EXP-037  can Aurum-style portfolios beat the S&P 500?
    python run_xlab.py --exp trend      # EXP-038  trend and momentum, 10 assets, many windows
    python run_xlab.py --exp meanrev    # EXP-039  mean reversion and pairs (cointegration)
    python run_xlab.py --exp vol        # EXP-040  volatility models: forecast accuracy and sizing
    python run_xlab.py --exp candles    # EXP-041  candlestick patterns with controls and multiple-testing correction
    python run_xlab.py --exp ml         # EXP-042  ML models vs simple baselines, walk-forward
    python run_xlab.py --exp macro      # EXP-043  macro and cross-asset lead-lag
    python run_xlab.py --exp delay      # EXP-044  execution delay and cost sensitivity of the traded strategy
    AURUM_OFFLINE=1 python run_xlab.py --exp sp500   # synthetic: code check only

Each run writes research/experiments/results/<date-time>-xlab-<exp>-<real|synthetic>/ with summary.md, CSVs,
metadata.json (config, code and data fingerprints) and figures/.
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
from aurum import xlab as X
from aurum.backtest import performance, risk_free_daily, slice_sim
from aurum.config import CFG, code_fingerprint, config_hash, git_commit
from aurum.figures import FigurePack
from run_experiments import RESULTS

COST_NOTE = "per-asset one-way bps (SPY/QQQ 2, IWM/EFA/TLT/IEF/GLD 3, SLV/GDX 5, DBC 8)"
SPLIT_NOTE = "pre <2013-10-18 | dev 2013-10-18..2023 | holdout 2024+"


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------
def load_universe(cfg, tickers=None, start=X.START):
    prices = {}
    for t in tickers or X.UNIVERSE:
        try:
            prices[t] = data.daily_prices_from(t, start, cfg)
        except Exception as exc:
            data.log_event("error", f"xlab:{t}", f"unavailable ({exc})")
    return prices


def as_sim(daily: pd.DataFrame) -> S.SimResult:
    d = daily.copy()
    if "invested" not in d:
        d["invested"] = (d.get("exposure", pd.Series(1.0, index=d.index)) > 1e-9).astype(float)
    for col in ("exposure", "traded", "cost"):
        if col not in d:
            d[col] = 0.0
    if "value" not in d:
        d["value"] = (1 + d["ret"]).cumprod()
    return S.SimResult(d, pd.DataFrame(columns=["entry_date", "exit_reason", "pnl", "ret", "days", "entry_value"]))


def scorecard(sim: S.SimResult, rf, bench: pd.Series | None, lo=None, hi=None) -> dict:
    s = slice_sim(sim, lo, hi)
    p = performance(s, rf)
    r = s.daily["ret"]
    eq = (1 + r).cumprod()
    dd = eq / eq.cummax() - 1
    under = (dd < 0).astype(int)
    runs = under.groupby((under != under.shift()).cumsum()).sum()
    out = {
        k: p.get(k)
        for k in (
            "cagr",
            "volatility",
            "sharpe",
            "sortino",
            "max_drawdown",
            "calmar",
            "avg_exposure",
            "turnover_per_year",
            "costs_per_year",
            "total_return",
        )
    }
    out["longest_drawdown_days"] = int(runs.max()) if len(runs) else 0
    q = r.quantile(0.05)
    out["cvar5_daily"] = float(r[r <= q].mean()) if len(r) else np.nan
    m = (1 + r).groupby([r.index.year, r.index.month]).prod() - 1
    out["months_positive"] = float((m > 0).mean()) if len(m) else np.nan
    if bench is not None:
        a, b = r.align(bench, join="inner")
        out["beta_vs_spy"] = float(a.cov(b) / b.var()) if b.var() > 0 else np.nan
        out["corr_vs_spy"] = float(a.corr(b))
    return out


def compare_to(sim, base, rf, lo, hi, cfg) -> dict:
    v, b = slice_sim(sim, lo, hi), slice_sim(base, lo, hi)
    ex_v = v.daily["ret"] - risk_free_daily(rf, v.daily.index)
    ex_b = b.daily["ret"] - risk_free_daily(rf, b.daily.index)
    a, bb = ex_v.align(ex_b, join="inner")
    rc = cfg["research"]
    boot = stats.bootstrap_sharpe(a, bb, rc["bootstrap_block_days"], rc["bootstrap_reps"], rc["seed"])
    pv, pb = performance(v, rf), performance(b, rf)
    return {
        "d_sharpe": (pv.get("sharpe") or np.nan) - (pb.get("sharpe") or np.nan),
        "d_cagr": (pv.get("cagr") or np.nan) - (pb.get("cagr") or np.nan),
        "share_better": boot.get("share_resamples_better", np.nan),
        "diff_p05": boot.get("diff_p05", np.nan),
        "diff_p95": boot.get("diff_p95", np.nan),
    }


def f_(x, pct=False, d=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "–"
    return f"{x:+.1%}" if pct else f"{x:+.{d}f}"


def out_dir(exp, cfg):
    tag = "synthetic" if cfg.get("offline") else "real"
    fill = cfg["strategy"].get("fill", "open")
    o = RESULTS / f"{datetime.now(timezone.utc):%Y-%m-%d-%H%M}-xlab-{exp}-{tag}{'' if fill == 'open' else '-closefill'}"
    o.mkdir(parents=True, exist_ok=True)
    return o, tag


def write_meta(out, cfg, extra, prices):
    meta = {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data": "synthetic" if cfg.get("offline") else "real",
        "config_hash": config_hash(cfg),
        "code_fingerprint": code_fingerprint(),
        "git_commit": git_commit(),
        "data_fingerprint": data.data_fingerprint(prices),
        "data_events": data.DATA_EVENTS,
        **extra,
    }
    (out / "metadata.json").write_text(json.dumps(meta, indent=2, default=str))
    return meta


def score_table(sims: dict, rf, bench, per) -> pd.DataFrame:
    rows = []
    for name, sim in sims.items():
        for p, (lo, hi) in {**per, "full": (None, None)}.items():
            rows.append({"strategy": name, "period": p, **scorecard(sim, rf, bench, lo, hi)})
    return pd.DataFrame(rows)


def period_md(table: pd.DataFrame, per_names) -> list[str]:
    L = [
        "| Strategy | " + " | ".join(f"{p}: CAGR / Sharpe / max DD" for p in per_names) + " | Exposure | Costs/yr | "
        "Beta vs SPY | Longest drawdown |",
        "|---|" + "---|" * (len(per_names) + 4),
    ]
    for name, g in table.groupby("strategy", sort=False):
        g = g.set_index("period")
        cells = " | ".join(
            f"{f_(g.loc[p, 'cagr'], True)} / {f_(g.loc[p, 'sharpe'])} / {f_(g.loc[p, 'max_drawdown'], True)}"
            for p in per_names
        )
        fu = g.loc["full"]
        L.append(
            f"| {name} | {cells} | {fu['avg_exposure']:.0%} | {fu['costs_per_year']:.2%} | "
            f"{f_(fu.get('beta_vs_spy'))} | {int(fu['longest_drawdown_days'])} days |"
        )
    return L


def aurum_core_returns(cfg, start=X.START):
    """The adopted strategy (vol_hold, GVZ-sized, daily, one account) on the core set, as a daily return series."""
    from aurum.lab import SETS, LabCtx
    from aurum.plab import PortCtx
    from aurum.portfolio import simulate_portfolio
    from run_lab import load_shared

    shared = load_shared(cfg, start)
    ctxs, prices, costs = {}, {}, {}
    from aurum.config import cost_bps

    for t in SETS["core"]:
        p = data.daily_prices_from(t, start, cfg).iloc[21:]
        prices[t], costs[t] = p, cost_bps(t, cfg)
        ctxs[t] = LabCtx(t, p, None, cfg, shared)
    pc = PortCtx(ctxs, cfg)
    shared["_sleeve"] = pc.sleeve
    idx = pc.index
    rf = data.cash_rate(idx, cfg)
    tgt = pc.base().where(S.rebalance_days(idx, cfg["strategy"].get("rebalance", "daily")), np.nan)
    pr = simulate_portfolio(
        prices,
        tgt,
        cost_bps=costs,
        cash_rate=rf,
        band=cfg["strategy"].get("rebalance_band", 0.05) * pc.sleeve,
        fill=cfg["strategy"].get("fill", "open"),
    )
    return pr, prices, pc, rf


def returns_as_prices(r: pd.Series) -> pd.DataFrame:
    """A strategy's daily returns as an OHLC frame (open = close = equity), so it can be held as a fund."""
    eq = (1 + r.fillna(0)).cumprod()
    return pd.DataFrame({"Open": eq.shift(1).fillna(1.0), "High": eq, "Low": eq, "Close": eq, "Volume": 1.0})


# ---------------------------------------------------------------------------
# EXP-037: can Aurum-style portfolios beat the S&P 500?
# ---------------------------------------------------------------------------
def exp_sp500(cfg):
    out, tag = out_dir("sp500", cfg)
    prices = load_universe(cfg)
    aur, core_prices, _, _ = aurum_core_returns(cfg)
    aur_r = aur.daily["ret"]
    idx = X.common_index({**prices, "AURUM": returns_as_prices(aur_r)})
    prices = {t: p.reindex(idx) for t, p in prices.items()}
    rf = data.cash_rate(idx, cfg)
    spy_r = prices["SPY"]["Close"].pct_change().fillna(0)
    fund = {**prices, "AURUM": returns_as_prices(aur_r).reindex(idx)}
    costs = {**X.COSTS, "AURUM": 0.0}  # Aurum's own trading costs are already inside its returns
    sims = {}

    def keep(name, pr):
        sims[name] = as_sim(pr.daily)

    one = lambda tick, w: pd.DataFrame({t: w[i] for i, t in enumerate(tick)}, index=idx)  # noqa: E731
    keep(
        "SPY buy & hold",
        X.run(fund, one(["SPY"], [1.0]).where(pd.Series(np.arange(len(idx)) == 0, index=idx)), rf, costs=costs),
    )
    keep("Aurum (adopted, core)", X.run(fund, one(["AURUM"], [1.0]), rf, costs=costs))
    keep("60/40 SPY/IEF", X.run(fund, X.monthly(one(["SPY", "IEF"], [0.6, 0.4])), rf, costs=costs))
    for a in (0.2, 0.3, 0.4):
        keep(
            f"SPY {1 - a:.0%} + Aurum {a:.0%}",
            X.run(fund, X.monthly(one(["SPY", "AURUM"], [1 - a, a])), rf, costs=costs),
        )
    keep("SPY 70% + GLD 30%", X.run(fund, X.monthly(one(["SPY", "GLD"], [0.7, 0.3])), rf, costs=costs))
    multi = ["SPY", "EFA", "TLT", "IEF", "GLD", "DBC", "GDX"]
    mp = {t: prices[t] for t in multi}
    w_multi = X.vol_weights(mp, idx) / len(multi)
    keep("Aurum rule on 7 assets", X.run(fund, w_multi, rf, costs=costs, band=0.05 / len(multi)))
    rp_assets = ["SPY", "EFA", "TLT", "IEF", "GLD", "DBC"]
    rp = X.monthly(X.scale_to_vol(X.inverse_vol({t: prices[t] for t in rp_assets}, idx), prices, target=0.10))
    keep("Risk parity 10% vol", X.run(fund, rp, rf, costs=costs))
    lev_rows = []
    for L_ in (1.25, 1.5, 2.0):
        for spread in (0.015, 0.03):
            pr = X.run(fund, rp, rf, costs=costs, leverage=L_, financing_spread=spread)
            name = f"Risk parity x{L_:g} (borrow T-bill+{spread:.1%})"
            if spread == 0.015:
                keep(name, pr)
            lev_rows.append((L_, spread, pr))
    pr = X.run(fund, w_multi, rf, costs=costs, band=0.05 / len(multi), leverage=1.5, financing_spread=0.015)
    keep("Aurum rule on 7 assets x1.5 (T-bill+1.5%)", pr)

    per = X.periods(idx[0])
    table = score_table(sims, rf, spy_r, per)
    table.to_csv(out / "scorecard.csv", index=False)
    base = sims["SPY buy & hold"]
    vs = []
    for n, s in sims.items():
        row = {"strategy": n}
        for p, (lo, hi) in {**per, "full": (None, None)}.items():
            c = compare_to(s, base, rf, lo, hi, cfg)
            row.update({f"{p}_{k}": v for k, v in c.items()})
        vs.append(row)
    vs = pd.DataFrame(vs)
    vs.to_csv(out / "vs_spy.csv", index=False)
    # pre-registered test (EXP-037): beats SPY = higher CAGR in pre, dev, holdout and full, AND full max DD no worse
    sc = table.set_index(["strategy", "period"])
    verdicts = {}
    for n in sims:
        if n == "SPY buy & hold":
            verdicts[n] = "benchmark"
            continue
        higher = all(sc.loc[(n, p), "cagr"] > sc.loc[("SPY buy & hold", p), "cagr"] for p in [*per, "full"])
        dd_ok = sc.loc[(n, "full"), "max_drawdown"] >= sc.loc[("SPY buy & hold", "full"), "max_drawdown"]
        sharpe_up = sc.loc[(n, "full"), "sharpe"] > sc.loc[("SPY buy & hold", "full"), "sharpe"]
        verdicts[n] = (
            "BEATS SPY (return and drawdown, every period)"
            if higher and dd_ok
            else "higher return per unit of risk, lower return"
            if sharpe_up and not higher
            else "does not beat SPY"
        )
    fp = FigurePack(
        out, "EXP-037", "SPY, QQQ, IWM, EFA, TLT, IEF, GLD, SLV, GDX, DBC + Aurum core", COST_NOTE, SPLIT_NOTE
    )
    main = [
        "SPY buy & hold",
        "Aurum (adopted, core)",
        "SPY 70% + Aurum 30%",
        "60/40 SPY/IEF",
        "Risk parity 10% vol",
        "Risk parity x1.5 (borrow T-bill+1.5%)",
        "Risk parity x2 (borrow T-bill+1.5%)",
    ]
    R = {n: sims[n].daily["ret"] for n in main if n in sims}
    fp.equity_drawdown(R)
    fp.rolling(R, spy_r)
    fp.annual({k: R[k] for k in list(R)[:4]})
    fp.distribution({k: R[k] for k in ("SPY buy & hold", "Aurum (adopted, core)", "SPY 70% + Aurum 30%")})
    fp.tails(R)
    fp.turnover_costs({n: sims[n].daily for n in main[1:5] if n in sims})
    rp_pr = X.run(fund, rp, rf, costs=costs)
    fp.exposure(rp_pr.weights, "exposure_risk_parity", "risk parity 10% vol")
    fp.exposure(
        X.run(fund, w_multi, rf, costs=costs, band=0.05 / len(multi)).weights,
        "exposure_aurum7",
        "Aurum rule on 7 assets",
    )
    gross = X.run(fund, rp, rf, costs=costs, cost_mult=0.0)
    fp.gross_vs_net(gross.daily["ret"], rp_pr.daily["ret"], "gross_vs_net_risk_parity")
    rets = pd.DataFrame({t: prices[t]["Close"].pct_change() for t in prices} | {"AURUM": aur_r.reindex(idx)}).dropna()
    fp.corr_heatmap(rets)
    lev = pd.DataFrame(
        [
            {"leverage": L_, "borrow": f"T-bill+{sp:.1%}", "CAGR": performance(as_sim(pr.daily), rf).get("cagr")}
            for L_, sp, pr in lev_rows
        ]
    ).pivot(index="leverage", columns="borrow", values="CAGR")
    lev["SPY CAGR"] = sc.loc[("SPY buy & hold", "full"), "cagr"]
    fp.lines(
        lev,
        "Risk parity CAGR by leverage and financing cost vs SPY",
        "leverage_cagr",
        "leverage",
        "CAGR (whole period)",
    )
    bp = pd.DataFrame({n: [sc.loc[(n, p), "sharpe"] for p in per] for n in main if n in sims}, index=list(per))
    fp.by_period(bp, "Sharpe ratio by period", "sharpe_by_period")
    meta = write_meta(
        out,
        cfg,
        {"exp": "EXP-037", "periods": {k: [str(a.date()), str(b.date()) if b else None] for k, (a, b) in per.items()}},
        prices,
    )
    L = [f"# EXP-037: can Aurum-style portfolios beat the S&P 500? ({tag}, {meta['run_at'][:16]} UTC)", ""]
    if tag == "synthetic":
        L += ["> **SYNTHETIC DATA.** Code check only.", ""]
    L += [
        f"Historical simulation, net of costs; common dates {idx[0].date()} → {idx[-1].date()}; one account, next-open "
        "fills, cash at T-bill; leverage financed at T-bill + 1.5% (sensitivity +3%); mixes rebalanced monthly. "
        "Aurum = adopted strategy on GLD, SLV, GDX, NEM, AEM, WPM.",
        "",
        "## Scorecard",
        "",
    ]
    L += period_md(table, list(per))
    L += [
        "",
        "## Versus SPY (whole period): ΔCAGR, ΔSharpe, share of block-bootstrap resamples with higher Sharpe; "
        "pre-registered verdict",
        "",
        "| Strategy | ΔCAGR | ΔSharpe | better | Verdict |",
        "|---|---|---|---|---|",
    ]
    for _, r in vs.iterrows():
        L.append(
            f"| {r['strategy']} | {f_(r['full_d_cagr'], True)} | {f_(r['full_d_sharpe'])} | "
            f"{r['full_share_better']:.0%} | {verdicts[r['strategy']]} |"
            if np.isfinite(r["full_share_better"])
            else f"| {r['strategy']} | – | – | – | {verdicts[r['strategy']]} |"
        )
    L += ["", "## Leverage and financing", "", "| Leverage | T-bill+1.5% CAGR | T-bill+3% CAGR |", "|---|---|---|"]
    for L_ in (1.25, 1.5, 2.0):
        L.append(f"| {L_:g} | {f_(lev.loc[L_, 'T-bill+1.5%'], True)} | {f_(lev.loc[L_, 'T-bill+3.0%'], True)} |")
    L += [
        "",
        *fp.markdown_index(),
        "",
        "Verdicts are proposals; nothing changes the traded strategy without a recorded decision.",
    ]
    (out / "summary.md").write_text("\n".join(L) + "\n")
    return out


# ---------------------------------------------------------------------------
# shared evaluation of a family of portfolio variants against a no-signal baseline
# ---------------------------------------------------------------------------
def evaluate_family(
    sims: dict[str, S.SimResult], sims_x2: dict[str, S.SimResult], baseline: str, trials: list[str], rf, cfg, per
) -> pd.DataFrame:
    from run_experiments import compare
    from run_lab import lab_verdict

    lo, hi = per["dev"]
    dev = pd.DataFrame({n: slice_sim(sims[n], lo, hi).daily["ret"] for n in sims})
    dev_ex = dev.sub(risk_free_daily(rf, dev.index), axis=0)
    trial_sr = [dev_ex[c].mean() / dev_ex[c].std(ddof=1) for c in trials]
    pbo = stats.probability_of_backtest_overfitting(dev_ex[trials]) if len(trials) > 2 else {}
    rows = []
    for n in sims:
        r = {"variant": n}
        cmp = {}
        for p, (a, b) in per.items():
            cmp[p] = compare(sims[n], sims[baseline], rf, a, b, cfg)
            r[f"{p}_d_sharpe"], r[f"{p}_better"] = cmp[p]["d_sharpe"], cmp[p]["share_better"]
        x2 = compare(sims_x2[n], sims_x2[baseline], rf, lo, hi, cfg)
        r["dev_x2_d_sharpe"] = x2["d_sharpe"]
        r["dsr_dev"] = stats.deflated_sharpe(dev_ex[n], trial_sr) if n in trials else np.nan
        r["verdict"] = (
            "baseline"
            if n == baseline
            else lab_verdict(cmp["dev"], x2, cmp.get("holdout"), cmp.get("pre"), r["dsr_dev"])
            if n in trials
            else "reference"
        )
        rows.append(r)
    t = pd.DataFrame(rows)
    t.attrs["pbo"] = pbo.get("pbo", np.nan)
    return t


def verdict_md(t: pd.DataFrame, per_names) -> list[str]:
    L = [
        "| Variant | " + " | ".join(f"{p} ΔSharpe (better)" for p in per_names) + " | dev 2× cost | DSR | Verdict |",
        "|---|" + "---|" * (len(per_names) + 3),
    ]
    for _, r in t.iterrows():
        cells = " | ".join(
            f"{f_(r[f'{p}_d_sharpe'])} ({r[f'{p}_better']:.0%})"
            if np.isfinite(r[f"{p}_better"])
            else f_(r[f"{p}_d_sharpe"])
            for p in per_names
        )
        dsr = f"{r['dsr_dev']:.2f}" if np.isfinite(r["dsr_dev"]) else "–"
        L.append(f"| {r['variant']} | {cells} | {f_(r['dev_x2_d_sharpe'])} | {dsr} | {r['verdict']} |")
    return L


def sim_both(fund, tgt, rf, band=0.0, fill="open"):
    return (
        as_sim(X.run(fund, tgt, rf, band=band, fill=fill).daily),
        as_sim(X.run(fund, tgt, rf, band=band, fill=fill, cost_mult=2.0).daily),
    )


def per_asset_sharpe(fund, rules, prices, rf, per, vol_size: bool):
    """Sharpe of each rule on each asset alone (long/flat), minus that asset's buy & hold, by period."""
    rows = []
    for t, p in prices.items():
        idx = p.index
        bh = as_sim(
            X.run(
                {t: p}, pd.DataFrame({t: 1.0}, index=idx).where(pd.Series(np.arange(len(idx)) == 0, index=idx)), rf
            ).daily
        )
        vw = S.vol_target_weight(X.realised_21d(p["Close"]), 0.15) if vol_size else 1.0
        for name, fn in rules.items():
            expo = (fn(p["Close"]) * vw).fillna(0.0)
            sim = as_sim(X.run({t: p}, expo.to_frame(t), rf, band=0.05 if vol_size else 0.0).daily)
            for per_name, (lo, hi) in {**per, "full": (None, None)}.items():
                a = performance(slice_sim(sim, lo, hi), rf).get("sharpe")
                b = performance(slice_sim(bh, lo, hi), rf).get("sharpe")
                rows.append(
                    {
                        "asset": t,
                        "rule": name,
                        "period": per_name,
                        "sharpe": a,
                        "bh_sharpe": b,
                        "d_sharpe_vs_bh": (a or np.nan) - (b or np.nan),
                    }
                )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# EXP-038 trend and momentum
# ---------------------------------------------------------------------------
TREND_RULES = {
    "sma_50_200": lambda c: X.sma_cross(c, 50, 200),
    "sma_20_100": lambda c: X.sma_cross(c, 20, 100),
    "ema_20_100": lambda c: X.ema_cross(c, 20, 100),
    "above_sma50": lambda c: X.above_sma(c, 50),
    "above_sma100": lambda c: X.above_sma(c, 100),
    "above_sma200": lambda c: X.above_sma(c, 200),
    "tsmom_63": lambda c: X.tsmom(c, 63),
    "tsmom_126": lambda c: X.tsmom(c, 126),
    "tsmom_252": lambda c: X.tsmom(c, 252),
    "donchian_50_20": lambda c: X.donchian(c, 50, 20),
    "multi_tf_1_3_12": X.multi_tf_trend,
}
MR_RULES = {
    "rsi2_reversion": X.rsi2_reversion,
    "bollinger_reversion": X.bollinger_reversion,
    "zscore60_reversion": X.zscore_reversion,
    "extreme_drop_5d": X.extreme_drop,
}


def family_experiment(cfg, exp_id, key, rules, title, extra_portfolios=None):
    out, tag = out_dir(key, cfg)
    prices = load_universe(cfg)
    idx = X.common_index(prices)
    prices = {t: p.reindex(idx) for t, p in prices.items()}
    rf = data.cash_rate(idx, cfg)
    per = X.periods(idx[0] + pd.Timedelta(days=380))  # first year only warms up the 252-day signals
    n = len(prices)
    vw = X.vol_weights(prices, idx)
    base_tgt = vw / n
    sims, sims2 = {}, {}
    sims["no-signal vol-sized (baseline)"], sims2["no-signal vol-sized (baseline)"] = sim_both(
        prices, base_tgt, rf, 0.05 / n
    )
    ew = pd.DataFrame(1.0 / n, index=idx, columns=list(prices))
    sims["equal weight, monthly (reference)"], sims2["equal weight, monthly (reference)"] = sim_both(
        prices, X.monthly(ew), rf
    )
    for name, fn in rules.items():
        sig = pd.DataFrame({t: fn(p["Close"]) for t, p in prices.items()}).fillna(0.0)
        sims[name], sims2[name] = sim_both(prices, base_tgt * sig, rf, 0.05 / n)
    for name, tgt in (extra_portfolios or {}).items():
        t_ = tgt(prices, idx, vw)
        sims[name], sims2[name] = sim_both(prices, t_, rf, 0.05 / n)
    trials = [k for k in sims if "baseline" not in k and "reference" not in k]
    ver = evaluate_family(sims, sims2, "no-signal vol-sized (baseline)", trials, rf, cfg, per)
    ver.to_csv(out / "verdicts.csv", index=False)
    spy_r = prices["SPY"]["Close"].pct_change().fillna(0)
    table = score_table(sims, rf, spy_r, per)
    table.to_csv(out / "scorecard.csv", index=False)
    pa_full = per_asset_sharpe(prices, rules, prices, rf, per, vol_size=False)
    pa_vol = per_asset_sharpe(prices, rules, prices, rf, per, vol_size=True)
    pa_full.to_csv(out / "per_asset_long_flat.csv", index=False)
    pa_vol.to_csv(out / "per_asset_vol_sized.csv", index=False)
    fp = FigurePack(out, exp_id, ", ".join(prices), COST_NOTE, SPLIT_NOTE)
    top = ["no-signal vol-sized (baseline)", "equal weight, monthly (reference)", *list(rules)[:4]]
    fp.equity_drawdown({k: sims[k].daily["ret"] for k in top})
    for pname in ("dev", "full"):
        g = pa_full[pa_full["period"] == pname].pivot(index="rule", columns="asset", values="d_sharpe_vs_bh")
        fp.heatmap(
            g,
            f"Sharpe minus buy & hold, each rule alone on each asset, long/flat ({pname})",
            f"heatmap_rule_asset_{pname}",
        )
    by_p = pd.DataFrame(
        {p: [performance(slice_sim(sims[k], *per[p]), rf).get("sharpe") for k in sims] for p in per}, index=list(sims)
    )
    fp.by_period(by_p.T, "Portfolio Sharpe by period (pre / dev / holdout)", "sharpe_by_period")
    fp.annual({k: sims[k].daily["ret"] for k in top[:3]})
    # walk-forward style stability: Sharpe of each portfolio variant by calendar-year block
    yrs = {}
    for k in top:
        r = sims[k].daily["ret"]
        yrs[k] = r.groupby(r.index.year).apply(lambda x: x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else np.nan)
    fp.by_period(pd.DataFrame(yrs), "Sharpe by calendar year (stability across time)", "sharpe_by_year")
    sample = "GLD" if "GLD" in prices else list(prices)[0]
    fp.candles(
        prices[sample],
        {"SMA50>200 cross on": X.sma_cross(prices[sample]["Close"], 50, 200).diff() == 1},
        f"candles_{sample}",
        sample,
    )
    write_meta(out, cfg, {"exp": exp_id, "pbo_development": ver.attrs["pbo"], "n_trials": len(trials)}, prices)
    share = pa_full[pa_full.period != "full"].groupby("rule")["d_sharpe_vs_bh"].apply(lambda s: (s > 0).mean())
    L = [
        f"# {exp_id}: {title} ({tag})",
        "",
        f"Historical simulation, net of costs, common dates {idx[0].date()} → {idx[-1].date()} (first year warms up "
        f"signals). Portfolio variants: equal sleeves across {n} assets, each sized by Aurum's volatility rule "
        "(15% / 21-day vol) and multiplied by the rule's 0/1 signal; baseline = the same sizing with no signal. "
        f"{len(trials)} trial variants; PBO (dev) {ver.attrs['pbo']:.0%}.",
        "",
        "## Portfolio verdicts vs the no-signal baseline",
        "",
    ]
    L += verdict_md(ver, list(per))
    L += ["", "## Portfolio scorecard", ""] + period_md(table, list(per))
    L += [
        "",
        "## Each rule alone on each asset (long/flat, no vol sizing): share of asset-periods beating buy & hold",
        "",
        "| Rule | Share of (asset, period) cells with higher Sharpe than buy & hold |",
        "|---|---|",
    ]
    L += [f"| {k} | {v:.0%} |" for k, v in share.sort_values(ascending=False).items()]
    L += ["", *fp.markdown_index()]
    (out / "summary.md").write_text("\n".join(L) + "\n")
    return out


def xs_momentum(lookback, skip, top=3):
    def build(prices, idx, vw):
        closes = pd.DataFrame({t: p["Close"] for t, p in prices.items()}, index=idx)
        mom = closes.shift(skip) / closes.shift(lookback) - 1
        rank = mom.rank(axis=1, ascending=False)
        pick = (rank <= top).astype(float).where(mom.notna().all(axis=1), 0.0)
        tgt = X.monthly(vw * pick / top)
        return tgt

    return build


def exp_trend(cfg):
    return family_experiment(
        cfg,
        "EXP-038",
        "trend",
        TREND_RULES,
        "Trend following and momentum across 10 assets",
        {"xs_momentum_126_top3": xs_momentum(126, 0), "xs_momentum_252_21_top3": xs_momentum(252, 21)},
    )


def exp_meanrev(cfg):
    out = family_experiment(cfg, "EXP-039", "meanrev", MR_RULES, "Mean reversion across 10 assets")
    # pairs: cointegration stability and a market-neutral spread trade
    prices = load_universe(cfg, ["GLD", "SLV", "GDX", "SPY", "IWM", "TLT", "IEF"])
    idx = X.common_index(prices)
    rows, pair_rets = [], {}
    for y, x in (("SLV", "GLD"), ("GDX", "GLD"), ("IWM", "SPY"), ("TLT", "IEF")):
        a, b = prices[y]["Close"].reindex(idx), prices[x]["Close"].reindex(idx)
        full = X.engle_granger(a, b)
        win = [
            X.engle_granger(a.iloc[i - 252 : i], b.iloc[i - 252 : i])["cointegrated_5pct"]
            for i in range(252, len(idx), 21)
        ]
        # rolling hedge ratio (252 days), spread z (60 days); enter |z| > 2, exit at 0; position known at close t,
        # earns close-to-close returns from t+1; costs 5 bps per leg on position changes; short borrow 0.5% a year
        la, lb = np.log(a), np.log(b)
        beta = la.rolling(252).cov(lb) / lb.rolling(252).var()
        spread = la - beta * lb
        z = (spread - spread.rolling(60).mean()) / spread.rolling(60).std()
        pos = pd.Series(0.0, index=idx)
        st = 0.0
        for i, v in enumerate(z.to_numpy()):
            if np.isfinite(v):
                st = -1.0 if (st == 0 and v > 2) else 1.0 if (st == 0 and v < -2) else (0.0 if st * v >= 0 else st)
            pos.iloc[i] = st
        ra, rb = a.pct_change(), b.pct_change()
        gross = 0.5 * (pos.shift() * ra - pos.shift() * beta.shift() * rb)
        cost = pos.diff().abs().fillna(0) * 2 * 5e-4 * 0.5
        borrow = pos.shift().abs() * 0.5 * 0.005 / 252
        net = (gross - cost - borrow).fillna(0) + (1 - 0.5 * pos.shift().abs().fillna(0)) * 0  # cash interest ignored
        pair_rets[f"{y}/{x}"] = net
        perf = performance(as_sim(pd.DataFrame({"ret": net})), 0.0)
        rows.append(
            {
                "pair": f"{y}/{x}",
                **full,
                "share_252d_windows_cointegrated": float(np.mean(win)),
                "trade_cagr": perf.get("cagr"),
                "trade_sharpe": perf.get("sharpe"),
                "trade_max_dd": perf.get("max_drawdown"),
                "time_in_trade": float((pos != 0).mean()),
            }
        )
    pt = pd.DataFrame(rows)
    pt.to_csv(out / "pairs.csv", index=False)
    fp = FigurePack(
        out,
        "EXP-039",
        "pairs: SLV/GLD, GDX/GLD, IWM/SPY, TLT/IEF",
        "5 bps per leg + 0.5%/yr borrow",
        "whole sample (descriptive)",
    )
    fp.equity_drawdown(pair_rets, "pairs_equity")
    text = (out / "summary.md").read_text()
    L = [
        "",
        "## Pairs (market-neutral spread trades; descriptive, whole sample)",
        "",
        "| Pair | Hedge ratio | ADF t (full) | Cointegrated (5%, full sample) | Share of 1-year windows cointegrated | "
        "Half-life (days) | Trade CAGR | Trade Sharpe | Max DD | Time in trade |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for _, r in pt.iterrows():
        L.append(
            f"| {r['pair']} | {r['hedge_ratio']:.2f} | {r['adf_t']:.2f} | "
            f"{'yes' if r['cointegrated_5pct'] else 'no'} | "
            f"{r['share_252d_windows_cointegrated']:.0%} | {r['half_life_days']:.0f} | {f_(r['trade_cagr'], True)} | "
            f"{f_(r['trade_sharpe'])} | {f_(r['trade_max_dd'], True)} | {r['time_in_trade']:.0%} |"
        )
    L += [
        "",
        "Pair-trade returns are close-to-close with no cash interest, so they are not directly comparable with "
        "the portfolio rows above.",
        "",
        *fp.markdown_index(),
    ]
    (out / "summary.md").write_text(text + "\n".join(L) + "\n")
    return out


# ---------------------------------------------------------------------------
# EXP-040 volatility models
# ---------------------------------------------------------------------------
def exp_vol(cfg):
    from aurum.volatility import ewma, har_parkinson

    out, tag = out_dir("vol", cfg)
    prices = load_universe(cfg)
    idx = X.common_index(prices)
    prices = {t: p.reindex(idx) for t, p in prices.items()}
    rf = data.cash_rate(idx, cfg)
    per = X.periods(idx[0] + pd.Timedelta(days=1100))  # GARCH and HAR need ~3 years before the first forecast
    gvz = None
    try:
        gvz = data.daily_prices_from("^GVZ", X.START, cfg)["Close"] if not cfg.get("offline") else None
    except Exception as exc:
        data.log_event("warning", "xlab:GVZ", f"unavailable ({exc})")
    est = {}
    for t, p in prices.items():
        c = p["Close"]
        r = c.pct_change(fill_method=None)
        est[t] = {
            "realised_21d": X.realised_21d(c),
            "ewma_094": ewma(c),
            "garch_1_1": X.garch11(r),
            "har_parkinson": har_parkinson(p),
        }
        if gvz is not None and t in ("GLD", "SLV", "GDX"):
            ratio = ((gvz / 100) / X.realised_21d(prices["GLD"]["Close"])).clip(0.5, 2.0)
            est[t]["gvz_adjusted"] = X.realised_21d(c) * ratio.reindex(idx).ffill()
    # prediction question: QLIKE of each forecast vs the next 21 days' realised variance (out of sample by design)
    rows = []
    for t, p in prices.items():
        r2 = p["Close"].pct_change(fill_method=None) ** 2
        fwd = r2[::-1].rolling(21).mean()[::-1].shift(-1) * 252
        for name, v in est[t].items():
            for pn, (lo, hi) in per.items():
                rows.append(
                    {"asset": t, "estimator": name, "period": pn, "qlike": X.qlike((v**2).loc[lo:hi], fwd.loc[lo:hi])}
                )
    q = pd.DataFrame(rows)
    q.to_csv(out / "forecast_accuracy.csv", index=False)
    # portfolio question: the Aurum sizing rule with each estimator (common estimator set across all assets)
    n = len(prices)
    sims, sims2 = {}, {}
    for name in ("realised_21d", "ewma_094", "garch_1_1", "har_parkinson"):
        vw = X.vol_weights(prices, idx, vol={t: est[t][name] for t in prices}) / n
        sims[name], sims2[name] = sim_both(prices, vw, rf, 0.05 / n)
    inv = X.monthly(X.scale_to_vol(X.inverse_vol(prices, idx), prices, target=0.10))
    sims["risk_parity_10 (covariance)"], sims2["risk_parity_10 (covariance)"] = sim_both(prices, inv, rf)
    ew = X.monthly(pd.DataFrame(1.0 / n, index=idx, columns=list(prices)))
    sims["equal weight (reference)"], sims2["equal weight (reference)"] = sim_both(prices, ew, rf)
    trials = ["ewma_094", "garch_1_1", "har_parkinson", "risk_parity_10 (covariance)"]
    ver = evaluate_family(sims, sims2, "realised_21d", trials, rf, cfg, per)
    ver.to_csv(out / "verdicts.csv", index=False)
    spy_r = prices["SPY"]["Close"].pct_change().fillna(0)
    table = score_table(sims, rf, spy_r, per)
    table.to_csv(out / "scorecard.csv", index=False)
    # VaR / expected shortfall backtest of the realised-vol rule: share of days beyond the 1-day 99% normal VaR
    var_rows = []
    for t, p in prices.items():
        r = p["Close"].pct_change(fill_method=None)
        for name, v in est[t].items():
            sd = (v / np.sqrt(252)).shift(1)
            m = sd.notna() & r.notna()
            var_rows.append({"asset": t, "estimator": name, "breach_rate_99": float((r[m] < -2.326 * sd[m]).mean())})
    vt = pd.DataFrame(var_rows)
    vt.to_csv(out / "var_backtest.csv", index=False)
    fp = FigurePack(out, "EXP-040", ", ".join(prices), COST_NOTE, SPLIT_NOTE)
    fp.equity_drawdown({k: s.daily["ret"] for k, s in sims.items()})
    qs = q[q.period == "dev"].pivot(index="asset", columns="estimator", values="qlike")
    fp.heatmap(
        qs,
        "QLIKE loss of volatility forecasts vs next-21-day realised variance (dev; lower is better)",
        "qlike_dev",
        "{:.3f}",
    )
    fp.heatmap(
        vt.pivot(index="asset", columns="estimator", values="breach_rate_99"),
        "Share of days with a loss beyond the 1-day 99% normal VaR (target 1%)",
        "var_breaches",
        "{:.1%}",
    )
    g = prices["GLD"]["Close"]
    fp.lines(
        pd.DataFrame({k: v for k, v in est["GLD"].items()}).loc[per["dev"][0] :],
        "GLD volatility forecasts",
        "gld_vol_forecasts",
        "date",
        "annualised volatility",
    )
    fp.exposure(X.run(prices, inv, rf).weights, "exposure_risk_parity", "risk parity 10%")
    vol_bucket = pd.qcut(X.realised_21d(g), 5, labels=False, duplicates="drop")
    fwd63 = g.shift(-63) / g - 1
    fp.bars(
        fwd63.groupby(vol_bucket).mean().rename(lambda i: f"vol quintile {int(i) + 1}"),
        "GLD: average next-63-day return by current volatility quintile (descriptive)",
        "gld_vol_vs_future",
        "mean forward return",
    )
    write_meta(out, cfg, {"exp": "EXP-040", "pbo_development": ver.attrs["pbo"]}, prices)
    best = q[q.period == "dev"].groupby("estimator")["qlike"].median().sort_values()
    L = [
        f"# EXP-040: volatility models ({tag})",
        "",
        "**Prediction question:** median QLIKE across assets (dev; lower = better forecasts of the next 21 days' "
        "variance): " + ", ".join(f"{k} {v:.3f}" for k, v in best.items()) + ".",
        "",
        "**Portfolio question:** Aurum's sizing rule on all assets with each estimator vs plain 21-day volatility:",
        "",
    ]
    L += verdict_md(ver, list(per)) + ["", "## Scorecard", ""] + period_md(table, list(per))
    L += [
        "",
        "## 99% one-day VaR breach rates (target 1.0%)",
        "",
        "| Estimator | Median breach rate across assets |",
        "|---|---|",
    ]
    L += [f"| {k} | {v:.2%} |" for k, v in vt.groupby("estimator")["breach_rate_99"].median().items()]
    L += [
        "",
        "VaR assumes normal returns; breach rates above 1% show fat tails, which is why expected shortfall and "
        "stress windows are reported elsewhere.",
        "",
        *fp.markdown_index(),
    ]
    (out / "summary.md").write_text("\n".join(L) + "\n")
    return out


# ---------------------------------------------------------------------------
# EXP-041 candlestick patterns
# ---------------------------------------------------------------------------
def exp_candles(cfg):
    out, tag = out_dir("candles", cfg)
    prices = load_universe(cfg)
    rows = []
    for t, p in prices.items():
        c = p["Close"]
        pats = X.candle_patterns(p)
        ctrl = pd.DataFrame(
            {"mom21": c.pct_change(21), "vol21": X.realised_21d(c), "trend": c / c.rolling(200).mean() - 1}
        )
        per = X.periods(p.index[0] + pd.Timedelta(days=300))
        for h in (1, 5, 10):
            fwd = c.shift(-h) / c - 1
            for pn, (lo, hi) in per.items():
                for name in pats.columns:
                    d = pd.concat([fwd.rename("y"), pats[name].astype(float).rename("x"), ctrl], axis=1).loc[lo:hi]
                    d = d.dropna()
                    if d["x"].sum() < 20:
                        continue
                    Xm = np.column_stack([np.ones(len(d)), d["x"], d["mom21"], d["vol21"], d["trend"]])
                    beta, tstat = X.newey_west_t(d["y"].to_numpy(), Xm, lags=h)
                    rows.append(
                        {
                            "asset": t,
                            "pattern": name,
                            "horizon": h,
                            "period": pn,
                            "events": int(d["x"].sum()),
                            "effect_bps": beta[1] * 1e4,
                            "t_nw": tstat[1],
                            "p": float(2 * X.norm_sf(abs(tstat[1]))[0]),
                        }
                    )
    ev = pd.DataFrame(rows)
    dev = ev[ev.period == "dev"].copy()
    dev["discovery_fdr10"] = X.benjamini_hochberg(dev["p"].to_numpy(), 0.10)
    dev["raw_p_below_5pct"] = dev["p"] < 0.05
    conf = []
    for _, r in dev[dev.discovery_fdr10].iterrows():
        other = ev[(ev.asset == r.asset) & (ev.pattern == r.pattern) & (ev.horizon == r.horizon) & (ev.period != "dev")]
        ok = len(other) == 2 and all(np.sign(other.effect_bps) == np.sign(r.effect_bps)) and all(other.p < 0.05)
        conf.append({**r.to_dict(), "confirmed_pre_and_holdout": ok})
    conf = pd.DataFrame(conf)
    ev.to_csv(out / "event_study.csv", index=False)
    dev.to_csv(out / "dev_tests_with_fdr.csv", index=False)
    conf.to_csv(out / "discoveries.csv", index=False)
    # portfolio question for bullish patterns: long the asset for 5 days after the pattern (vol-sized), vs buy & hold
    idx = X.common_index(prices)
    pr = {t: p.reindex(idx) for t, p in prices.items()}
    rf = data.cash_rate(idx, cfg)
    per = X.periods(idx[0] + pd.Timedelta(days=300))
    n = len(pr)
    vw = X.vol_weights(pr, idx)
    sims, sims2 = {}, {}
    sims["no-signal vol-sized (baseline)"], sims2["no-signal vol-sized (baseline)"] = sim_both(pr, vw / n, rf, 0.05 / n)
    for name in sorted(X.BULLISH):
        sig = pd.DataFrame(
            {t: X.candle_patterns(p)[name].astype(int).rolling(5, min_periods=1).max() for t, p in pr.items()}
        )
        sims[f"after {name} (hold 5d)"], sims2[f"after {name} (hold 5d)"] = sim_both(pr, vw / n * sig, rf, 0.05 / n)
    sig = pd.DataFrame({t: X.sma_cross(p["Close"], 50, 200) for t, p in pr.items()}).fillna(0)
    sims["simple trend sma_50_200 (comparison)"], sims2["simple trend sma_50_200 (comparison)"] = sim_both(
        pr, vw / n * sig, rf, 0.05 / n
    )
    rng = np.random.default_rng(0)
    for k in range(3):  # randomised baseline: random 5-day holding windows with the same frequency as breakouts
        rnd = (
            pd.DataFrame(rng.random((len(idx), n)) < 0.05, index=idx, columns=list(pr))
            .astype(int)
            .rolling(5, min_periods=1)
            .max()
        )
        sims[f"random entries #{k + 1} (control)"], sims2[f"random entries #{k + 1} (control)"] = sim_both(
            pr, vw / n * rnd, rf, 0.05 / n
        )
    trials = [k for k in sims if k.startswith("after ")]
    ver = evaluate_family(sims, sims2, "no-signal vol-sized (baseline)", trials, rf, cfg, per)
    ver.to_csv(out / "verdicts.csv", index=False)
    fp = FigurePack(out, "EXP-041", ", ".join(prices), COST_NOTE, SPLIT_NOTE)
    for t in ("GLD", "SPY"):
        if t in prices:
            pats = X.candle_patterns(prices[t])
            fp.candles(
                prices[t], {k: pats[k] for k in ("hammer", "bullish_engulfing", "breakout_20")}, f"candles_{t}", t
            )
    g = dev[dev.horizon == 5].pivot_table(index="pattern", columns="asset", values="t_nw")
    fp.heatmap(
        g,
        "Newey-West t-statistics of 5-day forward return after each pattern, with controls (dev)",
        "pattern_t_stats_dev",
        "{:.1f}",
    )
    eff = dev[dev.horizon == 5].groupby("pattern")["effect_bps"].mean()
    fp.bars(
        eff,
        "Average 5-day effect after each pattern, controlling for momentum, volatility and trend (dev)",
        "pattern_effects",
        "basis points",
    )
    fp.equity_drawdown({k: sims[k].daily["ret"] for k in list(sims)[:6]}, "pattern_portfolios")
    write_meta(out, cfg, {"exp": "EXP-041", "n_tests_dev": int(len(dev)), "pbo_development": ver.attrs["pbo"]}, prices)
    n_raw = int(dev["raw_p_below_5pct"].sum())
    L = [
        f"# EXP-041: candlestick patterns ({tag})",
        "",
        f"{len(X.candle_patterns(next(iter(prices.values()))).columns)} patterns × {len(prices)} assets × 3 horizons "
        f"= **{len(dev)} tests** in the development period. Forward returns regressed on the pattern dummy plus "
        "21-day momentum, 21-day volatility and distance from the 200-day average, with Newey-West standard errors.",
        "",
        f"- Tests with raw p < 5%: **{n_raw}** (about {0.05 * len(dev):.0f} expected by chance alone).",
        f"- Discoveries at a 10% false-discovery rate (Benjamini-Hochberg): **{int(dev['discovery_fdr10'].sum())}**.",
        f"- Discoveries that also held (same sign, p < 5%) before 2013 and after 2024: "
        f"**{int(conf['confirmed_pre_and_holdout'].sum()) if len(conf) else 0}**.",
        "",
    ]
    if len(conf):
        L += [
            "| Asset | Pattern | Horizon | Events (dev) | Effect (bps) | t | Confirmed |",
            "|---|---|---|---|---|---|---|",
        ]
        L += [
            f"| {r.asset} | {r.pattern} | {r.horizon}d | {r.events} | {r.effect_bps:+.0f} | {r.t_nw:.1f} | "
            f"{'yes' if r.confirmed_pre_and_holdout else 'no'} |"
            for r in conf.itertuples()
        ]
    L += ["", "## Trading the bullish patterns (portfolio level, net of costs) vs the no-signal baseline", ""]
    L += verdict_md(ver, list(per)) + ["", *fp.markdown_index()]
    (out / "summary.md").write_text("\n".join(L) + "\n")
    return out


# ---------------------------------------------------------------------------
# EXP-042 machine learning vs simple baselines
# ---------------------------------------------------------------------------
ML_ASSETS = ["SPY", "EFA", "TLT", "GLD", "GDX", "DBC"]
ML_H = 21


def make_logit_l1(random_state: int = 0):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    return make_pipeline(StandardScaler(), LogisticRegression(C=0.05, penalty="l1", solver="liblinear", max_iter=2000))


def macro_frame(cfg, idx):
    lag = int(cfg["macro"].get("fred_lag_days", 2))
    out = {}
    # credit: FRED's high-yield spread (BAMLH0A0HYM2) only has 3 years of history (data audit 2026-10-29), so a
    # market proxy is used instead: high-yield bonds (HYG, from 2007) relative to Treasuries (IEF)
    for name, tick in (("dxy", "DX-Y.NYB"), ("vix", "^VIX"), ("copper", "HG=F"), ("hyg", "HYG"), ("ief", "IEF")):
        try:
            out[name] = data.daily_prices_from(tick, X.START, cfg)["Close"]
        except Exception as exc:
            data.log_event("warning", f"xlab:{name}", f"unavailable ({exc})")
    for name, sid in (
        ("real_yield", "DFII10"),
        ("breakeven", "T10YIE"),
        ("y10", "DGS10"),
        ("y2", "DGS2"),
    ):
        try:
            s = data.fred(sid, cfg) if not cfg.get("offline") else data.synthetic.macro([sid])[sid]
            out[name] = data.publication_lag(s, lag) if not cfg.get("offline") else s
        except Exception as exc:
            data.log_event("warning", f"xlab:{name}", f"unavailable ({exc})")
    m = pd.DataFrame(out)
    m = m[~m.index.duplicated(keep="last")].sort_index()
    if "hyg" in m and "ief" in m:
        m["credit"] = m.pop("hyg") / m.pop("ief")  # falls when credit spreads widen
    return m.reindex(m.index.union(idx)).ffill().reindex(idx)


def ml_features(p, cross: pd.DataFrame, macro: pd.DataFrame) -> pd.DataFrame:
    from aurum.features import technical_features

    f = technical_features(p).drop(columns=["volume_z"], errors="ignore")
    f["ret_252"] = p["Close"].pct_change(252)
    for c in cross:
        f[f"{c}_ret21"] = cross[c].pct_change(21)
    if "dxy" in macro:
        f["dxy_chg21"] = macro["dxy"].pct_change(21)
    for c in ("real_yield", "breakeven"):
        if c in macro:
            f[f"{c}_chg21"] = macro[c].diff(21)
    if "credit" in macro:
        f["credit_ret21"] = macro["credit"].pct_change(21)
    if "vix" in macro:
        f["vix_level"] = macro["vix"]
    if "y10" in macro and "y2" in macro:
        f["curve_10_2"] = macro["y10"] - macro["y2"]
    return f.replace([np.inf, -np.inf], np.nan)


def exp_ml(cfg):
    from scipy.stats import spearmanr
    from sklearn.metrics import roc_auc_score

    from aurum import model as M

    out, tag = out_dir("ml", cfg)
    prices = load_universe(cfg, ML_ASSETS)
    idx = X.common_index(prices)
    prices = {t: p.reindex(idx) for t, p in prices.items()}
    rf = data.cash_rate(idx, cfg)
    macro = macro_frame(cfg, idx)
    cross = pd.DataFrame({t: prices[t]["Close"] for t in ("SPY", "TLT", "GLD", "DBC") if t in prices})
    factories = {
        "logit_l2": M.make_logit,
        "logit_l1": make_logit_l1,
        "random_forest": M.make_forest,
        "gradient_boosting": M.make_model,
    }
    probs, labels, fwd_ret, coefs = {}, {}, {}, []
    for t, p in prices.items():
        Xf = ml_features(p, cross.drop(columns=[t], errors="ignore"), macro)
        fr = p["Close"].shift(-ML_H) / p["Close"] - 1
        y = (fr > 0).astype(float).where(fr.notna())
        labels[t], fwd_ret[t] = y, fr
        for name, fac in factories.items():
            wf = M.walk_forward(Xf, y, ML_H, 756, 126, 0, factory=fac)
            probs[(t, name)] = wf.probs
            print(f"  ML {t} {name}: {wf.probs.notna().sum()} out-of-sample predictions", flush=True)
        # climatology baseline: share of up periods among labels already revealed (purged by the horizon)
        probs[(t, "climatology")] = y.shift(ML_H).expanding(252).mean()
        probs[(t, "tsmom_252 (rule)")] = (
            (p["Close"].pct_change(252) > 0).astype(float).where(p["Close"].pct_change(252).notna())
        )
        # feature stability: standardised L2-logit coefficients refitted on each walk-forward training window
        Xv, yv = M.usable(Xf, y)
        for start in range(756, len(Xv), 252):
            mdl = M.make_logit().fit(Xv.iloc[: start - ML_H], yv.iloc[: start - ML_H])
            coefs.append(
                {"asset": t, "fold_end": str(Xv.index[start - ML_H].date()), **dict(zip(Xv.columns, mdl[-1].coef_[0]))}
            )
    first_pred = min(s.first_valid_index() for k, s in probs.items() if k[1] in factories and s.notna().any())
    per = X.periods(first_pred)
    rows = []
    for (t, name), pr in probs.items():
        for pn, (lo, hi) in per.items():
            p_, y_ = pr.loc[lo:hi], labels[t].loc[lo:hi]
            m = p_.notna() & y_.notna()
            if m.sum() < 100 or y_[m].nunique() < 2:
                continue
            clim = labels[t].shift(ML_H).expanding(252).mean().loc[lo:hi][m]
            rows.append(
                {
                    "asset": t,
                    "model": name,
                    "period": pn,
                    "n": int(m.sum()),
                    "auc": roc_auc_score(y_[m], p_[m]) if p_[m].nunique() > 1 else np.nan,
                    "brier": float(np.mean((p_[m] - y_[m]) ** 2)),
                    "brier_climatology": float(np.mean((clim - y_[m]) ** 2)),
                    "ic_spearman": spearmanr(p_[m], fwd_ret[t].loc[lo:hi][m]).statistic,
                    "hit_rate": float(((p_[m] > 0.5) == (y_[m] > 0.5)).mean()),
                }
            )
    sig = pd.DataFrame(rows)
    sig.to_csv(out / "signal_metrics.csv", index=False)
    pd.DataFrame(coefs).to_csv(out / "logit_coefficients_by_fold.csv", index=False)
    # portfolio question
    n = len(prices)
    vw = X.vol_weights(prices, idx)
    sims, sims2 = {}, {}
    sims["no-signal vol-sized (baseline)"], sims2["no-signal vol-sized (baseline)"] = sim_both(
        prices, vw / n, rf, 0.05 / n
    )
    for name in [*factories, "tsmom_252 (rule)"]:
        s_ = pd.DataFrame(
            {t: (probs[(t, name)] > 0.5).astype(float).where(probs[(t, name)].notna(), 1.0) for t in prices}
        )
        sims[name], sims2[name] = sim_both(prices, vw / n * s_, rf, 0.05 / n)
    trials = list(factories)
    ver = evaluate_family(sims, sims2, "no-signal vol-sized (baseline)", trials, rf, cfg, per)
    ver.to_csv(out / "verdicts.csv", index=False)
    table = score_table(sims, rf, prices["SPY"]["Close"].pct_change().fillna(0), per)
    table.to_csv(out / "scorecard.csv", index=False)
    fp = FigurePack(
        out,
        "EXP-042",
        ", ".join(prices),
        COST_NOTE,
        f"walk-forward, expanding, purge {ML_H}d; " + SPLIT_NOTE,
        f"label: {ML_H}-day forward return > 0",
    )
    for t in ("GLD", "SPY"):
        for name in ("gradient_boosting", "logit_l2"):
            if (t, name) in probs:
                fp.calibration_roc(probs[(t, name)], labels[t], f"calibration_{t}_{name}", f"{t} {name}")
    for pn in ("dev", "holdout"):
        g = sig[sig.period == pn].pivot(index="model", columns="asset", values="auc")
        fp.heatmap(g, f"Out-of-sample AUC by model and asset ({pn}); 0.50 = no skill", f"auc_{pn}", "{:.2f}")
        g = sig[sig.period == pn].pivot(index="model", columns="asset", values="ic_spearman")
        fp.heatmap(
            g, f"Information coefficient (rank corr. of prediction with realised return), {pn}", f"ic_{pn}", "{:.2f}"
        )
    cf = pd.DataFrame(coefs)
    stab = cf.drop(columns=["fold_end"]).groupby("asset").agg(lambda s: (s > 0).mean()).T
    fp.heatmap(
        stab,
        "Feature stability: share of walk-forward folds with a positive L2-logit coefficient",
        "feature_stability",
        "{:.0%}",
    )
    if ("GLD", "gradient_boosting") in probs:
        pg = probs[("GLD", "gradient_boosting")]
        b = pd.qcut(pg, 5, labels=False, duplicates="drop")
        fp.bars(
            fwd_ret["GLD"].groupby(b).mean().rename(lambda i: f"prediction quintile {int(i) + 1}"),
            "GLD: realised 21-day return by predicted-probability quintile (out of sample)",
            "gld_signal_strength",
            "mean forward return",
        )
    fp.equity_drawdown({k: s.daily["ret"] for k, s in sims.items()})
    write_meta(out, cfg, {"exp": "EXP-042", "pbo_development": ver.attrs["pbo"]}, prices)
    agg = sig[sig.period == "dev"].groupby("model")[["auc", "ic_spearman"]].median()
    brier_win = (
        sig[sig.period == "dev"].assign(win=lambda d: d.brier < d.brier_climatology).groupby("model")["win"].mean()
    )
    L = [
        f"# EXP-042: machine learning vs simple baselines ({tag})",
        "",
        f"Assets {', '.join(prices)}; label = {ML_H}-day forward return > 0; features: price/technical, cross-asset "
        "21-day returns, dollar, real yield, breakeven, credit (HYG/IEF), VIX, yield curve "
        "(FRED lagged 2 business days); "
        f"expanding walk-forward from 3 years, refit every 126 days, purge {ML_H} days.",
        "",
        "## Prediction question (development period, median across assets)",
        "",
        "| Model | AUC | Information coefficient | Share of assets where Brier beats climatology |",
        "|---|---|---|---|",
    ]
    L += [
        f"| {m_} | {r.auc:.3f} | {r.ic_spearman:+.3f} | {brier_win.get(m_, np.nan):.0%} |" for m_, r in agg.iterrows()
    ]
    L += ["", "## Portfolio question: hold the asset (vol-sized) only when the model says up, vs always holding", ""]
    L += verdict_md(ver, list(per)) + ["", "## Scorecard", ""] + period_md(table, list(per))
    L += ["", *fp.markdown_index()]
    (out / "summary.md").write_text("\n".join(L) + "\n")
    return out


# ---------------------------------------------------------------------------
# EXP-043 macro and cross-asset lead-lag
# ---------------------------------------------------------------------------
def exp_macro(cfg):
    out, tag = out_dir("macro", cfg)
    prices = load_universe(cfg, ["GLD", "SLV", "GDX", "NEM", "SPY", "TLT", "DBC"])
    idx = X.common_index(prices)
    prices = {t: p.reindex(idx) for t, p in prices.items()}
    macro = macro_frame(cfg, idx)
    preds = {}
    if "dxy" in macro:
        preds["dollar 21d % chg"] = macro["dxy"].pct_change(21)
    for c in ("real_yield", "breakeven"):
        if c in macro:
            preds[f"{c} 21d chg"] = macro[c].diff(21)
    if "credit" in macro:
        preds["credit (HYG/IEF) 21d % chg"] = macro["credit"].pct_change(21)
    if "vix" in macro:
        preds["VIX level"] = macro["vix"]
    if "copper" in macro:
        preds["copper 21d % chg"] = macro["copper"].pct_change(21)
    if "y10" in macro and "y2" in macro:
        preds["curve 10y-2y"] = macro["y10"] - macro["y2"]
    preds["SPY 21d return"] = prices["SPY"]["Close"].pct_change(21)
    per = X.periods(idx[0] + pd.Timedelta(days=60))
    rows = []
    for t in ("GLD", "GDX", "SLV", "SPY"):
        c = prices[t]["Close"]
        fwd, past = c.shift(-21) / c - 1, c.pct_change(21)
        for name, x in preds.items():
            for pn, (lo, hi) in per.items():
                d = pd.concat([fwd.rename("y"), x.rename("x"), past.rename("past")], axis=1).loc[lo:hi].dropna()
                if len(d) < 200:
                    continue
                Xm = np.column_stack([np.ones(len(d)), (d["x"] - d["x"].mean()) / d["x"].std(), d["past"]])
                beta, tt = X.newey_west_t(d["y"].to_numpy(), Xm, lags=21)
                same = pd.concat([past.rename("y"), x.rename("x")], axis=1).loc[lo:hi].dropna()
                rows.append(
                    {
                        "asset": t,
                        "predictor": name,
                        "period": pn,
                        "n": len(d),
                        "predictive_effect_per_sd": beta[1],
                        "t_nw": tt[1],
                        "p": float(2 * X.norm_sf(abs(tt[1]))[0]),
                        "contemporaneous_corr": same["y"].corr(same["x"]),
                    }
                )
    t_ = pd.DataFrame(rows)
    dev = t_[t_.period == "dev"].copy()
    dev["fdr10"] = X.benjamini_hochberg(dev["p"].to_numpy(), 0.10)
    conf = []
    for _, r in dev[dev.fdr10].iterrows():
        o = t_[(t_.asset == r.asset) & (t_.predictor == r.predictor) & (t_.period != "dev")]
        conf.append(
            {
                **r.to_dict(),
                "confirmed": bool(len(o) == 2 and all(np.sign(o.t_nw) == np.sign(r.t_nw)) and all(o.p < 0.05)),
            }
        )
    t_.to_csv(out / "lead_lag.csv", index=False)
    pd.DataFrame(conf).to_csv(out / "discoveries.csv", index=False)
    fp = FigurePack(
        out,
        "EXP-043",
        "GLD, SLV, GDX, NEM, SPY, TLT, DBC + macro",
        "not applicable (no trading)",
        "descriptive and predictive regressions; " + SPLIT_NOTE,
    )
    plt = __import__("aurum.figures", fromlist=["_plt"])._plt()
    g = prices["GLD"]["Close"]

    def two_axis(a, b, la, lb, name, title, invert=False):
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(a.index, a, color="#C9A227", label=la)
        ax2 = ax.twinx()
        ax2.plot(b.index, b, color="#555", label=lb, lw=0.8)
        if invert:
            ax2.invert_yaxis()
        ax.set_ylabel(la)
        ax2.set_ylabel(lb + (" (inverted)" if invert else ""))
        ax.set_title(title)
        fp._save(fig, name, title, f"{a.index[0].date()} to {a.index[-1].date()}", "levels")

    if "dxy" in macro:
        two_axis(g, macro["dxy"], "GLD", "Dollar index", "gold_vs_dollar", "Gold vs the US dollar", invert=True)
    if "real_yield" in macro:
        two_axis(
            g,
            macro["real_yield"],
            "GLD",
            "10y real yield %",
            "gold_vs_real_yield",
            "Gold vs 10-year real yield (the link weakened after 2021)",
            invert=True,
        )
    norm = pd.DataFrame(
        {t: prices[t]["Close"] / prices[t]["Close"].iloc[0] for t in ("GLD", "SLV", "GDX", "NEM", "SPY")}
    )
    if "copper" in macro:
        norm["copper"] = macro["copper"] / macro["copper"].dropna().iloc[0]
    fp.lines(
        norm, "Gold, silver, miners, copper and the S&P 500 (growth of 1)", "cross_asset_levels", "date", "growth of 1"
    )
    rc = pd.DataFrame({k: g.pct_change(21).rolling(756).corr(v) for k, v in preds.items()})
    fp.lines(
        rc,
        "Rolling 3-year correlation: GLD 21-day return vs each driver (contemporaneous)",
        "rolling_corr_gld",
        "date",
        "correlation",
    )
    lagc = pd.DataFrame(
        {k: [(g.shift(-L_) / g - 1).corr(v) for L_ in (1, 5, 10, 21, 42, 63)] for k, v in preds.items()},
        index=[1, 5, 10, 21, 42, 63],
    )
    fp.lines(
        lagc,
        "Lead-lag: correlation of GLD's next-N-day return with each driver today",
        "lead_lag_gld",
        "forward horizon (days)",
        "correlation",
    )
    rets = pd.DataFrame({t: p["Close"].pct_change() for t, p in prices.items()}).dropna()
    fp.corr_heatmap(rets)
    dd = pd.DataFrame({t: p["Close"] / p["Close"].cummax() - 1 for t, p in prices.items()})
    fp.lines(dd, "Drawdowns of each asset", "asset_drawdowns", "date", "drawdown")
    fp.distribution(
        {t: prices[t]["Close"].pct_change().dropna() for t in ("GLD", "GDX", "SPY")}, "asset_return_distribution"
    )
    hm = dev.pivot(index="predictor", columns="asset", values="t_nw")
    fp.heatmap(
        hm,
        "Predictive t-statistics (Newey-West), next-21-day return on each driver, controlling for the "
        "asset's own 21-day return (dev)",
        "predictive_t_dev",
        "{:.1f}",
    )
    write_meta(out, cfg, {"exp": "EXP-043", "n_tests_dev": int(len(dev))}, prices)
    L = [
        f"# EXP-043: macro and cross-asset lead-lag ({tag})",
        "",
        f"{len(dev)} predictive tests in the development period (4 assets × {len(preds)} drivers); next-21-day return "
        "regressed on today's standardised driver plus the asset's own past 21-day return, Newey-West (21 lags).",
        "",
        f"- Raw p < 5%: {int((dev.p < 0.05).sum())} (about {0.05 * len(dev):.1f} expected by chance).",
        f"- Discoveries at 10% false-discovery rate: {int(dev.fdr10.sum())}; confirmed before 2013 and after 2024: "
        f"{sum(c['confirmed'] for c in conf)}.",
        "",
        "| Asset | Driver | Predictive effect per 1 sd (dev) | t | Contemporaneous corr. (dev) |",
        "|---|---|---|---|---|",
    ]
    for _, r in dev.sort_values("p").head(12).iterrows():
        L.append(
            f"| {r.asset} | {r.predictor} | {r.predictive_effect_per_sd:+.2%} | {r.t_nw:.1f} | "
            f"{r.contemporaneous_corr:+.2f} |"
        )
    L += [
        "",
        "Contemporaneous correlation (moving together) is not prediction: only the predictive column could be traded.",
        "",
        *fp.markdown_index(),
    ]
    (out / "summary.md").write_text("\n".join(L) + "\n")
    return out


# ---------------------------------------------------------------------------
# EXP-044 execution delay and cost sensitivity of the adopted strategy
# ---------------------------------------------------------------------------
def exp_delay(cfg):
    from aurum.portfolio import simulate_portfolio

    out, tag = out_dir("delay", cfg)
    aur, prices, pc, rf = aurum_core_returns(cfg)
    idx = pc.index
    base_t = pc.base()
    rows, rets = [], {}
    sched = S.rebalance_days(idx, cfg["strategy"].get("rebalance", "daily"))
    from aurum.config import cost_bps

    costs = {t: cost_bps(t, cfg) for t in prices}
    for label, fill, delay in (
        ("next open (as traded)", "open", 0),
        ("next close", "close", 0),
        ("open, 1 extra day late", "open", 1),
        ("open, 2 extra days late", "open", 2),
        ("open, 5 extra days late", "open", 5),
    ):
        tgt = base_t.shift(delay).where(sched, np.nan)
        for cm in (0, 1, 2, 3, 5):
            pr = simulate_portfolio(
                prices,
                tgt,
                cost_bps={t: c * cm for t, c in costs.items()},
                cash_rate=rf,
                band=cfg["strategy"].get("rebalance_band", 0.05) * pc.sleeve,
                fill=fill,
            )
            p = performance(as_sim(pr.daily), rf)
            rows.append(
                {
                    "execution": label,
                    "cost_multiple": cm,
                    "cagr": p.get("cagr"),
                    "sharpe": p.get("sharpe"),
                    "max_drawdown": p.get("max_drawdown"),
                }
            )
            if cm == 1:
                rets[label] = pr.daily["ret"]
    t_ = pd.DataFrame(rows)
    t_.to_csv(out / "delay_costs.csv", index=False)
    fp = FigurePack(
        out,
        "EXP-044",
        "GLD, SLV, GDX, NEM, AEM, WPM (adopted strategy)",
        "per-ticker bps x multiple",
        "whole period 2006-2026",
    )
    fp.lines(
        t_.pivot(index="cost_multiple", columns="execution", values="sharpe"),
        "Sharpe vs transaction-cost multiple and execution timing",
        "cost_delay_sharpe",
        "cost multiple (1 = assumed)",
        "Sharpe",
    )
    fp.lines(
        t_.pivot(index="cost_multiple", columns="execution", values="cagr"),
        "CAGR vs transaction-cost multiple and execution timing",
        "cost_delay_cagr",
        "cost multiple",
        "CAGR",
    )
    fp.equity_drawdown(rets, "delay_equity")
    write_meta(out, cfg, {"exp": "EXP-044"}, prices)
    piv = t_.pivot(index="execution", columns="cost_multiple", values="sharpe")
    L = [
        f"# EXP-044: execution delay and cost sensitivity of the adopted strategy ({tag})",
        "",
        "Whole period, one account. Sharpe ratio by execution timing (rows) and multiple of the assumed costs "
        "(columns):",
        "",
        "| Execution | " + " | ".join(f"{c}× costs" for c in piv.columns) + " |",
        "|---|" + "---|" * len(piv.columns),
    ]
    L += [f"| {e} | " + " | ".join(f"{v:.2f}" for v in r) + " |" for e, r in piv.iterrows()]
    L += ["", *fp.markdown_index()]
    (out / "summary.md").write_text("\n".join(L) + "\n")
    return out


# ---------------------------------------------------------------------------
# EXP-045 robustness of SPY + gold, and downturn protection
# ---------------------------------------------------------------------------
DOWNTURNS = {
    "2008-09 recession": ("2007-12-01", "2009-06-30"),
    "2020 Covid recession": ("2020-02-01", "2020-04-30"),
    "2022 rate rises": ("2022-01-01", "2022-10-31"),
}


def exp_mix(cfg):
    out, tag = out_dir("mix", cfg)
    prices = load_universe(cfg, ["SPY", "GLD", "IEF"])
    aur, _, _, _ = aurum_core_returns(cfg)
    fund = {**prices, "AURUM": returns_as_prices(aur.daily["ret"])}
    idx = X.common_index(fund)
    fund = {t: p.reindex(idx) for t, p in fund.items()}
    rf = data.cash_rate(idx, cfg)
    fill = cfg["strategy"].get("fill", "open")
    costs = {**X.COSTS, "AURUM": 0.0}
    per = X.periods(idx[0])

    def frame(w: dict) -> pd.DataFrame:
        return pd.DataFrame(w, index=idx)

    def every(df, months):
        first = df.index.to_series().groupby([df.index.year, df.index.month]).transform("min") == df.index.to_series()
        keep = first & ((df.index.month - 1) % months == 0)
        return df.where(keep, np.nan)

    variants = {"SPY buy & hold": frame({"SPY": 1.0}).where(pd.Series(np.arange(len(idx)) == 0, index=idx))}
    for a in (0.1, 0.2, 0.3, 0.4, 0.5):
        variants[f"SPY/GLD {round((1 - a) * 100)}/{round(a * 100)} monthly"] = every(frame({"SPY": 1 - a, "GLD": a}), 1)
    base = frame({"SPY": 0.7, "GLD": 0.3})
    variants["SPY/GLD 70/30 quarterly"] = every(base, 3)
    variants["SPY/GLD 70/30 yearly"] = every(base, 12)
    variants["SPY/GLD 70/30 5-pt band"] = base
    variants["SPY/GLD/IEF 60/25/15 monthly"] = every(frame({"SPY": 0.6, "GLD": 0.25, "IEF": 0.15}), 1)
    cap = pd.DataFrame({t: S.vol_target_weight(X.realised_21d(fund[t]["Close"]), 0.20) for t in ("SPY", "GLD")})
    variants["70/30 + risk cap (20% vol)"] = base * cap
    trend = X.above_sma(fund["SPY"]["Close"], 200).fillna(1.0)
    variants["70/30 + SPY 200-day trend filter"] = base.assign(SPY=0.7 * trend)
    variants["SPY 70% + Aurum 30% monthly"] = every(frame({"SPY": 0.7, "AURUM": 0.3}), 1)
    sims = {}
    for name, tgt in variants.items():
        band = 0.05 if "band" in name or "risk cap" in name or "trend" in name else 0.0
        sims[name] = as_sim(X.run(fund, tgt, rf, costs=costs, band=band, fill=fill).daily)
    spy_r = sims["SPY buy & hold"].daily["ret"]
    table = score_table(sims, rf, spy_r, per)
    table.to_csv(out / "scorecard.csv", index=False)
    sc = table.set_index(["strategy", "period"])
    vs = []
    for n_, s_ in sims.items():
        row = {"strategy": n_}
        for p, (lo, hi) in {**per, "full": (None, None)}.items():
            c = compare_to(s_, sims["SPY buy & hold"], rf, lo, hi, cfg)
            row.update({f"{p}_{k}": v for k, v in c.items()})
        vs.append(row)
    vs = pd.DataFrame(vs).set_index("strategy")
    vs.to_csv(out / "vs_spy.csv")
    dn = []
    for n_, s_ in sims.items():
        for w, (a, b) in DOWNTURNS.items():
            from run_lab import window_stats

            ret, mdd = window_stats(s_, a, b)
            dn.append({"strategy": n_, "window": w, "return": ret, "max_drawdown": mdd})
    dn = pd.DataFrame(dn)
    dn.to_csv(out / "downturns.csv", index=False)

    # pre-registered tests
    def sharpe_up(n_, p):
        return sc.loc[(n_, p), "sharpe"] > sc.loc[("SPY buy & hold", p), "sharpe"]

    mixes = ["SPY/GLD 80/20 monthly", "SPY/GLD 70/30 monthly", "SPY/GLD 60/40 monthly"]
    t1a = all(sharpe_up(m, "full") and sum(sharpe_up(m, p) for p in per) >= 2 for m in mixes)
    t1b = all(sharpe_up(m, "full") for m in ("SPY/GLD 70/30 quarterly", "SPY/GLD 70/30 yearly"))
    t2 = sc.loc[("SPY/GLD 70/30 monthly", "full"), "cagr"] >= sc.loc[("SPY buy & hold", "full"), "cagr"] - 0.01
    d_ = dn.set_index(["strategy", "window"])
    prot = {}
    for n_ in ("70/30 + risk cap (20% vol)", "70/30 + SPY 200-day trend filter"):
        less = all(d_.loc[(n_, w), "return"] > d_.loc[("SPY/GLD 70/30 monthly", w), "return"] for w in DOWNTURNS)
        cost = sc.loc[("SPY/GLD 70/30 monthly", "full"), "cagr"] - sc.loc[(n_, "full"), "cagr"]
        prot[n_] = (less, cost)
    fp = FigurePack(
        out, "EXP-045", "SPY, GLD, IEF (+ Aurum core)", "SPY 2, GLD 3, IEF 3 bps", SPLIT_NOTE, f"fills: next {fill}"
    )
    show = [
        "SPY buy & hold",
        "SPY/GLD 70/30 monthly",
        "SPY/GLD 60/40 monthly",
        "70/30 + risk cap (20% vol)",
        "70/30 + SPY 200-day trend filter",
        "SPY 70% + Aurum 30% monthly",
    ]
    R = {k: sims[k].daily["ret"] for k in show}
    fp.equity_drawdown(R)
    fp.annual({k: R[k] for k in show[:3]})
    fp.rolling(R, spy_r)
    roll3 = pd.DataFrame({k: (1 + r).rolling(756).apply(np.prod, raw=True) ** (1 / 3) - 1 for k, r in R.items()})
    fp.lines(roll3, "Rolling 3-year annualised return", "rolling_3y", "date", "annualised return")
    mixgrid = pd.DataFrame(
        {
            p: [sc.loc[(m, p), "sharpe"] for m in [k for k in sims if "monthly" in k and "GLD" in k]]
            for p in [*per, "full"]
        },
        index=[k for k in sims if "monthly" in k and "GLD" in k],
    )
    fp.heatmap(mixgrid, "Sharpe ratio of each mix by period (SPY alone: see table)", "mix_sharpe_grid")
    dd_tbl = dn.pivot(index="strategy", columns="window", values="return").loc[show]
    fp.by_period(dd_tbl, "Return during each downturn window", "downturns")
    fp.tails(R)
    meta = write_meta(out, cfg, {"exp": "EXP-045", "fill": fill}, prices)
    L = [
        f"# EXP-045: S&P 500 + gold robustness and downturn protection ({tag}, next-{fill} fills)",
        "",
        f"Historical simulation, net of costs, {idx[0].date()} → {idx[-1].date()}.",
        "",
        "## Scorecard",
        "",
    ]
    L += period_md(table, list(per))
    L += [
        "",
        "## Versus SPY (whole period)",
        "",
        "| Strategy | ΔCAGR | ΔSharpe | resamples with higher Sharpe |",
        "|---|---|---|---|",
    ]
    for n_, r in vs.iterrows():
        L.append(
            f"| {n_} | {f_(r['full_d_cagr'], True)} | {f_(r['full_d_sharpe'])} | "
            + (f"{r['full_share_better']:.0%} |" if np.isfinite(r["full_share_better"]) else "– |")
        )
    L += [
        "",
        "## Downturns (return over the window)",
        "",
        "| Strategy | " + " | ".join(DOWNTURNS) + " |",
        "|---|" + "---|" * len(DOWNTURNS),
    ]
    for n_ in show:
        L.append(f"| {n_} | " + " | ".join(f_(d_.loc[(n_, w), "return"], True) for w in DOWNTURNS) + " |")
    L += [
        "",
        "## Pre-registered tests",
        "",
        "1a. Every mix 80/20–60/40 beats SPY's Sharpe overall and in ≥ 2 of 3 periods: "
        f"**{'PASS' if t1a else 'FAIL'}**",
        f"1b. 70/30 beats SPY's Sharpe with quarterly and yearly rebalancing: **{'PASS' if t1b else 'FAIL'}**",
        f"2. 70/30 CAGR within 1 point of SPY's: **{'PASS' if t2 else 'FAIL'}**",
    ]
    for n_, (less, cost) in prot.items():
        L.append(
            f"3. {n_}: loses less than 70/30 in every downturn: {'yes' if less else 'no'}; costs "
            f"{cost:+.1%} a year vs 70/30: **{'PASS' if less and cost <= 0.01 else 'FAIL'}**"
        )
    L += ["", *fp.markdown_index()]
    (out / "summary.md").write_text("\n".join(L) + "\n")
    print(meta["run_at"])
    return out


EXPS = {
    "sp500": exp_sp500,
    "trend": exp_trend,
    "meanrev": exp_meanrev,
    "vol": exp_vol,
    "candles": exp_candles,
    "ml": exp_ml,
    "macro": exp_macro,
    "delay": exp_delay,
    "mix": exp_mix,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", choices=list(EXPS), required=True)
    ap.add_argument("--fill", choices=["open", "close"])
    args = ap.parse_args()
    cfg = copy.deepcopy(CFG)
    if args.fill:
        cfg["strategy"]["fill"] = args.fill
    out = EXPS[args.exp](cfg)
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
