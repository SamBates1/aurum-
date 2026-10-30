"""EXP-046, EXP-047, EXP-048: 70/30 for a UK investor, over 1972-2026, and the range of outcomes to expect.

    python run_uk.py            (needs internet: Yahoo, FRED, github.com/datasets; run on GitHub via a "uk:" RUN line)

Writes research/experiments/results/<date>-uk-real/ with summary.md, CSV tables and figures.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from aurum import data
from aurum import engine as E
from aurum import spec as SP
from aurum import ukstudy as U
from aurum.config import CFG, ROOT, code_fingerprint, git_commit
from aurum.figures import FigurePack, _plt

RESULTS = ROOT / "research" / "experiments" / "results"


def pct(x, signed=False):
    if x is None or not np.isfinite(x):
        return "–"
    return f"{x:+.1%}" if signed else f"{x:.1%}"


def num(x):
    return "–" if x is None or not np.isfinite(x) else f"{x:.2f}"


def gbp_money(x):
    return f"£{x:,.0f}"


def exp046(cfg, out, L):
    lib = SP.library()
    usd = {t: data.daily_prices_from(t, SP.DEFAULT_START, cfg) for t in ("SPY", "GLD")}
    fx = data.daily_prices_from("GBPUSD=X", "2003-01-01", cfg)["Close"]  # dollars per pound
    gbp = {t: U.gbp_frame(usd[t], fx, U.UK_FUND_DRAG[t]) for t in usd}
    idx = gbp["SPY"].index.intersection(gbp["GLD"].index)
    rf_gbp = U.uk_cash_daily(idx, cfg)
    rf_usd = data.cash_rate(idx, cfg)
    specs = {
        "S&P fund only": lib["spy-buy-and-hold"],
        "70/30 (main)": lib["spy-gld-70-30-monthly"],
        "70/30 + risk cap (shadow)": lib["spy-gld-70-30-risk-cap"],
    }
    runs_gbp = {n: U.run_in_gbp(s, usd, gbp, rf_gbp) for n, s in specs.items()}
    runs_usd = {n: E.run_spec(s, usd, rf_usd, capital=1.0, index=idx) for n, s in specs.items()}
    # model check against the real UK funds
    checks = {}
    for t, tick in U.UK_FUNDS_YAHOO.items():
        try:
            actual = data.daily_prices_from(tick, "2010-01-01", cfg)["Close"]
            checks[t] = U.tracking_check(gbp[t]["Close"], actual)
        except Exception as exc:
            checks[t] = {"error": str(exc)[:150], "diff": np.nan}
    sm = {n: E.summary(r) for n, r in runs_gbp.items()}
    su = {n: E.summary(r) for n, r in runs_usd.items()}
    me = {n: U.month_end_stats(r.daily["ret"], rf_gbp) for n, r in runs_gbp.items()}
    for t, c in checks.items():
        if "monthly" in c:
            c.pop("monthly").to_csv(out / f"exp046_check_{U.UK_FUNDS_YAHOO[t]}.csv")
    t1 = all(np.isfinite(c.get("diff", np.nan)) and abs(c["diff"]) < 0.005 for c in checks.values())
    a, s = sm["70/30 (main)"], sm["S&P fund only"]
    t2 = a["cagr"] >= s["cagr"] - 0.01
    # risk measured on month-end values: daily pound returns carry exchange-rate timing noise (see the note)
    t3 = (
        me["70/30 (main)"]["sharpe"] > me["S&P fund only"]["sharpe"]
        and me["70/30 (main)"]["max_drawdown"] > me["S&P fund only"]["max_drawdown"]
    )
    L += [
        "## EXP-046: 70/30 as a UK investor (pounds, UK funds, fees, ISA)",
        "",
        f"Daily {idx[0].date()} to {idx[-1].date()}. Decisions from US prices; accounting in pounds "
        "at each day's GBP/USD; "
        "UK fund drag S&P +0.22%/yr, gold −0.28%/yr vs the US ETFs; platform fee 0.25%/yr; 5 bps "
        "per trade; cash at the "
        "UK 3-month rate. Historical simulation, not a forecast.",
        "",
        "| Strategy | CAGR in £ | CAGR in $ | Sharpe (£) | Worst fall (£) | Worst fall ($) | "
        "Volatility (£) | Worst year (£) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for n in specs:
        g, u = sm[n], su[n]
        L.append(
            f"| {n} | {pct(g['cagr'])} | {pct(u['cagr'])} | {num(g['sharpe'])} | "
            f"{pct(g['max_drawdown'])} | {pct(u['max_drawdown'])} | {pct(g['volatility'])} | "
            f"{pct(g['worst_year'])} |"
        )
    L += [
        "",
        "Measured on month-end values in pounds (the MAIN risk figures: the pound/dollar rate is recorded hours away "
        "from the US close, which adds day-to-day noise that cancels within a month, so the daily volatility above is "
        "overstated):",
        "",
        "| Strategy | CAGR | Volatility | Sharpe (vs UK cash) | Worst fall (month-end) | Worst year |",
        "|---|---|---|---|---|---|",
    ]
    for n in specs:
        x = me[n]
        L.append(
            f"| {n} | {pct(x['cagr'])} | {pct(x['volatility'])} | {num(x['sharpe'])} | "
            f"{pct(x['max_drawdown'])} | {pct(x['worst_year'])} |"
        )
    L += [
        "",
        "Downturns (return over the window, in pounds then dollars):",
        "",
        "| Strategy | 2008-09 | 2020 | 2022 |",
        "|---|---|---|---|",
    ]
    for n in specs:
        cells = []
        for lo, hi in (("2007-12-01", "2009-06-30"), ("2020-02-01", "2020-04-30"), ("2022-01-01", "2022-10-31")):
            cells.append(
                f"{pct(E.window_return(runs_gbp[n], lo, hi)[0], True)} (in $ "
                f"{pct(E.window_return(runs_usd[n], lo, hi)[0], True)})"
            )
        L.append(f"| {n} | " + " | ".join(cells) + " |")
    L += [
        "",
        "Model check (modelled UK fund vs the real fund's price, month-end, annual return):",
        "",
        "| Fund | Months | Real | Model | Difference | Correlation of monthly returns | Pence/pound fixes |",
        "|---|---|---|---|---|---|---|",
    ]
    for t, c in checks.items():
        if "error" in c:
            L.append(f"| {U.UK_FUNDS_YAHOO[t]} | – | – | – | unavailable: {c['error']} | – | – |")
        elif "start" not in c:
            L.append(f"| {U.UK_FUNDS_YAHOO[t]} | too little data | – | – | – | – | – |")
        else:
            L.append(
                f"| {U.UK_FUNDS_YAHOO[t]} | {c.get('start')} to {c.get('end')} | "
                f"{pct(c.get('actual_cagr'))} | {pct(c.get('model_cagr'))} | {pct(c['diff'], True)} | "
                f"{num(c.get('correlation'))} | {c.get('unit_fixes', 0)} |"
            )
    L += [
        "",
        f"**Test 1 (model realistic, < 0.5 pt/yr):** {'PASS' if t1 else 'FAIL'}. **Test 2 (70/30 "
        "CAGR within 1 pt of the S&P fund):** "
        f"{'PASS' if t2 else 'FAIL'}. **Test 3 (higher Sharpe and smaller worst fall):** {'PASS' if t3 else 'FAIL'}.",
        "",
    ]
    fp = FigurePack(
        out,
        "EXP-046",
        "SPY/GLD as UK funds (VUSA/SGLN) in GBP",
        "5 bps/trade, fund drag, 0.25% platform",
        "daily 2006-2026",
        "ISA, in pounds",
    )
    fp.equity_drawdown({n: r.daily["ret"] for n, r in runs_gbp.items()}, name="equity_drawdown_gbp")
    fp.annual({n: r.daily["ret"] for n, r in runs_gbp.items()}, name="annual_returns_gbp")
    pd.DataFrame({n: r.daily["ret"] for n, r in runs_gbp.items()}).to_csv(out / "exp046_daily_returns_gbp.csv")
    month_end = {n: (1 + r.daily["ret"]).groupby(r.daily.index.to_period("M")).prod() - 1 for n, r in runs_gbp.items()}
    return {
        "tests": [t1, t2, t3],
        "summary_gbp": sm,
        "summary_usd": su,
        "checks": checks,
        "month_end": month_end,
        "month_end_stats": me,
    }


def exp047(cfg, out, L):
    ld = U.long_data(cfg)
    st = U.long_study(ld)
    t = U.long_tests(st)
    L += [
        "## EXP-047: 70/30 over 1972-2026 (monthly averages)",
        "",
        f"Data: Shiller S&P 500 total return (dividends known to {ld['info']['dividends_known_until']}, then a "
        f"{ld['info']['filled_yield']:.2%} yield), World Bank gold, pounds per dollar. Costs 0.10% "
        "per trade, fund fees "
        "0.2% (S&P) and 0.25% (gold) a year. **Monthly averages smooth falls inside a month**: see "
        "the check at the end. "
        + (
            "Cash rates: " + "; ".join(f"{k}: {v}" for k, v in ld["info"].items() if k.startswith("cash"))
            if any(k.startswith("cash") for k in ld["info"])
            else ""
        ),
        "",
    ]
    for cur in ("USD", "GBP"):
        tt = t[cur]
        L += [
            f"### In {'dollars' if cur == 'USD' else 'pounds'}",
            "",
            "| Strategy | CAGR | Volatility | Sharpe | Worst fall | Worst year |",
            "|---|---|---|---|---|---|",
        ]
        for n, r in st[cur]["returns"].items():
            m = U.mstats(r, st[cur]["cash"])
            L.append(
                f"| {n} | {pct(m['cagr'])} | {pct(m['volatility'])} | {num(m['sharpe'])} | "
                f"{pct(m['max_drawdown'])} | {pct(m['worst_year'])} |"
            )
        L += ["", "| Bear market | S&P 500 | 70/30 | 70/30 fell less? |", "|---|---|---|---|"]
        for k, (s_, m_) in tt["bears"].items():
            L.append(f"| {k} | {pct(s_, True)} | {pct(m_, True)} | {'yes' if m_ > s_ else '**no**'} |")
        L += ["", "| Sub-period | S&P Sharpe | 70/30 Sharpe |", "|---|---|---|"]
        L += [f"| {k} | {num(a)} | {num(b)} |" for k, (a, b) in tt["subperiods"].items()]
        L += ["", "| Decade | S&P 500 | 70/30 |", "|---|---|---|"]
        L += [f"| {k} | {pct(a, True)} | {pct(b, True)} |" for k, (a, b) in tt["decades"].items()]
        L += [
            "",
            f"Worst 10-year return a year: S&P {pct(tt['worst_10y'][0], True)}, 70/30 {pct(tt['worst_10y'][1], True)}. "
            f"70/30 beat the S&P in {tt['share_10y_7030_better']:.0%} of 10-year periods.",
            "",
            f"**Test 1 (fell less in every bear market):** {'PASS' if tt['test1_all_bears_smaller_fall'] else 'FAIL'}. "
            "**Test 2 (higher Sharpe overall and in 2 of 3 sub-periods):** "
            f"{'PASS' if tt['test2_sharpe'] else 'FAIL'}. "
            f"**Test 3 (better worst decade):** {'PASS' if tt['test3_worst_decade'] else 'FAIL'}.",
            "",
        ]
    # smoothing check
    m = st["USD"]["returns"]
    L += [
        "### How much monthly averages smooth things (2006-07 to 2026-09, dollars)",
        "",
        "| Strategy | Monthly-average volatility | Worst fall (monthly avg) |",
        "|---|---|---|",
    ]
    for n in ("S&P 500", "70/30 S&P/gold"):
        mm = U.mstats(m[n].loc["2006-07":])
        L.append(f"| {n} | {pct(mm['volatility'])} | {pct(mm['max_drawdown'])} |")
    L += [
        "",
        "Daily data over the same years (EXP-045/designer): S&P volatility 19.3%, worst fall "
        "−55.2%; 70/30 volatility 14.8%, worst fall −38.5%. Long-history worst falls and "
        "volatility are therefore understated; comparisons between the two strategies are on equal "
        "terms.",
        "",
    ]
    fp = FigurePack(
        out,
        "EXP-047",
        "S&P 500 total return, gold (monthly averages)",
        "0.10%/trade, fund fees",
        "1972-2026 monthly",
        "monthly averages smooth falls",
    )
    for cur in ("USD", "GBP"):
        fp.equity_drawdown(st[cur]["returns"], name=f"long_equity_{cur.lower()}")
        fp.lines(
            pd.DataFrame({k: U.rolling_cagr(v) for k, v in st[cur]["returns"].items() if k != "Gold"}),
            f"Rolling 10-year return a year ({cur})",
            f"rolling_10y_{cur.lower()}",
            "end of 10-year period",
            "return a year",
        )
        bears = pd.DataFrame(t[cur]["bears"], index=["S&P 500", "70/30"]).T
        plt = _plt()
        fig, ax = plt.subplots(figsize=(10, 4.5))
        x = np.arange(len(bears))
        ax.bar(x - 0.2, bears["S&P 500"] * 100, 0.4, label="S&P 500", color="#eb6834")
        ax.bar(x + 0.2, bears["70/30"] * 100, 0.4, label="70/30", color="#2a78d6")
        ax.set_xticks(x, bears.index, rotation=20, ha="right", fontsize=8)
        ax.axhline(0, color="#888", lw=0.8)
        ax.set_ylabel(f"return over the window (%, {cur})")
        ax.legend()
        fp._save(fig, f"bear_markets_{cur.lower()}", f"Bear markets 1972-2026 ({cur})", "1972-2026")
    pd.DataFrame({f"{cur} {k}": v for cur in st for k, v in st[cur]["returns"].items()}).to_csv(
        out / "exp047_monthly_returns.csv"
    )
    return {"tests": t, "study": st}


def exp048(cfg, out, L, r046, r047):
    L += [
        "## EXP-048: the range of outcomes to expect (in pounds, after fees)",
        "",
        "10,000 simulated futures (block bootstrap, 12-month blocks). Main view: true month-end "
        "returns from EXP-046's daily "
        "data in pounds, 2006-2026, after UK fund costs and the platform fee. Second view: "
        "1972-2026 monthly series scaled "
        "to daily-data volatility. Nominal pounds, before inflation. The future can be worse than "
        "anything in the sample.",
        "",
        "**Read this first:** 2006-2026 was unusually kind to a UK holder of 70/30 (gold rose about fourfold in pounds "
        "and the pound fell against the dollar, which lifts the value of dollar assets). The main view repeats "
        "those 20 "
        "years, so it is the OPTIMISTIC view. The 1972-2026 view includes harder decades (the early-1980s gold crash, "
        "the 1990s when gold fell) and is the more CAUTIOUS guide.",
        "",
    ]
    out_tables = {}
    for label, series in (
        ("70/30 (main)", r046["month_end"]["70/30 (main)"]),
        ("S&P fund only", r046["month_end"]["S&P fund only"]),
    ):
        for plan, lump, monthly in (("£1,000 once", 1000, 0), ("£1,000 + £100 a month", 1000, 100)):
            tab = U.outcomes(series.iloc[1:], lump=lump, monthly=monthly)
            out_tables[(label, plan)] = tab
            L += [
                f"### {label}: {plan}",
                "",
                "| Years | Paid in | Bad (1 in 20) | Below typical | Typical (median) | Above typical | "
                "Good (1 in 20) | Chance of ending below what you paid in | Chance of a 20%+ fall on the "
                "way |",
                "|---|---|---|---|---|---|---|---|---|",
            ]
            for _, rw in tab.iterrows():
                L.append(
                    f"| {rw['years']:.0f} | {gbp_money(rw['paid_in'])} | {gbp_money(rw['p5'])} | "
                    f"{gbp_money(rw['p25'])} | {gbp_money(rw['median'])} | "
                    f"{gbp_money(rw['p75'])} | {gbp_money(rw['p95'])} | {rw['chance_below_paid_in']:.0%} | "
                    f"{rw['chance_fall_20pct']:.0%} |"
                )
            L.append("")
    # second view: long history, volatility scaled to daily data
    long_m = r047["study"]["GBP"]["returns"]["70/30 S&P/gold"]
    short = r046["month_end"]["70/30 (main)"]
    scale = float(short.std() / long_m.loc["2006-07":].std())
    scaled = long_m.mean() + (long_m - long_m.mean()) * scale - U.PLATFORM_FEE / 12
    tab = U.outcomes(scaled, lump=1000, monthly=100)
    out_tables[("70/30 long history (scaled)", "£1,000 + £100 a month")] = tab
    L += [
        f"### Second view, 70/30 1972-2026 (volatility scaled x{scale:.2f}): £1,000 + £100 a month",
        "",
        "| Years | Paid in | Bad (1 in 20) | Typical | Good (1 in 20) | Chance below paid in |",
        "|---|---|---|---|---|---|",
    ]
    for _, rw in tab.iterrows():
        L.append(
            f"| {rw['years']:.0f} | {gbp_money(rw['paid_in'])} | {gbp_money(rw['p5'])} | "
            f"{gbp_money(rw['median'])} | {gbp_money(rw['p95'])} | {rw['chance_below_paid_in']:.0%} |"
        )
    L.append("")
    fp = FigurePack(
        out,
        "EXP-048",
        "70/30 and S&P fund in GBP",
        "UK fund costs + 0.25% platform",
        "bootstrap of 2006-2026 month-end returns",
        "nominal pounds",
    )
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    for ax, label in zip(axes, ("70/30 (main)", "S&P fund only")):
        tab = out_tables[(label, "£1,000 + £100 a month")]
        yrs = tab["years"]
        ax.fill_between(yrs, tab["p5"], tab["p95"], color="#2a78d6", alpha=0.15, label="1 in 20 bad to 1 in 20 good")
        ax.fill_between(yrs, tab["p25"], tab["p75"], color="#2a78d6", alpha=0.3, label="middle half")
        ax.plot(yrs, tab["median"], color="#2a78d6", lw=2, label="typical")
        ax.plot(yrs, tab["paid_in"], color="#555", lw=1.2, ls="--", label="money paid in")
        ax.set_title(label)
        ax.set_xlabel("years")
    axes[0].set_ylabel("value (£)")
    axes[0].legend(fontsize=8)
    fp._save(fig, "outcome_ranges", "£1,000 + £100 a month: range of outcomes", "simulated futures")
    pd.concat({f"{a} | {b}": t for (a, b), t in out_tables.items()}).to_csv(out / "exp048_outcomes.csv")
    return out_tables


def main():
    cfg = CFG
    run_at = datetime.now(timezone.utc)
    out = RESULTS / f"{run_at:%Y-%m-%d-%H%M}-uk-{'synthetic' if cfg.get('offline') else 'real'}"
    out.mkdir(parents=True, exist_ok=True)
    L = [
        f"# EXP-046, EXP-047, EXP-048 results ({run_at:%Y-%m-%d %H:%M} UTC)",
        "",
        f"Code {code_fingerprint()}, commit {git_commit()}. Historical simulations, net of the "
        "stated costs; not forecasts and not personal financial advice.",
        "",
    ]
    r046 = exp046(cfg, out, L)
    r047 = exp047(cfg, out, L)
    exp048(cfg, out, L, r046, r047)
    L += ["## Figures", ""] + [f"- [{p.name}](figures/{p.name})" for p in sorted((out / "figures").glob("*.png"))]
    (out / "summary.md").write_text("\n".join(L) + "\n")
    (out / "metadata.json").write_text(
        json.dumps(
            {
                "run_at": run_at.isoformat(),
                "code": code_fingerprint(),
                "commit": git_commit(),
                "exp046_tests": r046["tests"],
                "exp046_checks": r046["checks"],
            },
            default=str,
            indent=1,
        )
    )
    print("\n".join(L))
    print(f"Wrote {out / 'summary.md'}")


if __name__ == "__main__":
    main()
