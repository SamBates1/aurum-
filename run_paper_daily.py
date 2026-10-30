"""Daily paper trading on GitHub (simulated money only), run after every US close by
.github/workflows/paper-trading.yml.

For each strategy under paper.strategies in config.yaml that passes every eligibility gate, and for every completed
trading day not yet processed:
  1 a decision made at the previous close fills at THIS day's official opening price (exactly the backtest's
    next-open convention), after the risk engine and the safety checks;
  2 the strategy decides on this day's close (same engine as the backtest, designer and Decision Board);
  3 the account is valued at the close.
A brand-new ledger starts from the latest completed day. Missed days are caught up in order.

Writes (committed by the workflow): research/paper/<ledger>.json, research/paper/journal.md (one line per event),
research/paper/status.md (today's overview) and, with --weekly, research/paper/weekly-<date>.md.

    python run_paper_daily.py [--weekly]
"""

from __future__ import annotations

import argparse
from datetime import timezone

import numpy as np
import pandas as pd

from aurum import data, gates
from aurum import decision_board as DB
from aurum import engine as E
from aurum import fairtest as FT
from aurum import spec as SP
from aurum import spec_paper as SPP
from aurum.config import CFG, ROOT

PAPER_DIR = ROOT / "research" / "paper"


def ny(day: pd.Timestamp, hhmm: str):
    return pd.Timestamp(f"{day.date()} {hhmm}", tz="America/New_York").tz_convert(timezone.utc).to_pydatetime()


def journal(lines: list[str]) -> None:
    if not lines:
        return
    path = PAPER_DIR / "journal.md"
    head = (
        ""
        if path.exists()
        else "# Paper-trading journal (simulated money)\n\nNewest at the bottom. Times are New York trading days.\n\n"
    )
    with open(path, "a") as fh:
        fh.write(head + "\n".join(lines) + "\n")


def process(tr: SPP.SpecPaperTrader, daily: dict[str, pd.DataFrame]) -> list[str]:
    st = tr.book.state
    uni = tr.spec["universe"]
    idx = None
    for t in SP.assets_needed(tr.spec):
        idx = daily[t].index if idx is None else idx.intersection(daily[t].index)
    last = st.get("last_processed")
    todo = idx[idx > pd.Timestamp(last)] if last else idx[-1:]
    tag = f"[{tr.role}] {tr.spec['id']}"
    log = []
    for d in todo:
        upto = {t: p.loc[:d] for t, p in daily.items()}
        if st.get("pending") and pd.Timestamp(st["pending"]["decided"]) < d:
            n_before = len(st["trades"])
            opens = {t: float(daily[t].at[d, "Open"]) for t in uni}
            prev = {t: p.loc[: d - pd.Timedelta(days=1), "Close"] for t, p in daily.items() if t in uni}
            msgs = tr.execute(opens, prev, 0, now=ny(d, "09:35"))
            for x in st["trades"][n_before:]:
                x["time"] = f"{d.date()} (official open)"
            log += [f"- {d.date()} {tag}: {m}" for m in msgs]
        pend = tr.decide(upto)
        if pend:
            log.append(
                f"- {d.date()} {tag}: decided at the close: targets "
                + ", ".join(f"{k} {v:.0%}" for k, v in pend["targets"].items())
                + " (fills at the next official open)"
            )
        closes = {t: float(daily[t].at[d, "Close"]) for t in uni}
        tr.book.mark_prices(closes)
        eq = tr.book.equity()
        hist = [h for h in st["history"] if h.get("time") != str(d.date())]
        hist.append({"time": str(d.date()), "equity": round(eq, 2)})
        st["history"] = hist
        st["peak_equity"] = max(float(st.get("peak_equity", eq)), eq)
        st["last_processed"] = str(d.date())
        st.setdefault("started", str(d.date()))
    tr.book.save()
    return log


def status_md(traders, daily) -> str:
    lines = ["# Paper trading status (simulated money)", ""]
    for tr in traders:
        st = tr.book.state
        eq = tr.book.equity()
        start = float(CFG["paper"]["starting_cash"])
        held = ", ".join(f"{t} {p['qty'] * p['last_price'] / eq:.0%}" for t, p in st["positions"].items()) or "all cash"
        nxt = DB.next_decision_day(tr.spec, pd.Timestamp(st["last_processed"])) if st.get("last_processed") else None
        lines += [
            f"## {tr.spec['name']} ({'MAIN' if tr.role == 'main' else 'SHADOW, evidence only'})",
            "",
            f"- Equity **${eq:,.2f}** ({eq / start - 1:+.2%} since {st.get('started')}), cash ${st['cash']:,.2f}",
            f"- Holdings: {held}",
            f"- Last processed close: {st.get('last_processed')}; "
            f"next decision day: {nxt.date() if nxt is not None else 'n/a'}",
            "- Pending orders: "
            + (
                ", ".join(f"{k} {v:.0%}" for k, v in st["pending"]["targets"].items())
                + f" (decided {st['pending']['decided']})"
                if st.get("pending")
                else "none"
            ),
            f"- Orders so far: {len(st['trades'])}; fees ${st.get('fees', 0):,.2f}",
            "",
        ]
    return (
        "\n".join(lines)
        + "\nDecisions use completed daily prices and fill at the next official open, exactly as backtested.\n"
    )


def weekly_md(traders, daily, rf) -> str:
    end = max(pd.Timestamp(tr.book.state["last_processed"]) for tr in traders)
    lines = [f"# Weekly paper-trading report, week ending {end.date()} (simulated money)", ""]
    for tr in traders:
        st = tr.book.state
        hist = pd.Series(
            {pd.Timestamp(h["time"]): h["equity"] for h in st["history"] if len(h["time"]) == 10}
        ).sort_index()
        if hist.empty:
            continue
        start_day = pd.Timestamp(st["started"])
        spy = daily["SPY"]["Close"].loc[start_day:]
        cap = float(CFG["paper"]["starting_cash"])
        spy_val = cap * spy / spy.iloc[0]
        dd = (hist / hist.cummax() - 1).min()
        week = hist.loc[end - pd.Timedelta(days=6) :]
        wk_ret = (
            week.iloc[-1] / hist.loc[: end - pd.Timedelta(days=7)].iloc[-1] - 1
            if len(hist.loc[: end - pd.Timedelta(days=7)])
            else np.nan
        )
        bt = E.run_spec(tr.spec, {t: p.loc[start_day:] for t, p in daily.items()}, rf, capital=cap)
        bt_val = float(bt.equity.iloc[-1])
        trades = [x for x in st["trades"] if str(x["time"])[:10] >= str((end - pd.Timedelta(days=6)).date())]
        lines += [
            f"## {tr.spec['name']} ({'MAIN' if tr.role == 'main' else 'SHADOW, evidence only'})",
            "",
            "| | Value | Since start |",
            "|---|---|---|",
            f"| Paper account | ${hist.iloc[-1]:,.2f} | {hist.iloc[-1] / cap - 1:+.2%} |",
            f"| SPY bought and held from the same day | ${float(spy_val.iloc[-1]):,.2f} | "
            f"{float(spy_val.iloc[-1]) / cap - 1:+.2%} |",
            f"| The backtest of the same strategy over the same days | ${bt_val:,.2f} | {bt_val / cap - 1:+.2%} |",
            "",
            f"This week: {wk_ret:+.2%}." if np.isfinite(wk_ret) else "This week: first week.",
            f" Worst fall since start: {dd:.1%}. Paper vs backtest difference: ${hist.iloc[-1] - bt_val:+,.2f} "
            "(expected to be small: the paper account earns no interest on cash and skips orders under $25).",
            "",
            "Orders this week: "
            + (
                "; ".join(
                    f"{x['time'][:10]} {x['side']} {x['ticker']} {x['qty']:.4f} @ {x['price']:.2f}" for x in trades
                )
                or "none"
            ),
            "",
        ]
    lines.append(
        "Paper trading uses simulated money. Weeks are noisy: judge the strategies over months "
        "(research/paper-trading-plan.md)."
    )
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weekly", action="store_true", help="also write the weekly report")
    args = ap.parse_args()
    PAPER_DIR.mkdir(parents=True, exist_ok=True)
    fts = FT.latest_results()
    traders, notes = [], []
    for item in SPP.configured():
        el = gates.eligibility(item["spec"], item["role"], fts)
        if not el["eligible"]:
            notes.append(
                f"- {item['spec']['id']} NOT traded: " + "; ".join(g["detail"] for g in el["gates"] if not g["passed"])
            )
            continue
        traders.append(SPP.SpecPaperTrader(item["spec"], item["role"], item["ledger"]))
    tickers = sorted({a for tr in traders for a in SP.assets_needed(tr.spec)} | {"SPY"})
    daily = {t: data.completed_bars(data.daily_prices(t, use_cache=False)) for t in tickers}
    log = []
    for tr in traders:
        log += process(tr, daily)
    journal(notes + log)
    (PAPER_DIR / "status.md").write_text(status_md(traders, daily))
    if args.weekly and traders:
        idx = daily["SPY"].index
        rf = data.cash_rate(idx, CFG)
        end = max(pd.Timestamp(tr.book.state["last_processed"]) for tr in traders)
        (PAPER_DIR / f"weekly-{end.date()}.md").write_text(weekly_md(traders, daily, rf))
    print("\n".join(notes + log) or "No new completed trading day.")
    print((PAPER_DIR / "status.md").read_text())


if __name__ == "__main__":
    main()
