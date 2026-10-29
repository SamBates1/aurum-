# Fair Test: Example (rejected in EXP-045): 70/30 + SPY 200-day trend filter (v1, hash `bac378fceb35`)

**Verdict: FAILED**. Worse than the benchmark in development: lower Sharpe ratio and no meaningful reduction in falls.

Historical backtest, net of costs; not paper or live trading. Data: Yahoo Finance adjusted daily data (EOD), completed bars to 2026-10-29; historical backtest, net of costs. Code 7c05f7408c3d, commit f6555f3, run 2026-10-29T23:32:42+00:00.

## Checks
| Check | Result | Detail |
|---|---|---|
| Valid definition | pass | example-70-30-spy-trend-filter v1, hash bac378fceb35 |
| Enough clean data | pass | 20.4 years of common daily data (2006-06-01 to 2026-10-29); longest gap 5.0 days |
| No look-ahead | pass | targets identical when data after 3 cut dates were removed |
| Accounting | pass | no borrowing, no negative cash, costs charged on every order |
| Execution: next-close fills and 1 day late | pass | development Sharpe 0.70; next-close fills 0.67; one day late 0.61 |
| Not fragile (+-20% on every number) | pass | 6 nudged versions: development Sharpe from 0.58 to 0.71 (as defined 0.70) |
| Deflated Sharpe ratio | FAIL | DSR 0.37 allowing for 100 versions tried (needs >= 0.50) |

## Against the benchmark (A: 70/30 SPY/GLD, monthly rebalance)
| Period | Dates | Sharpe | Benchmark | dSharpe | Resamples better | CAGR | Benchmark CAGR | Worst fall | Benchmark worst fall | Drawdown/vol improvement |
|---|---|---|---|---|---|---|---|---|---|---|
| pre | 2006-06-01 to 2013-10-17 | 0.59 | 0.47 | +0.13 | 62.0% | 7.6% | 8.2% | -15.8% | -38.5% | +37.0% |
| dev | 2013-10-18 to 2023-12-31 | 0.70 | 0.73 | -0.03 | 37.7% | 7.5% | 10.3% | -15.6% | -25.1% | +12.4% |
| holdout | 2024-01-01 to latest | 1.28 | 1.24 | +0.04 | 55.6% | 20.5% | 22.5% | -9.8% | -12.9% | +11.8% |
| full | start to end | 0.74 | 0.68 | +0.07 | 64.9% | 9.2% | 11.1% | -15.8% | -38.5% | +41.4% |

Development period at 2x costs: dSharpe -0.04. DSR 0.37 for 100 versions tried. PBO across the nudged versions: 88.0% (information only, not part of the verdict: it measures whether picking the best nudged version would have helped, which says little when the versions are nearly identical).

## Sensitivity (development Sharpe)
| Change | Sharpe |
|---|---|
| SPY weight -10% | 0.67 |
| SPY weight +10% | 0.69 |
| band x0.5 | 0.70 |
| band x1.5 | 0.71 |
| spy_trend sma n x0.8 | 0.58 |
| spy_trend sma n x1.2 | 0.62 |

## Rules used (pre-registered, same as run_lab.lab_verdict)
Signal path: dSharpe >= 0.10 with >= 80% of bootstrap resamples better and >= 0 at 2x costs. Risk path: drawdown per unit of volatility >= 20% smaller with dSharpe >= -0.05 (also at 2x costs). Then DSR >= 0.50, then the improvement must hold on both the 2024+ holdout and pre-2013. A pass does not start paper trading: the owner must approve it.
