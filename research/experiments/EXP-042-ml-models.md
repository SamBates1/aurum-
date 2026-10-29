# EXP-042: Machine learning vs simple baselines

| Field | |
|---|---|
| Status | Run 2026-10-29: ML models have no reliable skill; not adopted |
| Origin | Master brief §8 |

## Design
Assets SPY, EFA, TLT, GLD, GDX, DBC. Label: 21-day forward return > 0. Features (all known at the close): technical
(returns 1/5/21/63/252, 21-day vol, RSI, MACD, SMA gaps, Bollinger z, ATR), other assets' 21-day returns, dollar,
real yield and breakeven changes (FRED lagged 2 business days), credit (HYG/IEF; FRED's high-yield spread has only 3
years of history), VIX, yield curve. Models: L2 and L1 logistic regression, random forest, gradient boosting (fixed
parameters). Expanding walk-forward from 3 years, refit every 126 days, purge 21 days. Baselines: climatology (the
share of up periods revealed so far), 12-month momentum, and always holding.

## Questions
Signal: out-of-sample AUC, Brier vs climatology, information coefficient, calibration, feature stability across folds.
Portfolio: hold each asset (vol-sized) only when P(up) > 0.5, vs always holding; lab rules.

Cross-asset lab rules (README, 'Cross-asset lab'): universe SPY, QQQ, IWM, EFA, TLT, IEF, GLD, SLV, GDX, DBC (CPER excluded: data audit found paired ±30–50% bad prints in 2014–15); costs SPY/QQQ 2, IWM/EFA/TLT/IEF/GLD 3, SLV/GDX 5, DBC 8 bps one way; one account, next-open fills, T-bill on cash; periods pre (to 2013-10-17), dev (to 2023), holdout (2024+); figures in each result folder's `figures/`.

## Results (real data, 2026-10-29; `results/2026-10-29-2128-xlab-ml-real/` (summary.md, CSVs, figures/))
About 2,600 out-of-sample predictions per asset in development, 690 in the holdout.

| Model | Median AUC (dev) | Median information coefficient | Brier better than climatology |
|---|---|---|---|
| L2 logistic | 0.495 | −0.01 | 0 of 6 assets |
| L1 logistic | 0.512 | +0.01 | 0 of 6 |
| Random forest | 0.524 | +0.06 | 1 of 6 |
| Gradient boosting | 0.499 | −0.01 | 0 of 6 |

(Climatology's AUC is not meaningful: it barely varies.) Portfolio (ΔSharpe vs always holding, pre / dev / holdout):
L2 −0.29 / +0.01 / −0.11; L1 −0.39 / +0.05 / −0.14 (REJECT); random forest −0.20 / +0.07 / +0.02 (INCONCLUSIVE); boosting
−0.23 / −0.29 / +0.17 (REJECT). The random forest's small edge in development disappears before 2013. Removing ML costs
nothing; it stays as dashboard context only.
