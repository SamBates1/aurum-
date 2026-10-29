# EXP-014: Always invested, sized by volatility (candidate new baseline)

| Field | |
|---|---|
| Status | Run 2026-10-29: **adopted** |
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

## Results (real data, 2026-10-29 12:46 UTC; `results/2026-10-29-1248-real-vs-vol_hold/` and `…-1251-real-closefill-vs-vol_hold/`)
16 variants tried; PBO across them 18% (open fills) / 9% (close fills): low, so the ranking of variants is fairly stable between halves of the history.

| Variant | Dev Sharpe | Dev ΔSharpe vs vol_hold | better | Holdout ΔSharpe | DSR | Verdict (open fills) | Dev ΔSharpe / verdict (close fills) |
|---|---|---|---|---|---|---|---|
| vol_hold | +0.12 | +0.00 | 0% | +0.00 | 0.51 | baseline | +0.00 / baseline |
| vol_hold_band0 | +0.12 | -0.00 | 39% | -0.02 | 0.51 | REJECT | -0.01 / REJECT |
| vol_hold_band10 | +0.12 | -0.01 | 31% | +0.04 | 0.50 | REJECT | +0.01 / INCONCLUSIVE |
| vol_hold_monthly | +0.10 | -0.02 | 36% | +0.11 | 0.49 | REJECT | -0.00 / REJECT |
| vol_hold_tv20 | +0.14 | +0.01 | 81% | -0.04 | 0.53 | INCONCLUSIVE | +0.01 / INCONCLUSIVE |

**Adoption test for `vol_hold` vs the timing strategy (pre-registered criteria):**

| | Timing (v0.2) open / close fills | vol_hold open / close fills | Buy & hold |
|---|---|---|---|
| Dev CAGR | 0.8% / 0.2% | **2.0% / 1.7%** | 6.0% |
| Dev Sharpe | −0.02 / −0.09 | **0.12 / 0.10** | 0.30 |
| Dev max drawdown | −21.4% / −20.5% | −27.8% / −28.2% (35% smaller than B&H) | −43.0% |
| Holdout CAGR | 20.8% / 21.7% | **24.6% / 25.4%** | 44.2% |
| Holdout Sharpe vs B&H | −0.15 / −0.12 | **+0.18 / +0.24** | 0 |
| Holdout max drawdown | −17.2% / −17.9% | −13.7% / −13.5% (64% smaller than B&H) | −38.0% |

All criteria met in both periods with both fills: higher CAGR and Sharpe than timing, and drawdowns more than 25%
smaller than buy & hold. **Adopted (D-020).** On the holdout it even beat buy & hold's Sharpe, though it earned
much less in absolute terms. Band width and monthly resizing made no meaningful difference (turnover-cost trade-off
is small at these costs); a 20% target gave slightly more return with deeper drawdowns (inconclusive).
