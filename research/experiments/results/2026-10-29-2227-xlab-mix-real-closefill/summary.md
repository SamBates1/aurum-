# EXP-045: S&P 500 + gold robustness and downturn protection (real, next-close fills)

Historical simulation, net of costs, 2006-06-30 → 2026-10-29.

## Scorecard

| Strategy | pre: CAGR / Sharpe / max DD | dev: CAGR / Sharpe / max DD | holdout: CAGR / Sharpe / max DD | Exposure | Costs/yr | Beta vs SPY | Longest drawdown |
|---|---|---|---|---|---|---|---|
| SPY buy & hold | +6.4% / +0.34 / -55.2% | +12.4% / +0.69 / -33.7% | +20.2% / +1.00 / -18.8% | 100% | 0.00% | +1.00 | 1223 days |
| SPY/GLD 90/10 monthly | +7.2% / +0.38 / -49.9% | +11.7% / +0.71 / -30.9% | +21.0% / +1.10 / -16.8% | 100% | 0.00% | +0.90 | 843 days |
| SPY/GLD 80/20 monthly | +7.9% / +0.43 / -44.4% | +11.0% / +0.72 / -28.1% | +21.8% / +1.19 / -14.9% | 100% | 0.01% | +0.80 | 758 days |
| SPY/GLD 70/30 monthly | +8.4% / +0.48 / -38.6% | +10.3% / +0.73 / -25.2% | +22.5% / +1.24 / -12.9% | 100% | 0.01% | +0.71 | 612 days |
| SPY/GLD 60/40 monthly | +9.0% / +0.53 / -35.7% | +9.5% / +0.72 / -22.7% | +23.2% / +1.26 / -12.1% | 100% | 0.01% | +0.61 | 383 days |
| SPY/GLD 50/50 monthly | +9.4% / +0.57 / -33.2% | +8.7% / +0.69 / -20.5% | +23.8% / +1.24 / -13.3% | 100% | 0.01% | +0.52 | 428 days |
| SPY/GLD 70/30 quarterly | +8.3% / +0.48 / -38.9% | +10.3% / +0.73 / -24.7% | +22.7% / +1.25 / -12.7% | 100% | 0.00% | +0.70 | 729 days |
| SPY/GLD 70/30 yearly | +7.6% / +0.45 / -37.9% | +10.2% / +0.73 / -24.7% | +22.9% / +1.27 / -12.3% | 97% | 0.00% | +0.68 | 611 days |
| SPY/GLD 70/30 5-pt band | +8.3% / +0.47 / -38.8% | +10.3% / +0.73 / -25.4% | +23.5% / +1.31 / -12.6% | 100% | 0.00% | +0.72 | 615 days |
| SPY/GLD/IEF 60/25/15 monthly | +8.4% / +0.55 / -32.7% | +9.1% / +0.73 / -21.0% | +19.2% / +1.19 / -10.8% | 100% | 0.01% | +0.59 | 485 days |
| 70/30 + risk cap (20% vol) | +9.4% / +0.67 / -25.0% | +9.6% / +0.78 / -18.1% | +20.9% / +1.26 / -12.1% | 93% | 0.02% | +0.52 | 505 days |
| 70/30 + SPY 200-day trend filter | +8.2% / +0.65 / -13.7% | +7.2% / +0.67 / -15.3% | +19.7% / +1.23 / -10.0% | 86% | 0.07% | +0.27 | 517 days |
| SPY 70% + Aurum 30% monthly | +5.6% / +0.34 / -41.8% | +10.0% / +0.70 / -25.8% | +21.4% / +1.27 / -13.4% | 100% | 0.00% | +0.73 | 790 days |

## Versus SPY (whole period)

| Strategy | ΔCAGR | ΔSharpe | resamples with higher Sharpe |
|---|---|---|---|
| SPY buy & hold | +0.0% | +0.00 | 0% |
| SPY/GLD 90/10 monthly | +0.1% | +0.04 | 98% |
| SPY/GLD 80/20 monthly | +0.0% | +0.08 | 96% |
| SPY/GLD 70/30 monthly | -0.0% | +0.12 | 93% |
| SPY/GLD 60/40 monthly | -0.1% | +0.14 | 88% |
| SPY/GLD 50/50 monthly | -0.3% | +0.15 | 83% |
| SPY/GLD 70/30 quarterly | -0.0% | +0.12 | 93% |
| SPY/GLD 70/30 yearly | -0.3% | +0.11 | 91% |
| SPY/GLD 70/30 5-pt band | +0.1% | +0.12 | 94% |
| SPY/GLD/IEF 60/25/15 monthly | -1.1% | +0.15 | 96% |
| 70/30 + risk cap (20% vol) | -0.3% | +0.24 | 98% |
| 70/30 + SPY 200-day trend filter | -2.1% | +0.18 | 84% |
| SPY 70% + Aurum 30% monthly | -1.3% | +0.04 | 80% |

## Downturns (return over the window)

| Strategy | 2008-09 recession | 2020 Covid recession | 2022 rate rises |
|---|---|---|---|
| SPY buy & hold | -35.1% | -9.9% | -18.2% |
| SPY/GLD 70/30 monthly | -20.5% | -4.5% | -15.5% |
| SPY/GLD 60/40 monthly | -15.4% | -2.8% | -14.6% |
| 70/30 + risk cap (20% vol) | -12.8% | -6.9% | -14.6% |
| 70/30 + SPY 200-day trend filter | -1.0% | -2.1% | -12.1% |
| SPY 70% + Aurum 30% monthly | -23.8% | -6.4% | -14.8% |

## Pre-registered tests

1a. Every mix 80/20–60/40 beats SPY's Sharpe overall and in ≥ 2 of 3 periods: **PASS**
1b. 70/30 beats SPY's Sharpe with quarterly and yearly rebalancing: **PASS**
2. 70/30 CAGR within 1 point of SPY's: **PASS**
3. 70/30 + risk cap (20% vol): loses less than 70/30 in every downturn: no; costs +0.2% a year vs 70/30: **FAIL**
3. 70/30 + SPY 200-day trend filter: loses less than 70/30 in every downturn: yes; costs +2.0% a year vs 70/30: **FAIL**

## Figures

- [Equity curves and drawdowns](figures/equity_drawdown.png)
- [Calendar-year returns](figures/annual_returns.png)
- [Rolling return, volatility, Sharpe and correlation](figures/rolling.png)
- [Rolling 3-year annualised return](figures/rolling_3y.png)
- [Sharpe ratio of each mix by period (SPY alone: see table)](figures/mix_sharpe_grid.png)
- [Return during each downturn window](figures/downturns.png)
- [Tail-loss comparison](figures/tail_risk.png)
