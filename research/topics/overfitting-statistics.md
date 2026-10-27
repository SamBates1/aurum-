# Statistics for honest backtests

Status: implemented in `aurum/stats.py` (2026-10-27).

| Tool | What it answers | Implementation |
|---|---|---|
| Stationary block bootstrap (Politis & Romano 1994) | How uncertain is a Sharpe ratio, or a Sharpe *difference*, when returns are autocorrelated? | `bootstrap_sharpe` |
| Probabilistic Sharpe Ratio (Bailey & López de Prado 2012) | Probability the true Sharpe exceeds a benchmark, given sample length, skew and kurtosis | `probabilistic_sharpe` |
| Expected maximum Sharpe ("False Strategy Theorem") | How good the best of N zero-skill strategies looks by luck | `expected_max_sharpe` |
| Deflated Sharpe Ratio (Bailey & López de Prado 2014) [S12] | PSR against that luck-adjusted hurdle, using all trials run | `deflated_sharpe` |
| PBO via CSCV (Bailey, Borwein, López de Prado & Zhu 2017) [S13] | How often the in-sample winner falls below median out of sample | `probability_of_backtest_overfitting` |

## Formulas (per-period Sharpe `SR`, `T` observations, skew `γ3`, non-excess kurtosis `γ4`)
- PSR(SR*) = Φ( (SR − SR*) √(T−1) / √(1 − γ3·SR + (γ4−1)/4 · SR²) )
- E[max SR] ≈ √Var(SR_trials) · ( (1−γ)·Φ⁻¹(1 − 1/N) + γ·Φ⁻¹(1 − 1/(N·e)) ), γ = Euler–Mascheroni constant
- DSR = PSR(E[max SR])
- CSCV: split the sample into S blocks; for each of the C(S, S/2) ways to pick half as in-sample, take the
  in-sample best variant, find its out-of-sample relative rank ω, and record logit(ω). PBO = share of logits ≤ 0.

Implemented independently from the papers (VectorBT has a DSR function, but its licence includes the Commons
Clause, so no code was copied). Unit tests check that DSR < PSR for a selected-from-many strategy, that PBO is
near 0.5 for pure noise and near 0 when one variant has a real edge.

## How Aurum uses them
- Every experiment run reports DSR for each variant using *all* variants tried as the trial set, and PBO
  across variants. Acceptance requires DSR ≥ 0.5 ([../experiments/README.md](../experiments/README.md)).
- Caveat: N is the number of variants in this registry. Earlier informal choices (thresholds, features)
  are extra, unrecorded trials, so the true DSR is somewhat lower than reported.
