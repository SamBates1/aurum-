# EXP-015: Does prediction add value, and at which horizon?

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, awaiting a real-data run |
| Origin | Stage 3; Moskowitz–Ooi–Pedersen (momentum persists 1–12 months); first results showed 5-day direction is close to a coin flip. |

## Common setup (stages 3–4, pre-registered 2026-10-29 before any real-data run)
All variants use the new target-weight engine (`strategy.simulate_weights`): each sleeve holds a *fraction* of its
value in the asset and is resized at the next open (and, as a check, the next close: D-018) when the target moves
more than 5 points. They are compared with **`vol_hold`** (EXP-014) rather than the old timing baseline, so each
idea is judged on whether it adds anything to simply holding with volatility-based sizing. Standard acceptance
rules (registry README) apply; the trial set is all variants in this run. Run with
`python run_experiments.py --baseline vol_hold --exps EXP-014,EXP-015,EXP-016,EXP-017,EXP-018,EXP-019`.

## Hypothesis
The same model predicts 21- or 63-day direction better than 5-day direction, and tilting vol_hold weights by that prediction improves risk-adjusted return.

## Variants (fixed before running)
`ml_tilt_h5`, `ml_tilt_h21`, `ml_tilt_h63`: weight = vol_hold weight × (1 + skill × (2·P(up over h days) − 1)), capped at 1; skill is the point-in-time out-of-sample AUC weighting (0 at AUC 0.50, full at 0.56) using labels revealed by each date; purge gap = h.

## Acceptance criteria
Standard rules vs `vol_hold`. Also compare out-of-sample AUC by horizon (diagnostic).

## Results
_Not yet run._
