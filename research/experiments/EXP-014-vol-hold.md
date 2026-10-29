# EXP-014: Always invested, sized by volatility (candidate new baseline)

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, awaiting a real-data run |
| Origin | Stage 2 (EXP-013) and correction of D-019: the `vol_sized_hold` reference chose its size once and never resized, so its lower drawdowns came mostly from holding cash. |

## Common setup (stages 3–4, pre-registered 2026-10-29 before any real-data run)
All variants use the new target-weight engine (`strategy.simulate_weights`): each sleeve holds a *fraction* of its
value in the asset and is resized at the next open (and, as a check, the next close: D-018) when the target moves
more than 5 points. They are compared with **`vol_hold`** (EXP-014) rather than the old timing baseline, so each
idea is judged on whether it adds anything to simply holding with volatility-based sizing. Standard acceptance
rules (registry README) apply; the trial set is all variants in this run. Run with
`python run_experiments.py --baseline vol_hold --exps EXP-014,EXP-015,EXP-016,EXP-017,EXP-018,EXP-019`.

## Hypothesis
Holding every asset at weight min(1, 15% / 21-day volatility), resized as volatility changes, earns more than the current timing strategy while keeping drawdowns well below buy & hold.

## Variants (fixed before running)
`vol_hold` (5-point band, checked daily); `vol_hold_band0` (resize daily); `vol_hold_band10`; `vol_hold_monthly` (resize every 21 days); `vol_hold_tv20` (20% target: more invested).

## Acceptance criteria
**Adopt `vol_hold` as the traded strategy** only if, versus the current timing baseline, in both development and holdout and with both open and close fills: CAGR higher **and** Sharpe higher; **and** its max drawdown is at least 25% smaller than buy & hold's in both periods. The band/monthly/target variants are judged with the standard rules against `vol_hold` (lower turnover with ΔSharpe ≥ 0 counts in favour).

## Results
_Not yet run._
