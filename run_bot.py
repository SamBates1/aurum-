"""Headless bot: re-evaluates the universe every `live.refresh_seconds`, prints
signals and, with --paper, executes them in the local paper portfolio.

    python run_bot.py              # signals only
    python run_bot.py --paper      # signals + paper trades (simulated money only)
    python run_bot.py --once       # one pass, then exit

Freshness: the slow research step (walk-forward model) reruns once per day.
Every loop re-downloads prices and rebuilds features from the latest completed
bars before deciding, so decisions never use stale features. If the latest bar
is too old, the ticker is marked untradeable and no paper trade is made.
"""

from __future__ import annotations

import argparse
import time
from datetime import date, datetime

from aurum import data
from aurum.config import CFG, all_tickers
from aurum.paper import PaperPortfolio
from aurum.pipeline import decide, research


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", action="store_true", help="execute signals in the paper portfolio")
    ap.add_argument("--once", action="store_true", help="run one pass and exit")
    args = ap.parse_args()

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
                trade = book.apply(t, d.decision, d.last_price, d.ann_vol, d.atr, prices, d.tradeable)
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
