"""Walk-forward backtest of the ML strategy across the whole universe.

    python run_backtest.py            # all tickers
    python run_backtest.py GLD NEM    # chosen tickers
Writes results/backtest_summary.csv.
"""
import sys
from pathlib import Path

import pandas as pd

from aurum import data
from aurum.config import CFG, all_tickers
from aurum.pipeline import research


def main(tickers):
    macro = data.macro_daily()
    rows = []
    for t in tickers:
        print(f"Backtesting {t} ...", flush=True)
        r = research(t, macro)
        s = r["summary"]
        rows.append({"ticker": t, **{f"strat_{k}": v for k, v in s["Strategy"].items()},
                     **{f"hold_{k}": v for k, v in s["Buy & hold"].items()},
                     **{f"model_{k}": v for k, v in r["oos"].items()}})
    df = pd.DataFrame(rows).set_index("ticker")
    out = Path("results"); out.mkdir(exist_ok=True)
    df.to_csv(out / "backtest_summary.csv")
    cols = ["strat_CAGR", "hold_CAGR", "strat_Sharpe", "hold_Sharpe", "strat_Max drawdown", "hold_Max drawdown", "model_auc"]
    with pd.option_context("display.width", 140):
        print(df[cols].round(3))
    print(f"\nCosts: {CFG['backtest']['cost_bps']} bps per trade. Saved results/backtest_summary.csv")


if __name__ == "__main__":
    main(sys.argv[1:] or all_tickers())
