# Machine learning versus simple strategies

Priority 4. Status: literature reviewed 2026-10-27; tested by benchmarks in `run_research.py` and EXP-004 / EXP-007.

## Evidence
- **Out-of-sample predictability of returns is weak.** Welch & Goyal (2008) showed that none of the
  well-known equity-premium predictors beat the historical mean out of sample, and most made forecasts
  worse, despite good in-sample fits. [S10]
- **Most published "discoveries" are likely false** once the number of tests is accounted for: Harvey, Liu &
  Zhu (2016) argue new factors should clear a t-statistic of about 3.0, not 2.0. [S11]
- **Selection bias is mechanical**: the best of many backtests looks good by chance. The Deflated Sharpe
  Ratio (Bailey & López de Prado 2014) adjusts for the number of trials and for skew/fat tails [S12]; the
  Probability of Backtest Overfitting (Bailey, Borwein, López de Prado & Zhu 2017) measures how often the
  in-sample winner underperforms out of sample [S13].
- Practical systems reflect this: FreqAI ships outlier gating and frequent retraining because ML signals
  decay; it leaves label leakage to the user (see [../frameworks/freqtrade.md](../frameworks/freqtrade.md)).

## What Aurum already does
- Walk-forward, expanding window, purged by the label horizon.
- The ML vote is weighted by its **point-in-time** out-of-sample AUC (zero at 0.50).
- Benchmarks in every research run: technical-only, ML-only, ML without macro, trend, momentum, buy & hold.
- Diagnostics beyond accuracy: AUC, Brier and log loss vs a constant forecast, calibration, per-fold AUC.

## Experiments
- **EXP-004 model families**: regularised logistic regression, random forest, calibrated boosting, an
  equal-weight ensemble, all with identical features, labels, folds and scoring. Fixed hyperparameters, no
  tuning (each tuning run would be another trial for the DSR).
- **EXP-007 labels**: triple-barrier labels that match the trade actually held (stop, target, max holding
  period) vs fixed 5-day direction labels.

## Prior expectation (stated before results)
On daily gold data the most likely outcome is that no model beats simple trend rules after costs by a margin
that survives the DSR. If so, the honest conclusion is to keep ML as a small, skill-weighted vote or drop it.
