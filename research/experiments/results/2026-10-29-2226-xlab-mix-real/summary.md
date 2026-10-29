# EXP-045: S&P 500 + gold robustness and downturn protection (real, next-open fills)

Historical simulation, net of costs, 2006-06-30 → 2026-10-29.

## Scorecard

| Strategy | pre: CAGR / Sharpe / max DD | dev: CAGR / Sharpe / max DD | holdout: CAGR / Sharpe / max DD | Exposure | Costs/yr | Beta vs SPY | Longest drawdown |
|---|---|---|---|---|---|---|---|
| SPY buy & hold | +6.5% / +0.34 / -55.2% | +12.4% / +0.69 / -33.7% | +20.2% / +1.00 / -18.8% | 100% | 0.00% | +1.00 | 1223 days |
| SPY/GLD 90/10 monthly | +7.2% / +0.38 / -49.9% | +11.7% / +0.71 / -30.9% | +21.0% / +1.10 / -16.8% | 100% | 0.00% | +0.90 | 843 days |
| SPY/GLD 80/20 monthly | +7.9% / +0.43 / -44.3% | +11.1% / +0.72 / -28.0% | +21.8% / +1.18 / -14.9% | 100% | 0.01% | +0.80 | 758 days |
| SPY/GLD 70/30 monthly | +8.5% / +0.49 / -38.5% | +10.3% / +0.73 / -25.1% | +22.5% / +1.24 / -12.9% | 100% | 0.01% | +0.71 | 612 days |
| SPY/GLD 60/40 monthly | +9.0% / +0.53 / -35.7% | +9.6% / +0.73 / -22.6% | +23.2% / +1.26 / -12.0% | 100% | 0.01% | +0.61 | 383 days |
| SPY/GLD 50/50 monthly | +9.4% / +0.57 / -33.0% | +8.7% / +0.69 / -20.4% | +23.8% / +1.24 / -13.3% | 100% | 0.01% | +0.52 | 428 days |
| SPY/GLD 70/30 quarterly | +8.3% / +0.48 / -38.9% | +10.3% / +0.73 / -24.8% | +22.7% / +1.25 / -12.7% | 100% | 0.00% | +0.70 | 731 days |
| SPY/GLD 70/30 yearly | +7.5% / +0.45 / -37.9% | +10.2% / +0.73 / -24.8% | +22.8% / +1.27 / -12.4% | 97% | 0.00% | +0.68 | 611 days |
| SPY/GLD 70/30 5-pt band | +8.6% / +0.49 / -38.0% | +10.3% / +0.73 / -25.1% | +22.9% / +1.27 / -12.6% | 100% | 0.00% | +0.71 | 608 days |
| SPY/GLD/IEF 60/25/15 monthly | +8.4% / +0.55 / -32.7% | +9.1% / +0.74 / -20.9% | +19.2% / +1.19 / -10.8% | 100% | 0.01% | +0.59 | 485 days |
| 70/30 + risk cap (20% vol) | +9.1% / +0.65 / -25.8% | +9.7% / +0.80 / -17.9% | +21.1% / +1.27 / -12.0% | 94% | 0.02% | +0.51 | 510 days |
| 70/30 + SPY 200-day trend filter | +7.8% / +0.62 / -15.8% | +7.5% / +0.70 / -15.6% | +20.5% / +1.28 / -9.8% | 86% | 0.07% | +0.27 | 424 days |
| SPY 70% + Aurum 30% monthly | +5.7% / +0.34 / -41.8% | +10.0% / +0.70 / -25.7% | +21.4% / +1.27 / -13.5% | 100% | 0.00% | +0.73 | 790 days |

## Versus SPY (whole period)

| Strategy | ΔCAGR | ΔSharpe | resamples with higher Sharpe |
|---|---|---|---|
| SPY buy & hold | +0.0% | +0.00 | 0% |
| SPY/GLD 90/10 monthly | +0.1% | +0.04 | 98% |
| SPY/GLD 80/20 monthly | +0.1% | +0.08 | 96% |
| SPY/GLD 70/30 monthly | -0.0% | +0.12 | 93% |
| SPY/GLD 60/40 monthly | -0.1% | +0.14 | 89% |
| SPY/GLD 50/50 monthly | -0.3% | +0.15 | 83% |
| SPY/GLD 70/30 quarterly | -0.0% | +0.12 | 93% |
| SPY/GLD 70/30 yearly | -0.4% | +0.11 | 91% |
| SPY/GLD 70/30 5-pt band | +0.1% | +0.12 | 94% |
| SPY/GLD/IEF 60/25/15 monthly | -1.1% | +0.15 | 96% |
| 70/30 + risk cap (20% vol) | -0.3% | +0.24 | 98% |
| 70/30 + SPY 200-day trend filter | -2.0% | +0.19 | 85% |
| SPY 70% + Aurum 30% monthly | -1.4% | +0.05 | 80% |

## Downturns (return over the window)

| Strategy | 2008-09 recession | 2020 Covid recession | 2022 rate rises |
|---|---|---|---|
| SPY buy & hold | -35.1% | -9.9% | -18.2% |
| SPY/GLD 70/30 monthly | -20.3% | -4.3% | -15.4% |
| SPY/GLD 60/40 monthly | -15.2% | -2.6% | -14.5% |
| 70/30 + risk cap (20% vol) | -13.8% | -6.2% | -14.2% |
| 70/30 + SPY 200-day trend filter | +0.7% | -8.7% | -9.0% |
| SPY 70% + Aurum 30% monthly | -23.8% | -6.2% | -14.7% |

## Pre-registered tests

1a. Every mix 80/20–60/40 beats SPY's Sharpe overall and in ≥ 2 of 3 periods: **PASS**
1b. 70/30 beats SPY's Sharpe with quarterly and yearly rebalancing: **PASS**
2. 70/30 CAGR within 1 point of SPY's: **PASS**
3. 70/30 + risk cap (20% vol): loses less than 70/30 in every downturn: no; costs +0.3% a year vs 70/30: **FAIL**
3. 70/30 + SPY 200-day trend filter: loses less than 70/30 in every downturn: no; costs +2.0% a year vs 70/30: **FAIL**

## Figures

- [Equity curves and drawdowns](figures/equity_drawdown.png)
- [Calendar-year returns](figures/annual_returns.png)
- [Rolling return, volatility, Sharpe and correlation](figures/rolling.png)
- [Rolling 3-year annualised return](figures/rolling_3y.png)
- [Sharpe ratio of each mix by period (SPY alone: see table)](figures/mix_sharpe_grid.png)
- [Return during each downturn window](figures/downturns.png)
- [Tail-loss comparison](figures/tail_risk.png)
