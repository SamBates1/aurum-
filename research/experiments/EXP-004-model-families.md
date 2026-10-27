# EXP-004: Model families

| Field | |
|---|---|
| Status | Pre-registered 2026-10-27, awaiting a real-data run |
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

## Results
_Not yet run on real data._ After `python run_experiments.py`, copy the rows for this experiment from
`results/<date>-real/summary.md` here, with the verdict and any decision recorded in `../decisions.md`.
