"""Headless bot: re-analyses the universe every `live.refresh_seconds`, prints
signals and (optionally) paper-trades them.

    python run_bot.py              # signals only
    python run_bot.py --paper      # signals + paper trades
    python run_bot.py --once       # one pass then exit
The slow ML research step reruns once a day; prices, news and decisions refresh every loop.
"""
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
            cache = {t: research(t, macro) for t in all_tickers()}
            cache_day = date.today()
        else:  # refresh prices so today's partial bar updates
            for t in cache:
                cache[t]["prices"] = data.daily_prices(t)

        print(f"\n=== {datetime.now():%Y-%m-%d %H:%M:%S} ===")
        analyses = {t: decide(t, r) for t, r in cache.items()}
        prices = {t: a.last_price for t, a in analyses.items()}
        for t, a in analyses.items():
            s = a.signal
            print(f"{t:5} {s['decision']:4}  score {s['score']:+.2f}  P(up) {a.prob_up:.0%}  price {a.last_price:.2f}")
            if book:
                trade = book.apply(t, s["decision"], a.last_price, a.ann_vol, a.atr, prices)
                if trade:
                    print(f"      paper trade: {trade}")
        if book:
            book.mark(prices); book.save()
            print(f"Paper equity: {book.equity(prices):,.2f}  cash: {book.state['cash']:,.2f}")
        if args.once:
            break
        time.sleep(CFG["live"]["refresh_seconds"])


if __name__ == "__main__":
    main()
