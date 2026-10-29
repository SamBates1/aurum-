"""Fair Test: the validation pipeline behind the designer's "Send for Fair Test" button.

It applies the SAME pre-registered rules as the research labs (README "Lab rules", run_lab.lab_verdict), so a strategy
built in the designer is judged exactly like every earlier experiment:

  integrity   1 valid definition   2 enough clean data   3 no look-ahead (targets recomputed on truncated data must
              match)   4 accounting (no borrowing, no negative cash)
  evidence    5 development period 2013-10-18 -> 2023-12-31 against the benchmark, net of costs, with a
              stationary-bootstrap comparison of Sharpe ratios   6 the same at 2x costs   7 execution: next-close fills
              and one extra day's delay   8 parameter sensitivity (+-20% on every number in the rules) and PBO
              9 deflated Sharpe ratio for every version tried (registry)   10 confirmation on the 2024+ holdout AND on
              the pre-2013 period
  verdict     signal path: dSharpe >= 0.10, >= 80% of resamples better, still >= 0 at 2x costs
              risk path:   drawdown per unit of volatility >= 20% smaller, dSharpe >= -0.05 (also at 2x costs)
              then DSR >= 0.50, then the improvement must hold on BOTH the holdout and pre-2013.
              PASSED only if all of that holds and the integrity checks pass and the result is not fragile.

A pass is evidence, not permission: paper trading still needs the owner's approval (aurum/gates.py).
"""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import engine as E
from . import spec as SP
from . import stats
from .backtest import risk_free_daily
from .config import CFG, ROOT, code_fingerprint, git_commit
from .indicators import INDICATORS

FAIRTEST_DIR = ROOT / "research" / "fairtests"
DEV_START, HOLD_START = pd.Timestamp("2013-10-18"), pd.Timestamp("2024-01-01")


def periods(index: pd.DatetimeIndex) -> dict:
    first = index[0]
    out = {}
    if first < DEV_START - pd.Timedelta(days=365):
        out["pre"] = (first, DEV_START - pd.Timedelta(days=1))
    out["dev"] = (max(first, DEV_START), HOLD_START - pd.Timedelta(days=1))
    out["holdout"] = (HOLD_START, None)
    return out


def benchmark_spec(spec: dict, library: dict[str, dict] | None = None) -> dict:
    b = spec.get("benchmark", "SPY")
    library = library if library is not None else SP.library()
    if b in library:
        return library[b]
    return SP.validate(
        {
            "id": f"{str(b).lower()}-buy-and-hold",
            "name": f"{b} buy and hold",
            "universe": [b],
            "base_weights": {b: 1.0},
            "schedule": {"rebalance": "once"},
            "start": spec.get("start", SP.DEFAULT_START),
        }
    )


def compare(v: E.StrategyRun, b: E.StrategyRun, lo, hi, cfg) -> dict:
    """Same quantities as run_experiments.compare: dSharpe, bootstrap share of resamples better, drawdown per unit of
    volatility relative to the benchmark."""
    dv, db = E.slice_daily(v.daily, lo, hi), E.slice_daily(b.daily, lo, hi)
    pv, pb = E.summary(v, lo, hi), E.summary(b, lo, hi)
    ex_v = dv["ret"] - risk_free_daily(v.rf, dv.index)
    ex_b = db["ret"] - risk_free_daily(b.rf, db.index)
    rc = cfg["research"]
    boot = stats.bootstrap_sharpe(ex_v, ex_b, rc["bootstrap_block_days"], rc["bootstrap_reps"], rc["seed"])
    mdd_v = abs(pv.get("max_drawdown", np.nan)) / (pv.get("volatility") or np.nan)
    mdd_b = abs(pb.get("max_drawdown", np.nan)) / (pb.get("volatility") or np.nan)
    return {
        "sharpe": pv.get("sharpe"),
        "bench_sharpe": pb.get("sharpe"),
        "cagr": pv.get("cagr"),
        "bench_cagr": pb.get("cagr"),
        "max_drawdown": pv.get("max_drawdown"),
        "bench_max_drawdown": pb.get("max_drawdown"),
        "d_sharpe": (pv.get("sharpe") or np.nan) - (pb.get("sharpe") or np.nan),
        "share_better": boot.get("share_resamples_better", np.nan),
        "diff_p05": boot.get("diff_p05", np.nan),
        "diff_p95": boot.get("diff_p95", np.nan),
        "dd_rel": 1 - mdd_v / mdd_b if mdd_b else np.nan,
    }


def verdict(dev: dict, dev2x: dict, hold: dict | None, pre: dict | None, dsr: float) -> tuple[str, str]:
    """Pre-registered rule (identical to run_lab.lab_verdict). Returns (status, explanation)."""
    d_sh, share, dd_rel = dev["d_sharpe"], dev["share_better"], dev["dd_rel"]
    signal = d_sh >= 0.10 and share >= 0.80 and dev2x["d_sharpe"] >= 0.0
    risk = dd_rel >= 0.20 and d_sh >= -0.05 and dev2x["d_sharpe"] >= -0.05
    if (signal or risk) and dsr >= 0.50:

        def holds(p):
            if p is None:
                return False
            return p["d_sharpe"] >= 0.0 if signal else (p["dd_rel"] >= 0.0 and p["d_sharpe"] >= -0.10)

        h, p = holds(hold), holds(pre)
        path = "better return per unit of risk" if signal else "smaller falls for the same risk"
        if h and p:
            return "passed", f"Passed on the {path} path and held on both the 2024+ holdout and pre-2013."
        failed = " and ".join(n for n, ok in (("2024+ holdout", h), ("pre-2013", p)) if not ok)
        return "failed", f"Looked better in development ({path}) but did not hold on the {failed}."
    if (signal or risk) and dsr < 0.50:
        return (
            "inconclusive",
            f"Better in development, but the deflated Sharpe ratio is {dsr:.2f} (< 0.50): too likely "
            "luck given the number of versions tried.",
        )
    if d_sh < 0 and dd_rel < 0.20:
        return (
            "failed",
            "Worse than the benchmark in development: lower Sharpe ratio and no meaningful reduction in falls.",
        )
    return "inconclusive", "Neither clearly better nor clearly worse than the benchmark in development."


def lookahead_check(spec: dict, prices: dict, cuts=(0.4, 0.6, 0.8)) -> tuple[bool, str]:
    full = E.compile_targets(spec, prices)
    idx = full.index
    worst = 0.0
    for q in cuts:
        cut = idx[int(len(idx) * q)]
        part = E.compile_targets(spec, {t: p.loc[:cut] for t, p in prices.items()}, idx[idx <= cut])
        a = full.raw_target.loc[:cut].to_numpy(float)
        b = part.raw_target.to_numpy(float)
        same = np.isclose(a, b, rtol=1e-9, atol=1e-12, equal_nan=True)
        if not same.all():
            worst = max(worst, float(np.nanmax(np.abs(a - b))))
    if worst:
        return False, f"targets changed when later data was removed (max difference {worst:.4f}): the rules look ahead"
    return True, f"targets identical when data after {len(cuts)} cut dates were removed"


def accounting_check(run: E.StrategyRun) -> tuple[bool, str]:
    d = run.daily
    problems = []
    if (d["cash"] < -1e-6 * d["value"]).any():
        problems.append("cash went negative")
    if (d["exposure"] > 1 + 1e-6).any():
        problems.append("held more than 100% of the account")
    if (d["value"] <= 0).any():
        problems.append("account value hit zero")
    if problems:
        return False, "; ".join(problems)
    return True, "no borrowing, no negative cash, costs charged on every order"


def data_check(spec: dict, prices: dict, index) -> tuple[bool, str]:
    years = len(index) / 252
    gaps = pd.Series(index).diff().dt.days.max() if len(index) > 1 else 0
    bad = [t for t in SP.assets_needed(spec) if (prices[t][["Open", "Close"]].reindex(index) <= 0).any().any()]
    ok = years >= 8 and gaps <= 7 and not bad
    return (
        ok,
        f"{years:.1f} years of common daily data ({index[0].date()} to {index[-1].date()}); longest gap {gaps} days"
        + (f"; non-positive prices in {', '.join(bad)}" if bad else ""),
    )


def perturbations(spec: dict, limit: int = 12) -> list[tuple[str, dict]]:
    """Every number in the rules nudged by +-20% (one at a time), within allowed bounds."""
    s = SP.normalise(spec)
    out = []

    def add(label, mutate):
        v = copy.deepcopy(s)
        try:
            mutate(v)
            SP.validate(v)
            out.append((label, v))
        except (SP.SpecError, KeyError, ValueError):
            pass

    uni = s["universe"]
    if len(uni) >= 2 and s["base_weights"].get(uni[0], 0) > 0:
        a, b = uni[0], uni[1]
        for dlt in (-0.1, 0.1):

            def mw(v, dlt=dlt):
                v["base_weights"][a] = round(v["base_weights"][a] + dlt, 4)
                v["base_weights"][b] = round(v["base_weights"].get(b, 0) - dlt, 4)

            add(f"{a} weight {dlt:+.0%}", mw)
    if s["sizing"]["method"] != "fixed":
        for f in (0.8, 1.2):
            add(
                f"target volatility x{f}",
                lambda v, f=f: v["sizing"].update(target_vol=round(v["sizing"]["target_vol"] * f, 4)),
            )
            add(
                f"volatility window x{f}",
                lambda v, f=f: v["sizing"].update(vol_window=int(round(v["sizing"]["vol_window"] * f))),
            )
    if s["schedule"]["band"] > 0:
        for f in (0.5, 1.5):
            add(f"band x{f}", lambda v, f=f: v["schedule"].update(band=round(v["schedule"]["band"] * f, 4)))
    for gi, g in enumerate(s["signals"]):
        for ci, c in enumerate(g["conditions"]):
            for side in ("left", "right"):
                o = c[side]
                if isinstance(o, float):
                    if o != 0:
                        for f in (0.8, 1.2):
                            add(
                                f"{g['id']} threshold x{f}",
                                lambda v, f=f, gi=gi, ci=ci, side=side: v["signals"][gi]["conditions"][ci].__setitem__(
                                    side, v["signals"][gi]["conditions"][ci][side] * f
                                ),
                            )
                    continue
                for p in INDICATORS[o["ind"]].params:
                    for f in (0.8, 1.2):

                        def mp(v, f=f, gi=gi, ci=ci, side=side, p=p):
                            op = v["signals"][gi]["conditions"][ci][side]
                            val = op[p.name] * f
                            op[p.name] = int(round(val)) if p.integer else round(val, 4)

                        add(f"{g['id']} {o['ind']} {p.name} x{f}", mp)
    ts = s["exits"].get("trailing_stop")
    if ts:
        for f in (0.8, 1.2):
            add(
                f"trailing stop x{f}",
                lambda v, f=f: v["exits"]["trailing_stop"].update(pct=round(v["exits"]["trailing_stop"]["pct"] * f, 4)),
            )
    return out[:limit]


def run_fair_test(
    spec: dict,
    prices: dict[str, pd.DataFrame],
    rf,
    *,
    registry=None,
    library: dict | None = None,
    cfg: dict = CFG,
    data_label: str = "",
    progress=None,
) -> dict:
    """Run every stage; returns a JSON-able result with each check, the numbers and the verdict."""

    def step(msg, frac):
        if progress:
            progress(msg, frac)

    s = SP.validate(spec)
    h = SP.spec_hash(s)
    bspec = benchmark_spec(s, library)
    checks = []

    def add(name, ok, detail, kind="check"):
        checks.append({"name": name, "passed": None if ok is None else bool(ok), "detail": detail, "kind": kind})

    add("Valid definition", True, f"{s['id']} v{s['version']}, hash {h}")
    need = sorted(set(SP.assets_needed(s)) | set(SP.assets_needed(bspec)))
    missing = [t for t in need if t not in prices]
    if missing:
        add("Data", False, f"missing prices for {', '.join(missing)}")
        return _finish(s, h, checks, "failed", "Cannot test without data for every asset.", {}, data_label)
    idx = None
    for t in need:
        idx = prices[t].index if idx is None else idx.intersection(prices[t].index)
    idx = idx.sort_values()
    idx = idx[idx >= pd.Timestamp(s["start"])]
    step("checking data", 0.05)
    ok, why = data_check(s, prices, idx)
    add("Enough clean data", ok, why)
    step("checking for look-ahead", 0.1)
    ok_la, why = lookahead_check(s, {t: prices[t] for t in SP.assets_needed(s)})
    add("No look-ahead", ok_la, why)

    step("backtesting strategy and benchmark", 0.2)
    v = E.run_spec(s, prices, rf, index=idx)
    b = E.run_spec(bspec, prices, rf, index=idx)
    v2 = E.run_spec(s, prices, rf, index=idx, cost_mult=2.0 * s["execution"]["cost_mult"])
    b2 = E.run_spec(bspec, prices, rf, index=idx, cost_mult=2.0)
    ok_acc, why = accounting_check(v)
    add("Accounting", ok_acc, why)

    per = periods(idx)
    step("comparing periods", 0.35)
    cmp = {p: compare(v, b, lo, hi, cfg) for p, (lo, hi) in per.items()}
    cmp["full"] = compare(v, b, None, None, cfg)
    dev2x = compare(v2, b2, *per["dev"], cfg)
    if registry is not None:
        registry.view_holdout(h, "fair test")

    step("execution stress", 0.5)
    vc = E.run_spec(s, prices, rf, index=idx, fill="close")
    vd = E.run_spec(s, prices, rf, index=idx, delay_days=1)
    sh_dev = cmp["dev"]["sharpe"]
    sh_close = E.summary(vc, *per["dev"]).get("sharpe")
    sh_delay = E.summary(vd, *per["dev"]).get("sharpe")
    drop = sh_dev - min(sh_close, sh_delay)
    add(
        "Execution: next-close fills and 1 day late",
        drop <= 0.10,
        f"development Sharpe {sh_dev:.2f}; next-close fills {sh_close:.2f}; one day late {sh_delay:.2f}",
    )

    step("parameter sensitivity", 0.6)
    pert = perturbations(s)
    sens, dev_rets = [], {"as defined": E.slice_daily(v.daily, *per["dev"])["ret"]}
    for k, (lab, ps) in enumerate(pert):
        r = E.run_spec(ps, prices, rf, index=idx)
        sens.append({"change": lab, "dev_sharpe": E.summary(r, *per["dev"]).get("sharpe")})
        dev_rets[lab] = E.slice_daily(r.daily, *per["dev"])["ret"]
        step(f"parameter sensitivity ({k + 1}/{len(pert)})", 0.6 + 0.25 * (k + 1) / max(1, len(pert)))
    if sens:
        worst = min(x["dev_sharpe"] for x in sens)
        fragile = worst < sh_dev - 0.15
        add(
            "Not fragile (+-20% on every number)",
            not fragile,
            f"{len(sens)} nudged versions: development Sharpe from {worst:.2f} to "
            f"{max(x['dev_sharpe'] for x in sens):.2f} (as defined {sh_dev:.2f})",
        )
        pbo = stats.probability_of_backtest_overfitting(pd.DataFrame(dev_rets))
    else:
        fragile = False
        add(
            "Not fragile (+-20% on every number)",
            None,
            "no adjustable numbers in this strategy (nothing to tune)",
            "info",
        )
        pbo = {"pbo": float("nan"), "n_splits": 0}

    step("deflating for the number of tries", 0.9)
    ex = E.slice_daily(v.daily, *per["dev"])["ret"]
    ex = ex - risk_free_daily(rf, ex.index)
    trial = list(registry.trial_sharpes()) if registry is not None else []
    n_prior = (
        registry.prior_trials if registry is not None else int((cfg.get("registry") or {}).get("prior_trials", 100))
    )
    var = float(np.var(trial, ddof=1)) if len(trial) >= 5 else (0.32 / np.sqrt(252)) ** 2
    from .stats import expected_max_sharpe, probabilistic_sharpe

    n_tr = len(trial) + n_prior
    dsr = probabilistic_sharpe(ex, expected_max_sharpe(max(n_tr, 2), var))
    add(
        "Deflated Sharpe ratio",
        dsr >= 0.5,
        f"DSR {dsr:.2f} allowing for {n_tr} versions tried (needs >= 0.50)",
        "evidence",
    )

    status, why = verdict(cmp["dev"], dev2x, cmp.get("holdout"), cmp.get("pre"), dsr)
    integrity = all(c["passed"] for c in checks[:4] if c["passed"] is not None) and ok_acc
    if not integrity:
        status, why = (
            "failed",
            "Integrity check failed (data, look-ahead or accounting): results cannot be trusted. " + why,
        )
    elif status == "passed" and fragile:
        status, why = (
            "inconclusive",
            "Passed the rules, but small changes to its numbers change the result a lot (fragile). " + why,
        )
    numbers = {
        "periods": {
            k: [str(a.date()) if a is not None else None, str(bb.date()) if bb is not None else None]
            for k, (a, bb) in per.items()
        },
        "comparison": cmp,
        "dev_2x_costs": dev2x,
        "execution": {"dev_sharpe": sh_dev, "next_close": sh_close, "one_day_late": sh_delay},
        "sensitivity": sens,
        "pbo": pbo,
        "dsr": dsr,
        "n_trials": n_tr,
        "benchmark": bspec["name"],
        "summary_full": {
            k: (str(x) if not isinstance(x, (int, float)) or x is None else x) for k, x in E.summary(v).items()
        },
    }
    if registry is not None:
        registry.register(s)
        registry.log_run(
            h,
            "fair_test",
            period="full",
            data_label=data_label,
            code_fp=code_fingerprint(),
            git_commit=git_commit(),
            sharpe_daily=float(ex.mean() / ex.std(ddof=1)) if ex.std(ddof=1) > 0 else None,
            metrics={"status": status, "dsr": dsr, "dev": cmp["dev"]},
        )
    step("done", 1.0)
    return _finish(s, h, checks, status, why, numbers, data_label)


def _finish(s, h, checks, status, why, numbers, data_label) -> dict:
    return {
        "strategy_id": s["id"],
        "name": s["name"],
        "version": s["version"],
        "spec_hash": h,
        "status": status,
        "explanation": why,
        "checks": checks,
        "numbers": numbers,
        "data_label": data_label,
        "code_fingerprint": code_fingerprint(),
        "git_commit": git_commit(),
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "spec": s,
    }


def _f(x, pct=False, signed=False):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "–"
    if pct:
        return f"{x:+.1%}" if signed else f"{x:.1%}"
    return f"{x:+.2f}" if signed else f"{x:.2f}"


def report_markdown(res: dict) -> str:
    n = res["numbers"]
    lines = [
        f"# Fair Test: {res['name']} (v{res['version']}, hash `{res['spec_hash']}`)",
        "",
        f"**Verdict: {res['status'].upper()}**. {res['explanation']}",
        "",
        "Historical backtest, net of costs; not paper or live trading. "
        f"Data: {res['data_label'] or 'see metadata'}. Code {res['code_fingerprint']}, commit "
        f"{res['git_commit']}, run {res['run_at']}.",
        "",
        "## Checks",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    for c in res["checks"]:
        r = "info" if c["passed"] is None else ("pass" if c["passed"] else "FAIL")
        lines.append(f"| {c['name']} | {r} | {c['detail']} |")
    if n.get("comparison"):
        lines += [
            "",
            f"## Against the benchmark ({n['benchmark']})",
            "| Period | Dates | Sharpe | Benchmark | dSharpe | Resamples better | CAGR | Benchmark "
            "CAGR | Worst fall | Benchmark worst fall | Drawdown/vol improvement |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for p in ("pre", "dev", "holdout", "full"):
            c = n["comparison"].get(p)
            if not c:
                continue
            d = n["periods"].get(p, ["start", "end"])
            lines.append(
                f"| {p} | {d[0] or 'start'} to {d[1] or 'latest'} | {_f(c['sharpe'])} | "
                f"{_f(c['bench_sharpe'])} | {_f(c['d_sharpe'], signed=True)} | "
                f"{_f(c['share_better'], pct=True)} | {_f(c['cagr'], pct=True)} | {_f(c['bench_cagr'], pct=True)} | "
                f"{_f(c['max_drawdown'], pct=True)} | "
                f"{_f(c['bench_max_drawdown'], pct=True)} | {_f(c['dd_rel'], pct=True, signed=True)} |"
            )
        d2 = n["dev_2x_costs"]
        lines += [
            "",
            f"Development period at 2x costs: dSharpe {_f(d2['d_sharpe'], signed=True)}. DSR "
            f"{_f(n['dsr'])} for {n['n_trials']} versions tried. "
            f"PBO across the nudged versions: {_f(n['pbo'].get('pbo'), pct=True)}.",
        ]
    if n.get("sensitivity"):
        lines += ["", "## Sensitivity (development Sharpe)", "| Change | Sharpe |", "|---|---|"]
        lines += [f"| {x['change']} | {_f(x['dev_sharpe'])} |" for x in n["sensitivity"]]
    lines += [
        "",
        "## Rules used (pre-registered, same as run_lab.lab_verdict)",
        "Signal path: dSharpe >= 0.10 with >= 80% of bootstrap resamples better and >= 0 at 2x "
        "costs. Risk path: drawdown per "
        "unit of volatility >= 20% smaller with dSharpe >= -0.05 (also at 2x costs). Then DSR >= "
        "0.50, then the improvement "
        "must hold on both the 2024+ holdout and pre-2013. A pass does not start paper trading: "
        "the owner must approve it.",
    ]
    return "\n".join(lines) + "\n"


def save_report(res: dict, folder: Path | None = None) -> Path:
    """Real-data reports go to research/fairtests (committed); synthetic (offline) ones to logs/, never mixed in."""
    if folder is None and str(res.get("data_label", "")).upper().startswith("SYNTHETIC"):
        folder = ROOT / "logs" / "fairtests-synthetic"
    folder = Path(folder or FAIRTEST_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"{res['run_at'][:10]}-{res['strategy_id']}-{res['spec_hash']}"
    (folder / f"{stem}.md").write_text(report_markdown(res))
    (folder / f"{stem}.json").write_text(json.dumps(res, indent=1, default=_json_default))
    return folder / f"{stem}.md"


def _json_default(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, (pd.Timestamp,)):
        return str(o.date())
    return str(o)


def latest_results(folder: Path | None = None, cfg: dict = CFG) -> dict[str, dict]:
    """Latest saved Fair Test per spec hash (offline mode also sees synthetic reports, clearly labelled)."""
    out = {}
    paths = sorted(Path(folder or FAIRTEST_DIR).glob("*.json"))
    if folder is None and cfg.get("offline"):
        paths += sorted((ROOT / "logs" / "fairtests-synthetic").glob("*.json"))
    for p in paths:
        try:
            r = json.loads(p.read_text())
        except Exception:
            continue
        out[r["spec_hash"]] = r | {"_file": str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)}
    return out
