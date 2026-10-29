# EXP-042: machine learning vs simple baselines (real)

Assets SPY, EFA, TLT, GLD, GDX, DBC; label = 21-day forward return > 0; features: price/technical, cross-asset 21-day returns, dollar, real yield, breakeven, credit (HYG/IEF), VIX, yield curve (FRED lagged 2 business days); expanding walk-forward from 3 years, refit every 126 days, purge 21 days.

## Prediction question (development period, median across assets)

| Model | AUC | Information coefficient | Share of assets where Brier beats climatology |
|---|---|---|---|
| climatology | 0.400 | -0.157 | 0% |
| gradient_boosting | 0.499 | -0.009 | 0% |
| logit_l1 | 0.512 | +0.005 | 0% |
| logit_l2 | 0.495 | -0.012 | 0% |
| random_forest | 0.524 | +0.058 | 17% |
| tsmom_252 (rule) | 0.486 | -0.061 | 0% |

## Portfolio question: hold the asset (vol-sized) only when the model says up, vs always holding

| Variant | pre ΔSharpe (better) | dev ΔSharpe (better) | holdout ΔSharpe (better) | dev 2× cost | DSR | Verdict |
|---|---|---|---|---|---|---|
| no-signal vol-sized (baseline) | +0.00 (0%) | +0.00 (0%) | +0.00 (0%) | +0.00 | – | baseline |
| logit_l2 | -0.29 (8%) | +0.01 (53%) | -0.11 (38%) | -0.08 | 0.68 | INCONCLUSIVE |
| logit_l1 | -0.39 (5%) | +0.05 (60%) | -0.14 (33%) | -0.01 | 0.72 | REJECT (failed on holdout and pre-2013) |
| random_forest | -0.20 (22%) | +0.07 (68%) | +0.02 (57%) | -0.00 | 0.74 | INCONCLUSIVE |
| gradient_boosting | -0.23 (19%) | -0.29 (3%) | +0.17 (75%) | -0.44 | 0.30 | REJECT |
| tsmom_252 (rule) | +0.39 (87%) | +0.01 (50%) | -0.13 (16%) | -0.02 | – | reference |

## Scorecard

| Strategy | pre: CAGR / Sharpe / max DD | dev: CAGR / Sharpe / max DD | holdout: CAGR / Sharpe / max DD | Exposure | Costs/yr | Beta vs SPY | Longest drawdown |
|---|---|---|---|---|---|---|---|
| no-signal vol-sized (baseline) | +4.7% / +0.56 / -11.5% | +3.5% / +0.31 / -20.2% | +15.2% / +1.14 / -7.0% | 80% | 0.09% | +0.24 | 1329 days |
| logit_l2 | +1.7% / +0.27 / -11.7% | +3.0% / +0.33 / -10.6% | +11.4% / +1.03 / -5.2% | 58% | 0.54% | +0.21 | 1678 days |
| logit_l1 | +1.1% / +0.17 / -14.0% | +3.3% / +0.36 / -11.2% | +11.0% / +1.00 / -5.2% | 61% | 0.40% | +0.22 | 2136 days |
| random_forest | +2.4% / +0.36 / -11.7% | +3.5% / +0.38 / -13.8% | +12.7% / +1.16 / -4.6% | 60% | 0.45% | +0.22 | 1467 days |
| gradient_boosting | +2.0% / +0.33 / -9.7% | +1.2% / +0.02 / -13.3% | +13.0% / +1.31 / -4.6% | 55% | 0.80% | +0.20 | 2318 days |
| tsmom_252 (rule) | +6.2% / +0.95 / -6.4% | +2.9% / +0.33 / -10.2% | +13.0% / +1.00 / -6.8% | 55% | 0.24% | +0.12 | 546 days |

## Figures

- [Calibration, ROC and predictions: GLD gradient_boosting](figures/calibration_GLD_gradient_boosting.png)
- [Calibration, ROC and predictions: GLD logit_l2](figures/calibration_GLD_logit_l2.png)
- [Calibration, ROC and predictions: SPY gradient_boosting](figures/calibration_SPY_gradient_boosting.png)
- [Calibration, ROC and predictions: SPY logit_l2](figures/calibration_SPY_logit_l2.png)
- [Out-of-sample AUC by model and asset (dev); 0.50 = no skill](figures/auc_dev.png)
- [Information coefficient (rank corr. of prediction with realised return), dev](figures/ic_dev.png)
- [Out-of-sample AUC by model and asset (holdout); 0.50 = no skill](figures/auc_holdout.png)
- [Information coefficient (rank corr. of prediction with realised return), holdout](figures/ic_holdout.png)
- [Feature stability: share of walk-forward folds with a positive L2-logit coefficient](figures/feature_stability.png)
- [GLD: realised 21-day return by predicted-probability quintile (out of sample)](figures/gld_signal_strength.png)
- [Equity curves and drawdowns](figures/equity_drawdown.png)
