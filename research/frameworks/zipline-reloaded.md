# Zipline-reloaded

| | |
|---|---|
| Repository | https://github.com/stefan-jansen/zipline-reloaded |
| Version inspected | commit `f131a72` (2026-10-25) |
| Licence | Apache-2.0 |
| Type | Event-driven daily/minute equity backtester (originally Quantopian's), with a point-in-time "Pipeline" for cross-sectional factors |
| Inspected by | Claude, 2026-10-27, by reading source |

## How it works (traced in source)

**Point-in-time pipeline.** `src/zipline/pipeline/loaders/equity_pricing_loader.py` shifts pricing data by one
session (`shift_dates(..., shift=1)`), with the comment that data known on day N is the data from day N−1.
Pipeline outputs used on day N therefore only contain information available before that day's trading.
Aurum's equivalent: features from the close of t, orders at the open of t+1, FRED lagged by publication
delay (`data.publication_lag`).

**Warm-up rows.** The pipeline engine computes `extra_rows` for each term so moving windows are fully
populated before the first output date (`pipeline/engine.py`), the same concern as Freqtrade's recursive
analysis.

**Slippage model.** `src/zipline/finance/slippage.py`:
- `VolumeShareSlippage` (default for equities): fills at most `volume_limit` = 2.5% of the bar's volume
  (`DEFAULT_EQUITY_VOLUME_SLIPPAGE_BAR_LIMIT`), and the price moves by
  `volume_share² × price_impact × price` with `price_impact = 0.1`. Unfilled remainder carries to later bars.
- `FixedBasisPointsSlippage`: price moved by a fixed number of basis points, with a volume cap.
- Orders placed during a bar fill on the next bar at its close (plus impact).

**Commissions.** `finance/commission.py`: `PerShare`, `PerTrade`, `PerDollar` models, minimums per trade.

**Survivorship and corporate actions.** Assets live in an asset database with start/end dates, and price
adjustments (splits, dividends) are applied as of each simulation date, so delisted securities can be part of
a historical universe if the data bundle includes them.

**Testing.** 86 test files.

## Lessons for Aurum
| Idea | Status |
|---|---|
| One-session shift for "known" data | Already in Aurum (next-open fills, FRED lag) |
| Quadratic volume-share impact | Not needed now: position sizes are tiny vs volume; revisit for larger capital |
| Asset DB with listing dates (survivorship) | Deferred: needs a historical miner universe incl. delisted names (paid data) |
| Adopting Zipline | Rejected (D-013): bundle ingestion and calendar setup are heavy for 6 tickers |
