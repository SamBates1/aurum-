# EXP-037: can Aurum-style portfolios beat the S&P 500? (real, 2026-10-29T22:27 UTC)

Historical simulation, net of costs; common dates 2006-06-30 → 2026-10-29; one account, next-open fills, cash at T-bill; leverage financed at T-bill + 1.5% (sensitivity +3%); mixes rebalanced monthly. Aurum = adopted strategy on GLD, SLV, GDX, NEM, AEM, WPM.

## Scorecard

| Strategy | pre: CAGR / Sharpe / max DD | dev: CAGR / Sharpe / max DD | holdout: CAGR / Sharpe / max DD | Exposure | Costs/yr | Beta vs SPY | Longest drawdown |
|---|---|---|---|---|---|---|---|
| SPY buy & hold | +6.5% / +0.34 / -55.2% | +12.4% / +0.69 / -33.7% | +20.2% / +1.00 / -18.8% | 100% | 0.00% | +1.00 | 1223 days |
| Aurum (adopted, core) | +2.1% / +0.13 / -32.7% | +3.6% / +0.25 / -20.5% | +23.1% / +1.29 / -13.0% | 100% | 0.00% | +0.13 | 2233 days |
| 60/40 SPY/IEF | +7.3% / +0.54 / -32.3% | +8.2% / +0.71 / -21.2% | +12.8% / +0.85 / -10.6% | 100% | 0.01% | +0.54 | 709 days |
| SPY 80% + Aurum 20% | +6.0% / +0.34 / -46.4% | +10.8% / +0.71 / -28.4% | +21.1% / +1.18 / -15.2% | 100% | 0.00% | +0.82 | 840 days |
| SPY 70% + Aurum 30% | +5.6% / +0.34 / -41.8% | +10.0% / +0.71 / -25.7% | +21.5% / +1.27 / -13.3% | 100% | 0.00% | +0.73 | 790 days |
| SPY 60% + Aurum 40% | +5.3% / +0.33 / -36.9% | +9.2% / +0.70 / -22.9% | +21.8% / +1.35 / -11.5% | 100% | 0.00% | +0.64 | 757 days |
| SPY 70% + GLD 30% | +8.5% / +0.49 / -38.5% | +10.3% / +0.73 / -25.1% | +22.5% / +1.24 / -12.9% | 100% | 0.01% | +0.71 | 612 days |
| Aurum rule on 7 assets | +5.6% / +0.59 / -12.2% | +3.2% / +0.30 / -16.7% | +13.2% / +1.04 / -6.1% | 83% | 0.08% | +0.19 | 1237 days |
| Risk parity 10% vol | +7.2% / +0.85 / -16.4% | +3.3% / +0.33 / -17.5% | +10.4% / +0.81 / -5.9% | 96% | 0.03% | +0.19 | 630 days |
| Risk parity x1.25 (borrow T-bill+1.5%) | +8.4% / +0.81 / -20.3% | +3.4% / +0.29 / -22.0% | +11.5% / +0.77 / -7.4% | 120% | 0.04% | +0.23 | 696 days |
| Risk parity x1.5 (borrow T-bill+1.5%) | +9.5% / +0.79 / -24.1% | +3.5% / +0.26 / -26.3% | +12.5% / +0.74 / -8.8% | 144% | 0.04% | +0.28 | 825 days |
| Risk parity x2 (borrow T-bill+1.5%) | +11.6% / +0.76 / -31.3% | +3.4% / +0.23 / -34.3% | +14.5% / +0.71 / -11.6% | 191% | 0.05% | +0.38 | 952 days |
| Aurum rule on 7 assets x1.5 (T-bill+1.5%) | +7.2% / +0.56 / -18.1% | +3.6% / +0.26 / -24.7% | +17.1% / +1.01 / -9.1% | 124% | 0.10% | +0.29 | 1325 days |

## Versus SPY (whole period): ΔCAGR, ΔSharpe, share of block-bootstrap resamples with higher Sharpe; pre-registered verdict

| Strategy | ΔCAGR | ΔSharpe | better | Verdict |
|---|---|---|---|---|
| SPY buy & hold | +0.0% | +0.00 | 0% | benchmark |
| Aurum (adopted, core) | -5.8% | -0.20 | 23% | does not beat SPY |
| 60/40 SPY/IEF | -2.8% | +0.09 | 95% | higher return per unit of risk, lower return |
| SPY 80% + Aurum 20% | -0.9% | +0.03 | 84% | higher return per unit of risk, lower return |
| SPY 70% + Aurum 30% | -1.3% | +0.05 | 80% | higher return per unit of risk, lower return |
| SPY 60% + Aurum 40% | -1.9% | +0.05 | 76% | higher return per unit of risk, lower return |
| SPY 70% + GLD 30% | -0.0% | +0.12 | 93% | higher return per unit of risk, lower return |
| Aurum rule on 7 assets | -5.9% | -0.05 | 39% | does not beat SPY |
| Risk parity 10% vol | -5.6% | +0.03 | 54% | higher return per unit of risk, lower return |
| Risk parity x1.25 (borrow T-bill+1.5%) | -5.0% | -0.01 | 46% | does not beat SPY |
| Risk parity x1.5 (borrow T-bill+1.5%) | -4.5% | -0.04 | 40% | does not beat SPY |
| Risk parity x2 (borrow T-bill+1.5%) | -3.5% | -0.08 | 33% | does not beat SPY |
| Aurum rule on 7 assets x1.5 (T-bill+1.5%) | -4.6% | -0.09 | 32% | does not beat SPY |

## Leverage and financing

| Leverage | T-bill+1.5% CAGR | T-bill+3% CAGR |
|---|---|---|
| 1.25 | +6.3% | +5.9% |
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
