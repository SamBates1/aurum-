# EXP-036: Regimes, consistency, tails and what normal looks like

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, before any portfolio-lab result on real data |
| Origin | Owner's brief §2, §7, §11 |

## What is produced (descriptive)
- Returns and volatility in bull / bear / sideways gold markets (GLD vs its 200-day average and 6-month return,
  ±5%), in low / medium / high gold implied volatility (GVZ terciles), and on thin-volume days (median volume
  below 70% of its 1-year median): a proxy for low liquidity.
- Consistency and tails: share of positive months, monthly profit factor (sum of gains / sum of losses), average
  up and down month, worst month and day, 5% daily CVaR, longest time below a previous peak, share of time below a peak.
  (Win rate and profit factor per trade do not apply to an always-invested strategy, so monthly figures are used.)
- Equity and drawdown charts and the monthly return distribution.
- **What normal looks like**: the 1st–95th percentile of every 1-, 3-, 6- and 12-month return in the history, used
  to judge paper trading fairly (a 3-month loss is normal if it is inside this range).

Portfolio-lab rules (README, 'Portfolio lab'); run with `python run_plab.py --set core` (and `--fill close`, `--set other`).

## Results
_Not yet run on real data._
