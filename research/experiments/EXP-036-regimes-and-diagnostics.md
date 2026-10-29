# EXP-036: Regimes, consistency, tails and what normal looks like

| Field | |
|---|---|
| Status | Run 2026-10-29: diagnostics produced; normal ranges set for paper trading |
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

## Results (real data, 2026-10-29; `results/2026-10-29-1440-plab-core-real/` (open fills), `…-1441-plab-core-real-closefill/`, `…-1442-plab-other-real/`; charts `equity_drawdown.png`, `monthly_returns.png` in each folder)
**By market regime** (traded rule, core, annualised mean return / volatility): gold bull markets +22.2% / 12%
(buy & hold +49.6% / 32%); bear markets −17.8% / 12% (buy & hold −38.0% / 39%); sideways −4.8% / 11% (−8.6% / 28%).
Low gold implied volatility +4.3%, medium +9.6%, high +2.2% a year. Thin-volume days behave like normal days.
The strategy makes its money in gold bull markets and loses in bear and sideways markets, about half as much as
holding.

**Consistency and tails (whole period):** 58% of months positive; monthly profit factor 1.42 (buy & hold 1.38);
average up month +2.9%, average down month −2.9%; worst month −8.3% (buy & hold −34.9%); worst day −4.7% (−15.3%);
average of the worst 5% of days −1.7% (−4.7%). **Longest time below a previous peak: 2,239 trading days (about 9 years,
from the 2011 gold peak)**, about the same as buy & hold: smaller falls do not mean faster recovery.

**What normal looks like** (every rolling window, traded rule, 2006–2026):

| Window | 5th pct | 25th | median | 75th | 95th | Share of windows with a loss |
|---|---|---|---|---|---|---|
| 1 month | −5.1% | −2.0% | +0.5% | +3.0% | +6.0% | 44% |
| 3 months | −8.7% | −2.4% | +1.6% | +5.7% | +11.7% | 39% |
| 6 months | −10.7% | −3.1% | +2.9% | +9.0% | +19.0% | 37% |
| 1 year | −13.2% | −4.0% | +4.5% | +16.9% | +30.0% | 38% |

So a 3-month paper-trading loss happens in about 4 windows out of 10 and says almost nothing on its own.
