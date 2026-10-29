# EXP-018: Gold implied volatility as a risk gate

| Field | |
|---|---|
| Status | Run 2026-10-29: not adopted |
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

## Results (real data, 2026-10-29 12:46 UTC; `results/2026-10-29-1248-real-vs-vol_hold/` and `…-1251-real-closefill-vs-vol_hold/`)
16 variants tried; PBO across them 18% (open fills) / 9% (close fills): low, so the ranking of variants is fairly stable between halves of the history.

| Variant | Dev Sharpe | Dev ΔSharpe vs vol_hold | better | Holdout ΔSharpe | DSR | Verdict (open fills) | Dev ΔSharpe / verdict (close fills) |
|---|---|---|---|---|---|---|---|
| gvz_gate | +0.09 | -0.03 | 30% | +0.26 | 0.47 | REJECT | -0.08 / REJECT |

**Rejected.** Halving exposure when GVZ is high lowered development Sharpe (−0.03 / −0.08) without reducing drawdown, even though it helped on the holdout (+0.26). Using GVZ *continuously* in sizing (EXP-017) worked; using it as an on/off switch did not. **Not adopted.**
