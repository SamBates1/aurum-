# EXP-044: execution delay and cost sensitivity of the adopted strategy (real)

Whole period, one account. Sharpe ratio by execution timing (rows) and multiple of the assumed costs (columns):

| Execution | 0× costs | 1× costs | 2× costs | 3× costs | 5× costs |
|---|---|---|---|---|---|
| next close | 0.38 | 0.37 | 0.35 | 0.33 | 0.30 |
| next open (as traded) | 0.38 | 0.36 | 0.35 | 0.33 | 0.30 |
| open, 1 extra day late | 0.39 | 0.37 | 0.36 | 0.34 | 0.31 |
| open, 2 extra days late | 0.38 | 0.37 | 0.35 | 0.33 | 0.30 |
| open, 5 extra days late | 0.38 | 0.36 | 0.34 | 0.33 | 0.29 |

## Figures

- [Sharpe vs transaction-cost multiple and execution timing](figures/cost_delay_sharpe.png)
- [CAGR vs transaction-cost multiple and execution timing](figures/cost_delay_cagr.png)
- [Equity curves and drawdowns](figures/delay_equity.png)
