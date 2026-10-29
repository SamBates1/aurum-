# EXP-004: Model families

| Field | |
|---|---|
| Status | Run 2026-10-29 on real data: see Results |
| Origin | ML-vs-simple literature [S10][S11]; FreqAI's model plug-ins. |
| Current Aurum equivalent | Aurum uses one model (shallow gradient boosting) with fixed parameters. |

## Hypothesis
A simpler (logistic) or averaged model gives more stable, better-calibrated probabilities and at least equal strategy performance.

## Variants (fixed before running)
`model_logit` (standardised features, L2-regularised logistic regression, C=0.1; scaler fitted inside each training window); `model_forest` (200 shallow trees, depth 4, min leaf 50); `model_hgb_calibrated` (boosting fitted on the first 80% of each training window, Platt-calibrated on the last 20% after a 5-day gap); `model_ensemble` (equal average of logistic, boosting, forest). Same features, labels, folds, scoring and skill weighting.

## Acceptance criteria
Standard rules. Also compare development AUC and Brier score in `run_research.py` output when choosing. See [README](README.md#acceptance-criteria-applied-automatically-by-run_experimentspyverdict).

## Main risks and limitations
No hyperparameter search (each search would add trials). Random forest is the slowest variant.

## Results (real data, first run 2026-10-29 11:34 UTC; files at commit `c3d1f65`, `results/2026-10-29-real/`)
Portfolio of 6 sleeves, net of costs, vs the baseline over identical dates. Development 2013-10-18 → 2023-12-31;
holdout from 2024-01-01. 26 variants tried in total; PBO across them 77%. (The same folder name was
reused by the 12:12 run, which added EXP-013 and overwrote these files; they remain in git history.)

| Variant | Dev Sharpe | Dev ΔSharpe | better | ΔSharpe 2× cost | Dev max DD | Holdout ΔSharpe | DSR | Verdict |
|---|---|---|---|---|---|---|---|---|
| model_logit | -0.01 | +0.00 | 53% | +0.02 | -22.1% | +0.05 | 0.25 | INCONCLUSIVE |
| model_forest | +0.07 | +0.08 | 77% | +0.10 | -21.1% | -0.02 | 0.33 | INCONCLUSIVE |
| model_hgb_calibrated | +0.08 | +0.09 | 78% | +0.10 | -19.0% | -0.07 | 0.35 | INCONCLUSIVE |
| model_ensemble | +0.05 | +0.06 | 82% | +0.08 | -20.3% | +0.00 | 0.32 | INCONCLUSIVE |

Forest, calibrated boosting and the ensemble were slightly better than the baseline model in development (+0.06 to +0.09, beating it in 77–82% of resamples) but below the +0.10 bar, flat-to-worse on the holdout, and DSR ≈ 0.33. Logistic regression matched the baseline. **Conclusion: model choice makes little difference; none adopted. The ensemble is the most consistent and could be re-tested if the model's role grows.**
