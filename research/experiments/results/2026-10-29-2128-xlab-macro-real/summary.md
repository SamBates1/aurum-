# EXP-043: macro and cross-asset lead-lag (real)

32 predictive tests in the development period (4 assets × 8 drivers); next-21-day return regressed on today's standardised driver plus the asset's own past 21-day return, Newey-West (21 lags).

- Raw p < 5%: 11 (about 1.6 expected by chance).
- Discoveries at 10% false-discovery rate: 9; confirmed before 2013 and after 2024: 0.

| Asset | Driver | Predictive effect per 1 sd (dev) | t | Contemporaneous corr. (dev) |
|---|---|---|---|---|
| GLD | credit (HYG/IEF) 21d % chg | -0.77% | -3.3 | -0.09 |
| SPY | VIX level | +0.98% | 3.2 | -0.47 |
| GDX | VIX level | +2.85% | 3.1 | +0.01 |
| SLV | VIX level | +1.73% | 2.8 | -0.04 |
| GDX | SPY 21d return | -2.42% | -2.5 | +0.28 |
| SLV | dollar 21d % chg | -1.02% | -2.4 | -0.46 |
| GLD | VIX level | +0.65% | 2.4 | +0.09 |
| GLD | SPY 21d return | -0.64% | -2.3 | +0.11 |
| GDX | credit (HYG/IEF) 21d % chg | -2.27% | -2.2 | +0.10 |
| GLD | breakeven 21d chg | -0.59% | -2.1 | +0.07 |
| SPY | SPY 21d return | -0.74% | -2.1 | +1.00 |
| GLD | dollar 21d % chg | -0.45% | -1.9 | -0.49 |

Contemporaneous correlation (moving together) is not prediction: only the predictive column could be traded.

## Figures

- [Gold vs the US dollar](figures/gold_vs_dollar.png)
- [Gold vs 10-year real yield (the link weakened after 2021)](figures/gold_vs_real_yield.png)
- [Gold, silver, miners, copper and the S&P 500 (growth of 1)](figures/cross_asset_levels.png)
- [Rolling 3-year correlation: GLD 21-day return vs each driver (contemporaneous)](figures/rolling_corr_gld.png)
- [Lead-lag: correlation of GLD's next-N-day return with each driver today](figures/lead_lag_gld.png)
- [Correlation of daily returns](figures/correlation.png)
- [Drawdowns of each asset](figures/asset_drawdowns.png)
- [Return distributions (daily and monthly)](figures/asset_return_distribution.png)
- [Predictive t-statistics (Newey-West), next-21-day return on each driver, controlling for the asset's own 21-day return (dev)](figures/predictive_t_dev.png)
