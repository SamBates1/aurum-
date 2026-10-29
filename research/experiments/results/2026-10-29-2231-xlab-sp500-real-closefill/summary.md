# EXP-037: can Aurum-style portfolios beat the S&P 500? (real, 2026-10-29T22:32 UTC)

Historical simulation, net of costs; common dates 2006-06-30 → 2026-10-29; one account, next-open fills, cash at T-bill; leverage financed at T-bill + 1.5% (sensitivity +3%); mixes rebalanced monthly. Aurum = adopted strategy on GLD, SLV, GDX, NEM, AEM, WPM.

## Scorecard

| Strategy | pre: CAGR / Sharpe / max DD | dev: CAGR / Sharpe / max DD | holdout: CAGR / Sharpe / max DD | Exposure | Costs/yr | Beta vs SPY | Longest drawdown |
|---|---|---|---|---|---|---|---|
| SPY buy & hold | +6.4% / +0.34 / -55.2% | +12.4% / +0.69 / -33.7% | +20.2% / +1.00 / -18.8% | 100% | 0.00% | +1.00 | 1223 days |
| Aurum (adopted, core) | +2.1% / +0.13 / -32.7% | +3.6% / +0.25 / -20.5% | +23.1% / +1.29 / -13.0% | 100% | 0.00% | +0.13 | 2233 days |
| 60/40 SPY/IEF | +7.3% / +0.53 / -32.3% | +8.2% / +0.71 / -21.2% | +12.8% / +0.85 / -10.6% | 100% | 0.01% | +0.55 | 709 days |
| SPY 80% + Aurum 20% | +6.0% / +0.34 / -46.4% | +10.8% / +0.70 / -28.5% | +21.1% / +1.18 / -15.2% | 100% | 0.00% | +0.82 | 839 days |
| SPY 70% + Aurum 30% | +5.6% / +0.34 / -41.8% | +10.0% / +0.70 / -25.8% | +21.4% / +1.27 / -13.4% | 100% | 0.00% | +0.73 | 790 days |
| SPY 60% + Aurum 40% | +5.3% / +0.33 / -36.9% | +9.2% / +0.70 / -23.1% | +21.7% / +1.35 / -11.5% | 100% | 0.00% | +0.64 | 756 days |
| SPY 70% + GLD 30% | +8.4% / +0.48 / -38.6% | +10.3% / +0.73 / -25.2% | +22.5% / +1.24 / -12.9% | 100% | 0.01% | +0.71 | 612 days |
| Aurum rule on 7 assets | +5.4% / +0.57 / -12.5% | +3.1% / +0.28 / -17.0% | +13.5% / +1.08 / -6.0% | 83% | 0.08% | +0.19 | 1313 days |
| Risk parity 10% vol | +7.3% / +0.85 / -16.4% | +3.3% / +0.33 / -17.3% | +10.4% / +0.81 / -5.9% | 96% | 0.03% | +0.19 | 630 days |
| Risk parity x1.25 (borrow T-bill+1.5%) | +8.4% / +0.82 / -20.4% | +3.4% / +0.29 / -21.8% | +11.5% / +0.77 / -7.3% | 120% | 0.04% | +0.24 | 695 days |
| Risk parity x1.5 (borrow T-bill+1.5%) | +9.5% / +0.79 / -24.2% | +3.4% / +0.26 / -26.1% | +12.5% / +0.74 / -8.7% | 144% | 0.04% | +0.28 | 720 days |
| Risk parity x2 (borrow T-bill+1.5%) | +11.7% / +0.76 / -31.4% | +3.4% / +0.22 / -34.0% | +14.4% / +0.71 / -11.5% | 191% | 0.05% | +0.38 | 948 days |
| Aurum rule on 7 assets x1.5 (T-bill+1.5%) | +7.0% / +0.54 / -18.5% | +3.3% / +0.24 / -25.1% | +17.6% / +1.04 / -8.9% | 125% | 0.11% | +0.29 | 1325 days |

## Versus SPY (whole period): ΔCAGR, ΔSharpe, share of block-bootstrap resamples with higher Sharpe; pre-registered verdict

| Strategy | ΔCAGR | ΔSharpe | better | Verdict |
|---|---|---|---|---|
| SPY buy & hold | +0.0% | +0.00 | 0% | benchmark |
| Aurum (adopted, core) | -5.8% | -0.20 | 23% | does not beat SPY |
| 60/40 SPY/IEF | -2.8% | +0.09 | 94% | higher return per unit of risk, lower return |
| SPY 80% + Aurum 20% | -0.9% | +0.03 | 83% | higher return per unit of risk, lower return |
| SPY 70% + Aurum 30% | -1.3% | +0.04 | 80% | higher return per unit of risk, lower return |
| SPY 60% + Aurum 40% | -1.9% | +0.05 | 76% | higher return per unit of risk, lower return |
| SPY 70% + GLD 30% | -0.0% | +0.12 | 93% | higher return per unit of risk, lower return |
| Aurum rule on 7 assets | -6.0% | -0.06 | 36% | does not beat SPY |
| Risk parity 10% vol | -5.6% | +0.03 | 55% | higher return per unit of risk, lower return |
| Risk parity x1.25 (borrow T-bill+1.5%) | -5.0% | -0.01 | 46% | does not beat SPY |
| Risk parity x1.5 (borrow T-bill+1.5%) | -4.5% | -0.04 | 40% | does not beat SPY |
| Risk parity x2 (borrow T-bill+1.5%) | -3.5% | -0.08 | 33% | does not beat SPY |
| Aurum rule on 7 assets x1.5 (T-bill+1.5%) | -4.8% | -0.10 | 30% | does not beat SPY |

## Leverage and financing

| Leverage | T-bill+1.5% CAGR | T-bill+3% CAGR |
|---|---|---|
| 1.25 | +6.2% | +5.9% |
| 1.5 | +6.8% | +6.1% |
| 2 | +7.8% | +6.3% |

## Figures

- [Equity curves and drawdowns](figures/equity_drawdown.png)
- [Rolling return, volatility, Sharpe and correlation](figures/rolling.png)
- [Calendar-year returns](figures/annual_returns.png)
- [Return distributions (daily and monthly)](figures/return_distribution.png)
- [Tail-loss comparison](figures/tail_risk.png)
- [Turnover and transaction costs by year](figures/turnover_costs.png)
- [Exposure and weights (risk parity 10% vol)](figures/exposure_risk_parity.png)
- [Exposure and weights (Aurum rule on 7 assets)](figures/exposure_aurum7.png)
- [Gross vs net returns](figures/gross_vs_net_risk_parity.png)
- [Correlation of daily returns](figures/correlation.png)
- [Risk parity CAGR by leverage and financing cost vs SPY](figures/leverage_cagr.png)
- [Sharpe ratio by period](figures/sharpe_by_period.png)

Verdicts are proposals; nothing changes the traded strategy without a recorded decision.
