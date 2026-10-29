# EXP-040: Volatility models: forecast accuracy and sizing

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, before any real-data run |
| Origin | Master brief §7; Patton (2011) QLIKE |

## Prediction question
21-day realised, EWMA (λ 0.94), GARCH(1,1) (quasi-maximum likelihood, expanding window, refit every 63 days) and HAR on
Parkinson ranges (and GVZ-adjusted for GLD/SLV/GDX), scored by QLIKE against the next 21 days' realised variance; and
99% one-day VaR breach rates (should be 1%).

## Portfolio question
Aurum's sizing rule on all ten assets with each estimator, vs plain 21-day volatility (lab rules); risk parity with
covariance as a further variant. Risk reduction and return prediction are reported separately.

Cross-asset lab rules (README, 'Cross-asset lab'): universe SPY, QQQ, IWM, EFA, TLT, IEF, GLD, SLV, GDX, DBC (CPER excluded: data audit found paired ±30–50% bad prints in 2014–15); costs SPY/QQQ 2, IWM/EFA/TLT/IEF/GLD 3, SLV/GDX 5, DBC 8 bps one way; one account, next-open fills, T-bill on cash; periods pre (to 2013-10-17), dev (to 2023), holdout (2024+); figures in each result folder's `figures/`.

## Results
_Not yet run on real data._
