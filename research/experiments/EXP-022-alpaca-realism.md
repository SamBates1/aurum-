# EXP-022: Trading the way Alpaca will

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, before any lab result on real data |
| Origin | Stage B: paper trading should match the backtest |

## Facts checked (Alpaca docs, 2026-10-29 [S25])
Fractional and notional orders: market, limit, stop orders with time-in-force **day** only; from about $1; available
in paper accounts. Opening/closing auction orders (OPG/CLS) are not listed for fractional quantities, so a strategy
that wants auction fills must trade whole shares, or trade fractions with a day market order just after the open
(fill close to, but not exactly, the open: covered by the 2× cost test).

## Variants (practical choices, not signals: not counted as trials)
- `weekly`: orders only every 5th trading day (same 5-point band) — fewer orders to place and check.
- `whole_shares_10k`, `whole_shares_100k`: positions in whole shares only, for a $10,000 and a $100,000 account
  (Alpaca's paper default). Prices are adjusted closes, so share counts are approximate.

## Decision rules (fixed before running)
- **Weekly** replaces daily checking if development ΔSharpe ≥ −0.05 and pre-2013 ΔSharpe ≥ −0.05 and turnover is lower.
- **Whole shares**: if ΔSharpe vs fractional is within ±0.03 in every period, the Alpaca connection uses whole-share
  auction orders (cleaner fills); otherwise fractional day orders.

Lab rules (README, 'Research lab'); run with `python run_lab.py --set core` (and `--fill close`, `--set other`).

## Results
_Not yet run on real data._
