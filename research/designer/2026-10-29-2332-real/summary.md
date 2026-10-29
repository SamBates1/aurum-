# Strategy Designer results (2026-10-29 23:32 UTC, real data)

Yahoo Finance adjusted daily data (EOD), completed bars to 2026-10-29; historical backtest, net of costs. Every number is a historical backtest net of costs (one account, next-open fills, T-bill on cash, no borrowing).
Code 7c05f7408c3d, commit f6555f3, config 4c1c01d63cc0.

## Reproduction check (designer engine vs the EXP-045 code path)
| Strategy | Max difference in account value | Result |
|---|---|---|
| spy-gld-70-30-monthly | 0.00e+00 | identical |
| spy-gld-70-30-risk-cap | 0.00e+00 | identical |
| example-70-30-spy-trend-filter | 0.00e+00 | identical |

## Results (full history and by period)
| Strategy | Period | Dates | CAGR | Sharpe | Worst fall | Volatility | Costs/yr | Orders/yr |
|---|---|---|---|---|---|---|---|---|
| Example (rejected in EXP-045): 70/30 + SPY 200-day trend filter | full | 2006-06-01 to 2026-10-29 | 9.2% | 0.74 | -15.8% | 10.3% | 0.07% | 6.6 |
| Example (rejected in EXP-045): 70/30 + SPY 200-day trend filter | pre | 2006-06-01 to 2013-10-17 | 7.6% | 0.59 | -15.8% | 11.3% | 0.09% | 7.6 |
| Example (rejected in EXP-045): 70/30 + SPY 200-day trend filter | dev | 2013-10-18 to 2023-12-29 | 7.5% | 0.70 | -15.6% | 9.1% | 0.08% | 6.8 |
| Example (rejected in EXP-045): 70/30 + SPY 200-day trend filter | holdout | 2024-01-02 to 2026-10-29 | 20.5% | 1.28 | -9.8% | 11.7% | 0.03% | 3.2 |
| Benchmark: SPY buy and hold | full | 2006-06-01 to 2026-10-29 | 11.2% | 0.56 | -55.2% | 19.3% | 0.00% | 0.0 |
| Benchmark: SPY buy and hold | pre | 2006-06-01 to 2013-10-17 | 6.3% | 0.33 | -55.2% | 22.8% | 0.00% | 0.1 |
| Benchmark: SPY buy and hold | dev | 2013-10-18 to 2023-12-29 | 12.4% | 0.69 | -33.7% | 17.4% | 0.00% | 0.0 |
| Benchmark: SPY buy and hold | holdout | 2024-01-02 to 2026-10-29 | 20.2% | 1.00 | -18.8% | 15.4% | 0.00% | 0.0 |
| A: 70/30 SPY/GLD, monthly rebalance | full | 2006-06-01 to 2026-10-29 | 11.1% | 0.68 | -38.5% | 14.8% | 0.01% | 24.0 |
| A: 70/30 SPY/GLD, monthly rebalance | pre | 2006-06-01 to 2013-10-17 | 8.2% | 0.47 | -38.5% | 17.4% | 0.01% | 24.1 |
| A: 70/30 SPY/GLD, monthly rebalance | dev | 2013-10-18 to 2023-12-29 | 10.3% | 0.73 | -25.1% | 12.8% | 0.01% | 24.0 |
| A: 70/30 SPY/GLD, monthly rebalance | holdout | 2024-01-02 to 2026-10-29 | 22.5% | 1.24 | -12.9% | 13.7% | 0.01% | 24.1 |
| B: 70/30 SPY/GLD with 20% risk cap | full | 2006-06-01 to 2026-10-29 | 11.0% | 0.81 | -25.8% | 11.7% | 0.02% | 11.0 |
| B: 70/30 SPY/GLD with 20% risk cap | pre | 2006-06-01 to 2013-10-17 | 9.1% | 0.65 | -25.8% | 12.7% | 0.02% | 13.7 |
| B: 70/30 SPY/GLD with 20% risk cap | dev | 2013-10-18 to 2023-12-29 | 9.7% | 0.80 | -17.9% | 10.8% | 0.01% | 9.2 |
| B: 70/30 SPY/GLD with 20% risk cap | holdout | 2024-01-02 to 2026-10-29 | 21.1% | 1.27 | -12.0% | 12.3% | 0.02% | 10.6 |

## Fair Test verdicts
| Strategy | Verdict | Why | Report |
|---|---|---|---|
| Example (rejected in EXP-045): 70/30 + SPY 200-day trend filter | **FAILED** | Worse than the benchmark in development: lower Sharpe ratio and no meaningful reduction in falls. | [2026-10-29-example-70-30-spy-trend-filter-bac378fceb35.md](../../../research/fairtests/2026-10-29-example-70-30-spy-trend-filter-bac378fceb35.md) |
| A: 70/30 SPY/GLD, monthly rebalance | **INCONCLUSIVE** | Neither clearly better nor clearly worse than the benchmark in development. | [2026-10-29-spy-gld-70-30-monthly-518a2c8d1e1e.md](../../../research/fairtests/2026-10-29-spy-gld-70-30-monthly-518a2c8d1e1e.md) |
| B: 70/30 SPY/GLD with 20% risk cap | **INCONCLUSIVE** | Neither clearly better nor clearly worse than the benchmark in development. | [2026-10-29-spy-gld-70-30-risk-cap-6cd979072a5f.md](../../../research/fairtests/2026-10-29-spy-gld-70-30-risk-cap-6cd979072a5f.md) |

## Downturns
| Strategy | 2008-09 recession | 2020 Covid crash | 2022 rate rises |
|---|---|---|---|
| Example (rejected in EXP-045): 70/30 + SPY 200-day trend filter | +0.7% (worst -11.9%) | -8.7% (worst -15.6%) | -9.0% (worst -9.5%) |
| Benchmark: SPY buy and hold | -35.1% (worst -53.9%) | -9.9% (worst -33.7%) | -18.2% (worst -24.5%) |
| A: 70/30 SPY/GLD, monthly rebalance | -20.3% (worst -38.4%) | -4.3% (worst -25.1%) | -15.4% (worst -19.9%) |
| B: 70/30 SPY/GLD with 20% risk cap | -13.8% (worst -25.4%) | -6.2% (worst -15.9%) | -14.2% (worst -17.9%) |

Decision charts (last three years, open in a browser): [chart-example-70-30-spy-trend-filter.html](chart-example-70-30-spy-trend-filter.html), [chart-spy-buy-and-hold.html](chart-spy-buy-and-hold.html), [chart-spy-gld-70-30-monthly.html](chart-spy-gld-70-30-monthly.html), [chart-spy-gld-70-30-risk-cap.html](chart-spy-gld-70-30-risk-cap.html)
