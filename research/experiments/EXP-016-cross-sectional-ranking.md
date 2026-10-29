# EXP-016: Ranking the six assets against each other

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, awaiting a real-data run |
| Origin | Stage 3; cross-sectional momentum literature; idea that relative performance is easier to predict than direction. |

## Common setup (stages 3–4, pre-registered 2026-10-29 before any real-data run)
All variants use the new target-weight engine (`strategy.simulate_weights`): each sleeve holds a *fraction* of its
value in the asset and is resized at the next open (and, as a check, the next close: D-018) when the target moves
more than 5 points. They are compared with **`vol_hold`** (EXP-014) rather than the old timing baseline, so each
idea is judged on whether it adds anything to simply holding with volatility-based sizing. Standard acceptance
rules (registry README) apply; the trial set is all variants in this run. Run with
`python run_experiments.py --baseline vol_hold --exps EXP-014,EXP-015,EXP-016,EXP-017,EXP-018,EXP-019`.

## Hypothesis
Assets with the strongest recent returns relative to the other five keep outperforming, so over-weighting the leaders and under-weighting the laggards beats vol_hold.

## Variants (fixed before running)
`xs_mom_126`: rank by 6-month return; top two × 1.5, bottom two × 0.5 (capped at 1). `xs_mom_252_21`: same with 12-month return skipping the latest month. Ranks use closes up to each date only.

## Acceptance criteria
Standard rules vs `vol_hold`. Note: with only six highly correlated assets the effect may be small.

## Results
_Not yet run._
