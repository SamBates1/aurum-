"""Headless bot: re-evaluates the universe every `live.refresh_seconds`, prints
signals and, with --paper, executes them in the local paper portfolio.

    python run_bot.py              # signals only
    python run_bot.py --paper      # signals + paper trades (simulated money only)
    python run_bot.py --once       # one pass, then exit

With paper.engine: spec in config.yaml (the default since D-034) the bot paper-trades the approved strategy
definitions listed under paper.strategies (70/30 SPY/GLD main + risk-capped shadow), using the same engine as the
backtest and the Strategy Designer; no ML step is needed. With paper.engine: legacy it runs the gold vol_hold bot.

Freshness: the slow research step (walk-forward model) reruns once per day.
Every loop re-downloads prices and rebuilds features from the latest completed
bars before deciding, so decisions never use stale features. If the latest bar
is too old, the ticker is marked untradeable and no paper trade is made.
"""

from __future__ import annotations

import argparse
import time
from datetime import date, datetime

from aurum import data, gates
from aurum import fairtest as FT
from aurum import spec_paper as SPP
from aurum.config import CFG, all_tickers
from aurum.paper import PaperPortfolio
from aurum.pipeline import decide, research


def spec_loop(args):
    """Paper-trade the approved strategy definitions (simulated money only)."""
    traders = []
    for item in SPP.configured():
        el = gates.eligibility(item["spec"], item["role"], FT.latest_results())
        if not el["eligible"]:
            why = "; ".join(f"{g['gate']}: {g['detail']}" for g in el["gates"] if not g["passed"])
            print(f"NOT TRADED {item['spec']['id']} ({item['role']}): {why}")
            data.log_event("warning", item["spec"]["id"], f"not eligible for paper trading: {why}")
            continue
        traders.append(SPP.SpecPaperTrader(item["spec"], item["role"], item["ledger"], min_order=item.get("min_order")))
        print(f"Paper-trading {item['spec']['name']} as {item['role']} (hash {traders[-1].hash})")
    if not traders:
        print("No eligible strategy: nothing to do.")
        return
    while True:
        print(f"\n=== {datetime.now():%Y-%m-%d %H:%M:%S} ===")
        tickers = sorted(
            {t for tr in traders for t in tr.spec["universe"]}
            | {a for tr in traders for a in SPP.SP.assets_needed(tr.spec)}
        )
        daily, live, ages = {}, {}, []
        for t in tickers:
            try:
                bars = data.completed_bars(data.daily_prices(t, use_cache=False))
                daily[t] = bars
                ages.append(data.staleness_days(bars))
                intra = data.intraday_prices(t)
                live[t] = float(intra["Close"].iloc[-1]) if len(intra) else float(bars["Close"].iloc[-1])
            except Exception as exc:
                data.log_event("error", t, f"no prices this loop: {exc}")
        age = max(ages) if ages else 99
        for tr in traders:
            if any(t not in daily for t in SPP.SP.assets_needed(tr.spec)):
                print(f"{tr.spec['id']}: missing prices, no decision")
                continue
            if args.paper:
                for msg in tr.execute(live, {t: daily[t]["Close"] for t in tr.spec["universe"]}, age):
                    print(f"  [{tr.role}] {msg}")
            pend = tr.decide(daily)
            if pend:
                print(
                    f"  [{tr.role}] decided on {pend['decided']}: targets "
                    + ", ".join(f"{k} {v:.0%}" for k, v in pend["targets"].items())
                    + " (orders after the next open)"
                )
            w, eq = tr.weights(live)
            print(
                f"  [{tr.role}] {tr.spec['id']}: equity ${eq:,.2f}, holdings "
                + ", ".join(f"{k} {v:.0%}" for k, v in w.items())
                + f", data age {age} days"
            )
            if args.paper:
                tr.save(live)
        if args.once:
            break
        time.sleep(CFG["live"]["refresh_seconds"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", action="store_true", help="execute signals in the paper portfolio")
    ap.add_argument("--once", action="store_true", help="run one pass and exit")
    ap.add_argument("--engine", choices=["spec", "legacy"], help="override paper.engine from config.yaml")
    args = ap.parse_args()
    if (args.engine or CFG["paper"].get("engine", "legacy")) == "spec":
        return spec_loop(args)

    cache, cache_day = {}, None
    book = PaperPortfolio() if args.paper else None
    while True:
        if cache_day != date.today():
            print("Running daily research (walk-forward ML)...", flush=True)
            macro = data.macro_daily()
            cache = {}
            for t in all_tickers():
                try:
                    cache[t] = research(t, macro)
                except Exception as exc:
                    data.log_event("error", t, f"research failed, ticker skipped today: {exc}")
            cache_day = date.today()

        print(f"\n=== {datetime.now():%Y-%m-%d %H:%M:%S} ===")
        decisions = {}
        for t, res in cache.items():
            try:
                fresh = data.daily_prices(t, use_cache=False)  # re-download every loop
                decisions[t] = decide(t, res, prices=fresh)
            except Exception as exc:
                data.log_event("error", t, f"no decision this loop: {exc}")
        prices = {t: d.last_price for t, d in decisions.items()}
        for t, d in decisions.items():
            flag = "" if d.tradeable else "  [NOT TRADEABLE]"
            print(
                f"{t:5} {d.decision:4}  score {d.score:+.2f}  P(up) {d.prob_up:.0%}  "
                f"price {d.last_price:.2f}  as of {d.as_of}{flag}"
            )
            for n in d.notes:
                print(f"      note: {n}")
            if book:
                trade = book.act(d, prices)
                if trade:
                    print(f"      paper trade: {trade}")
        if book:
            book.mark(prices)
            book.save()
            print(
                f"Paper equity: {book.equity(prices):,.2f}  cash: {book.state['cash']:,.2f}  "
                f"fees: {book.state['fees']:,.2f}  realised P&L: {book.state['realised_pnl']:+,.2f}"
            )
        if args.once:
            break
        time.sleep(CFG["live"]["refresh_seconds"])


if __name__ == "__main__":
    main()
