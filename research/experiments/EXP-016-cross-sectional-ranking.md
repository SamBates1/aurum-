# EXP-016: Ranking the six assets against each other

| Field | |
|---|---|
| Status | Run 2026-10-29: not adopted |
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

## Results (real data, 2026-10-29 12:46 UTC; `results/2026-10-29-1248-real-vs-vol_hold/` and `…-1251-real-closefill-vs-vol_hold/`)
16 variants tried; PBO across them 18% (open fills) / 9% (close fills): low, so the ranking of variants is fairly stable between halves of the history.

| Variant | Dev Sharpe | Dev ΔSharpe vs vol_hold | better | Holdout ΔSharpe | DSR | Verdict (open fills) | Dev ΔSharpe / verdict (close fills) |
|---|---|---|---|---|---|---|---|
| xs_mom_126 | +0.03 | -0.10 | 0% | -0.06 | 0.39 | REJECT | -0.09 / REJECT |
| xs_mom_252_21 | +0.06 | -0.06 | 5% | -0.05 | 0.44 | REJECT | -0.07 / REJECT |

**Rejected.** Over-weighting the recent leaders among the six assets *lowered* development Sharpe (−0.06 to −0.10, worse in 95–100% of resamples) with both fills. With six highly correlated gold assets, relative momentum did not persist. **Not adopted.**
