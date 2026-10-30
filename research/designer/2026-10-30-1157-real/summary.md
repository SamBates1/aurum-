# Strategy Designer results (2026-10-30 11:57 UTC, real data)

Yahoo Finance adjusted daily data (EOD), completed bars to 2026-10-29; historical backtest, net of costs. Every number is a historical backtest net of costs (one account, next-open fills, T-bill on cash, no borrowing).
Code d836141cb562, commit f6cea5b, config cc68131bf771.

## Reproduction check (designer engine vs the EXP-045 code path)
| Strategy | Max difference in account value | Result |
|---|---|---|
| spy-gld-70-30-monthly | 0.00e+00 | identical |
| spy-gld-70-30-risk-cap | 0.00e+00 | identical |
| example-70-30-spy-trend-filter | 0.00e+00 | identical |

## Results (full history and by period)
| Strategy | Period | Dates | CAGR | Sharpe | Worst fall | Volatility | Costs/yr | Orders/yr |
|---|---|---|---|---|---|---|---|---|
| C: 70/30 SPY/GLD, rebalanced every day | full | 2006-06-01 to 2026-10-29 | 11.2% | 0.68 | -38.1% | 14.9% | 0.03% | 503.9 |
| C: 70/30 SPY/GLD, rebalanced every day | pre | 2006-06-01 to 2013-10-17 | 8.3% | 0.47 | -38.1% | 17.7% | 0.03% | 503.7 |
| C: 70/30 SPY/GLD, rebalanced every day | dev | 2013-10-18 to 2023-12-29 | 10.3% | 0.73 | -25.5% | 13.0% | 0.03% | 504.0 |
| C: 70/30 SPY/GLD, rebalanced every day | holdout | 2024-01-02 to 2026-10-29 | 22.8% | 1.25 | -13.0% | 13.7% | 0.03% | 504.0 |

## Fair Test verdicts
| Strategy | Verdict | Why | Report |
|---|---|---|---|
| C: 70/30 SPY/GLD, rebalanced every day | **FAILED** | Worse than the benchmark in development: lower Sharpe ratio and no meaningful reduction in falls. | [2026-10-30-spy-gld-70-30-daily-9245b2081d68.md](../../../research/fairtests/2026-10-30-spy-gld-70-30-daily-9245b2081d68.md) |

## Downturns
| Strategy | 2008-09 recession | 2020 Covid crash | 2022 rate rises |
|---|---|---|---|
| C: 70/30 SPY/GLD, rebalanced every day | -19.5% (worst -37.9%) | -4.6% (worst -25.5%) | -15.2% (worst -19.7%) |

Decision charts (last three years, open in a browser): [chart-spy-gld-70-30-daily.html](chart-spy-gld-70-30-daily.html)
