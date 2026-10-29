# EXP-042: Machine learning vs simple baselines

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, before any real-data run |
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

## Results
_Not yet run on real data._
