# EXP-017: Better volatility forecasts for sizing

| Field | |
|---|---|
| Status | Run 2026-10-29: **adopted** |
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

## Results (real data, 2026-10-29 12:46 UTC; `results/2026-10-29-1248-real-vs-vol_hold/` and `…-1251-real-closefill-vs-vol_hold/`)
16 variants tried; PBO across them 18% (open fills) / 9% (close fills): low, so the ranking of variants is fairly stable between halves of the history.

| Variant | Dev Sharpe | Dev ΔSharpe vs vol_hold | better | Holdout ΔSharpe | DSR | Verdict (open fills) | Dev ΔSharpe / verdict (close fills) |
|---|---|---|---|---|---|---|---|
| vol_hold_ewma | +0.11 | -0.01 | 31% | +0.03 | 0.50 | REJECT | +0.01 / INCONCLUSIVE |
| vol_hold_har | +0.18 | +0.06 | 90% | -0.03 | 0.59 | INCONCLUSIVE | +0.08 / INCONCLUSIVE |
| vol_hold_gvz | +0.24 | +0.12 | 99% | +0.06 | 0.66 | KEEP (held on holdout) | +0.14 / KEEP (held on holdout) |

**`vol_hold_gvz` passed every pre-registered rule with both fills** (development +0.12 / +0.14, better in 99–100% of resamples, still +0.11 / +0.13 at 2× costs, holdout +0.06 / +0.00, DSR 0.66 / 0.63) and cut the development max drawdown from −27.8% to −20.8%. Using gold options' forward-looking risk (GVZ) to scale position sizes worked better than any backward-looking estimator. HAR helped in development (+0.06) but not on the holdout; EWMA made no difference. **GVZ-adjusted sizing adopted (D-021).**
