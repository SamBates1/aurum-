# EXP-040: volatility models (real)

**Prediction question:** median QLIKE across assets (dev; lower = better forecasts of the next 21 days' variance): gvz_adjusted 0.209, garch_1_1 0.245, har_parkinson 0.263, ewma_094 0.272, realised_21d 0.339.

**Portfolio question:** Aurum's sizing rule on all assets with each estimator vs plain 21-day volatility:

| Variant | pre ΔSharpe (better) | dev ΔSharpe (better) | holdout ΔSharpe (better) | dev 2× cost | DSR | Verdict |
|---|---|---|---|---|---|---|
| realised_21d | +0.00 (0%) | +0.00 (0%) | +0.00 (0%) | +0.00 | – | baseline |
| ewma_094 | +0.03 (87%) | +0.00 (52%) | -0.00 (50%) | +0.00 | 0.89 | INCONCLUSIVE |
| garch_1_1 | +0.03 (84%) | +0.02 (84%) | -0.01 (37%) | +0.02 | 0.90 | INCONCLUSIVE |
| har_parkinson | +0.04 (77%) | +0.05 (86%) | +0.02 (57%) | +0.05 | 0.91 | INCONCLUSIVE |
| risk_parity_10 (covariance) | +0.18 (96%) | +0.02 (60%) | -0.11 (21%) | +0.03 | 0.90 | INCONCLUSIVE |
| equal weight (reference) | -0.13 (10%) | +0.08 (80%) | -0.05 (37%) | +0.08 | – | reference |

## Scorecard

| Strategy | pre: CAGR / Sharpe / max DD | dev: CAGR / Sharpe / max DD | holdout: CAGR / Sharpe / max DD | Exposure | Costs/yr | Beta vs SPY | Longest drawdown |
|---|---|---|---|---|---|---|---|
| realised_21d | +7.9% / +0.90 / -10.1% | +4.2% / +0.40 / -16.0% | +14.6% / +1.09 / -7.3% | 80% | 0.09% | +0.27 | 735 days |
| ewma_094 | +7.9% / +0.93 / -9.8% | +4.1% / +0.40 / -16.0% | +14.4% / +1.09 / -7.5% | 78% | 0.07% | +0.26 | 733 days |
| garch_1_1 | +7.7% / +0.93 / -9.3% | +4.2% / +0.42 / -15.3% | +14.1% / +1.08 / -7.1% | 68% | 0.08% | +0.21 | 735 days |
| har_parkinson | +7.3% / +0.94 / -9.3% | +4.4% / +0.44 / -16.0% | +14.5% / +1.11 / -6.1% | 69% | 0.07% | +0.25 | 534 days |
| risk_parity_10 (covariance) | +9.7% / +1.07 / -9.5% | +4.5% / +0.42 / -18.9% | +14.2% / +0.99 / -7.6% | 91% | 0.04% | +0.31 | 600 days |
| equal weight (reference) | +10.2% / +0.77 / -15.7% | +6.5% / +0.47 / -23.5% | +20.5% / +1.04 / -11.9% | 100% | 0.02% | +0.51 | 952 days |

## 99% one-day VaR breach rates (target 1.0%)

| Estimator | Median breach rate across assets |
|---|---|
| ewma_094 | 1.99% |
| garch_1_1 | 1.60% |
| gvz_adjusted | 0.89% |
| har_parkinson | 1.19% |
| realised_21d | 2.32% |

VaR assumes normal returns; breach rates above 1% show fat tails, which is why expected shortfall and stress windows are reported elsewhere.

## Figures

- [Equity curves and drawdowns](figures/equity_drawdown.png)
- [QLIKE loss of volatility forecasts vs next-21-day realised variance (dev; lower is better)](figures/qlike_dev.png)
- [Share of days with a loss beyond the 1-day 99% normal VaR (target 1%)](figures/var_breaches.png)
- [GLD volatility forecasts](figures/gld_vol_forecasts.png)
- [Exposure and weights (risk parity 10%)](figures/exposure_risk_parity.png)
- [GLD: average next-63-day return by current volatility quintile (descriptive)](figures/gld_vol_vs_future.png)
