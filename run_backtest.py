"""Quick backtest of the traded strategy for each ticker (no benchmarks or diagnostics).
For the full study with benchmarks, holdout and robustness checks, use run_research.py.

    python run_backtest.py            # all tickers
    python run_backtest.py GLD NEM    # chosen tickers
"""

from __future__ import annotations

import sys

import pandas as pd

from aurum import data
from aurum.config import CFG, all_tickers
from aurum.pipeline import research, summary


def main(tickers):
    macro = data.macro_daily()
    rows = []
    for t in tickers:
        print(f"Backtesting {t} ...", flush=True)
        rows.append(summary(research(t, macro)))
    df = pd.DataFrame(rows).set_index("ticker")
    cols = ["start", "cagr", "sharpe", "sortino", "max_drawdown", "trades", "time_in_market", "auc", "base_rate"]
    print(df[cols].to_string(float_format=lambda x: f"{x:.3f}"))
    print(f"\nOut-of-sample walk-forward, next-open fills, costs per ticker: {CFG['costs']['per_ticker']} bps.")
    if CFG.get("offline"):
        print("SYNTHETIC DATA: these numbers do not describe real markets.")


if __name__ == "__main__":
    main(sys.argv[1:] or all_tickers())
