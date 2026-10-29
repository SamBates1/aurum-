# EXP-017: Better volatility forecasts for sizing

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, awaiting a real-data run |
| Origin | Stage 4; HAR model [S19]; RiskMetrics EWMA; CBOE gold volatility index (GVZ). |

## Common setup (stages 3–4, pre-registered 2026-10-29 before any real-data run)
All variants use the new target-weight engine (`strategy.simulate_weights`): each sleeve holds a *fraction* of its
value in the asset and is resized at the next open (and, as a check, the next close: D-018) when the target moves
more than 5 points. They are compared with **`vol_hold`** (EXP-014) rather than the old timing baseline, so each
idea is judged on whether it adds anything to simply holding with volatility-based sizing. Standard acceptance
rules (registry README) apply; the trial set is all variants in this run. Run with
`python run_experiments.py --baseline vol_hold --exps EXP-014,EXP-015,EXP-016,EXP-017,EXP-018,EXP-019`.

## Hypothesis
Sizing on a better volatility forecast keeps realised risk closer to target and improves risk-adjusted return versus 21-day realised volatility.

## Variants (fixed before running)
`vol_hold_ewma` (EWMA, λ = 0.94); `vol_hold_har` (HAR on Parkinson high-low variance, target = next-21-day close-to-close variance, refitted every 63 days on purged data); `vol_hold_gvz` (21-day vol × GVZ/GLD-vol ratio, clipped 0.5–2).

## Acceptance criteria
Standard rules vs `vol_hold`; also report portfolio volatility vs the 15% target (closer is better).

## Results
_Not yet run._
