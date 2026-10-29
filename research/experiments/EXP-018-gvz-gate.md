# EXP-018: Gold implied volatility as a risk gate

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, awaiting a real-data run |
| Origin | Stage 4; replaces the equity VIX gate tested in EXP-003 with gold's own implied volatility. |

## Common setup (stages 3–4, pre-registered 2026-10-29 before any real-data run)
All variants use the new target-weight engine (`strategy.simulate_weights`): each sleeve holds a *fraction* of its
value in the asset and is resized at the next open (and, as a check, the next close: D-018) when the target moves
more than 5 points. They are compared with **`vol_hold`** (EXP-014) rather than the old timing baseline, so each
idea is judged on whether it adds anything to simply holding with volatility-based sizing. Standard acceptance
rules (registry README) apply; the trial set is all variants in this run. Run with
`python run_experiments.py --baseline vol_hold --exps EXP-014,EXP-015,EXP-016,EXP-017,EXP-018,EXP-019`.

## Hypothesis
Halving exposure when gold options price unusually high risk reduces drawdowns without hurting Sharpe.

## Variants (fixed before running)
`gvz_gate`: vol_hold weights × 0.5 while GVZ is above its trailing 252-day 80th percentile.

## Acceptance criteria
Risk-control path (volatility-adjusted drawdown ≥ 20% better, ΔSharpe ≥ −0.05) vs `vol_hold`.

## Results
_Not yet run._
