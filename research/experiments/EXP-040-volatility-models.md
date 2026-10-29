# EXP-040: Volatility models: forecast accuracy and sizing

| Field | |
|---|---|
| Status | Run 2026-10-29: GVZ-adjusted volatility forecasts best; better forecasts barely change portfolio results |
| Origin | Master brief §7; Patton (2011) QLIKE |

## Prediction question
21-day realised, EWMA (λ 0.94), GARCH(1,1) (quasi-maximum likelihood, expanding window, refit every 63 days) and HAR on
Parkinson ranges (and GVZ-adjusted for GLD/SLV/GDX), scored by QLIKE against the next 21 days' realised variance; and
99% one-day VaR breach rates (should be 1%).

## Portfolio question
Aurum's sizing rule on all ten assets with each estimator, vs plain 21-day volatility (lab rules); risk parity with
covariance as a further variant. Risk reduction and return prediction are reported separately.

Cross-asset lab rules (README, 'Cross-asset lab'): universe SPY, QQQ, IWM, EFA, TLT, IEF, GLD, SLV, GDX, DBC (CPER excluded: data audit found paired ±30–50% bad prints in 2014–15); costs SPY/QQQ 2, IWM/EFA/TLT/IEF/GLD 3, SLV/GDX 5, DBC 8 bps one way; one account, next-open fills, T-bill on cash; periods pre (to 2013-10-17), dev (to 2023), holdout (2024+); figures in each result folder's `figures/`.

## Results (real data, 2026-10-29; `results/2026-10-29-2127-xlab-vol-real/` (summary.md, CSVs, figures/))
**Prediction (QLIKE, development, median across assets; lower is better):** GVZ-adjusted 0.209 (gold assets only),
GARCH(1,1) 0.245, HAR 0.263, EWMA 0.272, plain 21-day 0.339. **99% one-day VaR breach rates (target 1%):** GVZ-adjusted
0.89%, HAR 1.19%, GARCH 1.60%, EWMA 1.99%, plain 21-day 2.32%. This is independent support for D-021: options-implied
volatility gives the best risk forecasts for gold assets.

**Portfolio (ΔSharpe vs 21-day sizing, pre / dev / holdout):** EWMA +0.03 / +0.00 / −0.00; GARCH +0.03 / +0.02 / −0.01;
HAR +0.04 / +0.05 / +0.02 (consistent but below the +0.10 bar); risk parity with covariance +0.18 / +0.02 / −0.11.
All INCONCLUSIVE. Better forecasts make risk estimates more accurate; they add little return per unit of risk.
