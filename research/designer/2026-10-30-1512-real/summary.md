# Strategy Designer results (2026-10-30 15:12 UTC, real data)

Yahoo Finance adjusted daily data (EOD), completed bars to 2026-10-30; historical backtest, net of costs. Every number is a historical backtest net of costs (one account, next-open fills, T-bill on cash, no borrowing).
Code 7aaf0b313979, commit abbe644, config 44b1b488763f.

## Reproduction check (designer engine vs the EXP-045 code path)
| Strategy | Max difference in account value | Result |
|---|---|---|
| spy-gld-70-30-monthly | 0.00e+00 | identical |
| spy-gld-70-30-risk-cap | 0.00e+00 | identical |
| example-70-30-spy-trend-filter | 0.00e+00 | identical |

## Results (full history and by period)
| Strategy | Period | Dates | CAGR | Sharpe | Worst fall | Volatility | Costs/yr | Orders/yr |
|---|---|---|---|---|---|---|---|---|
| EXP-049: 70/30 with ATR(14) stop 2, target 4 | full | 2006-06-01 to 2026-10-30 | 7.2% | 0.52 | -32.3% | 11.6% | 0.32% | 60.4 |
| EXP-049: 70/30 with ATR(14) stop 2, target 4 | pre | 2006-06-01 to 2013-10-17 | 7.0% | 0.46 | -32.3% | 14.2% | 0.29% | 58.7 |
| EXP-049: 70/30 with ATR(14) stop 2, target 4 | dev | 2013-10-18 to 2023-12-29 | 6.3% | 0.54 | -19.0% | 9.9% | 0.33% | 60.9 |
| EXP-049: 70/30 with ATR(14) stop 2, target 4 | holdout | 2024-01-02 to 2026-10-30 | 11.2% | 0.71 | -9.4% | 9.6% | 0.33% | 63.1 |
| EXP-049: 70/30 with ATR(14) stop 3, target 6 | full | 2006-06-01 to 2026-10-30 | 8.2% | 0.55 | -42.8% | 12.9% | 0.16% | 44.0 |
| EXP-049: 70/30 with ATR(14) stop 3, target 6 | pre | 2006-06-01 to 2013-10-17 | 6.6% | 0.41 | -42.8% | 15.7% | 0.14% | 42.0 |
| EXP-049: 70/30 with ATR(14) stop 3, target 6 | dev | 2013-10-18 to 2023-12-29 | 8.4% | 0.69 | -20.5% | 10.8% | 0.18% | 45.6 |
| EXP-049: 70/30 with ATR(14) stop 3, target 6 | holdout | 2024-01-02 to 2026-10-30 | 11.8% | 0.65 | -13.9% | 11.7% | 0.13% | 43.2 |
| EXP-049: 70/30 with 10% stop, no target | full | 2006-06-01 to 2026-10-30 | 11.2% | 0.72 | -29.2% | 13.7% | 0.01% | 24.8 |
| EXP-049: 70/30 with 10% stop, no target | pre | 2006-06-01 to 2013-10-17 | 8.5% | 0.54 | -29.2% | 14.7% | 0.02% | 26.2 |
| EXP-049: 70/30 with 10% stop, no target | dev | 2013-10-18 to 2023-12-29 | 10.3% | 0.73 | -25.1% | 12.8% | 0.01% | 24.0 |
| EXP-049: 70/30 with 10% stop, no target | holdout | 2024-01-02 to 2026-10-30 | 21.7% | 1.19 | -12.9% | 13.7% | 0.01% | 24.1 |

## Fair Test verdicts
| Strategy | Verdict | Why | Report |
|---|---|---|---|
| EXP-049: 70/30 with ATR(14) stop 2, target 4 | **FAILED** | Worse than the benchmark in development: lower Sharpe ratio and no meaningful reduction in falls. | [2026-10-30-exp049-atr-2-4-088ab8c10857.md](../../../research/fairtests/2026-10-30-exp049-atr-2-4-088ab8c10857.md) |
| EXP-049: 70/30 with ATR(14) stop 3, target 6 | **FAILED** | Worse than the benchmark in development: lower Sharpe ratio and no meaningful reduction in falls. | [2026-10-30-exp049-atr-3-6-7b9fdc57f822.md](../../../research/fairtests/2026-10-30-exp049-atr-3-6-7b9fdc57f822.md) |
| EXP-049: 70/30 with 10% stop, no target | **INCONCLUSIVE** | Neither clearly better nor clearly worse than the benchmark in development. | [2026-10-30-exp049-pct-10-stop-d28c59464d87.md](../../../research/fairtests/2026-10-30-exp049-pct-10-stop-d28c59464d87.md) |

## Downturns
| Strategy | 2008-09 recession | 2020 Covid crash | 2022 rate rises |
|---|---|---|---|
| EXP-049: 70/30 with ATR(14) stop 2, target 4 | -10.0% (worst -31.7%) | +2.1% (worst -12.7%) | -14.5% (worst -19.0%) |
| EXP-049: 70/30 with ATR(14) stop 3, target 6 | -24.6% (worst -42.5%) | +14.3% (worst -8.7%) | -16.2% (worst -20.5%) |
| EXP-049: 70/30 with 10% stop, no target | -16.4% (worst -29.1%) | -4.3% (worst -25.1%) | -15.4% (worst -19.9%) |

Decision charts (last three years, open in a browser): [chart-exp049-atr-2-4.html](chart-exp049-atr-2-4.html), [chart-exp049-atr-3-6.html](chart-exp049-atr-3-6.html), [chart-exp049-pct-10-stop.html](chart-exp049-pct-10-stop.html)
