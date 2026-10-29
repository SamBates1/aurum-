# EXP-022: Trading the way Alpaca will

| Field | |
|---|---|
| Status | Run 2026-10-29: **weekly orders adopted** (D-022); whole shares make no difference (D-023) |
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

## Results (real data, 2026-10-29; `results/2026-10-29-1337-lab-core-real/`, `…-1337-lab-core-real-closefill/`, `…-1332-lab-other-real/`)
ΔSharpe vs the daily-checked strategy, pre / dev / holdout:

| Variant | Core, open fills | Core, close fills | Other assets | Orders per asset per year |
|---|---|---|---|---|
| weekly (every 5th day) | +0.02 / +0.02 / −0.03 | +0.05 / +0.01 / −0.05 | +0.04 / +0.01 / +0.02 | 20 (daily: 39) |
| whole shares, $10k | +0.01 / 0.00 / 0.00 | +0.01 / 0.00 / 0.00 | −0.03 / −0.01 / +0.03 | – |
| whole shares, $100k | 0.00 / 0.00 / 0.00 | 0.00 / 0.00 / 0.00 | +0.01 / 0.00 / 0.00 | – |

**Weekly** met its rule (dev and pre ΔSharpe ≥ −0.05, half the orders) → adopted (D-022). Implemented as *decide after
Friday's close* (last trading day of the week), which is easier to follow live than "every 5th day". Confirmation runs
with the Friday rule as the baseline (`results/2026-10-29-1345-lab-core-real/`, `…-1346-…-closefill/`,
`…-1346-lab-other-real/`): Sharpe vs daily −0.03 / +0.01 / −0.02 (open fills) and +0.02 / +0.02 / +0.02 (close
fills): the same within noise, with 21 instead of 39 orders per asset per year.
**Whole shares** stayed within ±0.03 everywhere → the Alpaca connection may use whole-share opening-auction orders
(D-023).
