# EXP-019: Miner vs GDX relative value, rechecked

| Field | |
|---|---|
| Status | Run 2026-10-29: not adopted |
| Origin | EXP-006 looked much stronger with close fills (+0.25) than open fills (+0.08) in EXP-010: needs explaining. |

## Common setup (stages 3–4, pre-registered 2026-10-29 before any real-data run)
All variants use the new target-weight engine (`strategy.simulate_weights`): each sleeve holds a *fraction* of its
value in the asset and is resized at the next open (and, as a check, the next close: D-018) when the target moves
more than 5 points. They are compared with **`vol_hold`** (EXP-014) rather than the old timing baseline, so each
idea is judged on whether it adds anything to simply holding with volatility-based sizing. Standard acceptance
rules (registry README) apply; the trial set is all variants in this run. Run with
`python run_experiments.py --baseline vol_hold --exps EXP-014,EXP-015,EXP-016,EXP-017,EXP-018,EXP-019`.

## Hypothesis
Miners that fall far behind GDX tend to catch up; if real, the effect should appear with both fill conventions.

## Variants (fixed before running)
`miner_gdx_tilt`: for NEM, AEM, WPM, vol_hold weight × 1.5 from when the 60-day z-score of log(miner/GDX) drops below −2 until it rises above 0; ETF sleeves unchanged.

## Acceptance criteria
Standard rules vs `vol_hold`, **and** the result must have the same sign and similar size with open and close fills; otherwise it is treated as a fill artefact.

## Results (real data, 2026-10-29 12:46 UTC; `results/2026-10-29-1248-real-vs-vol_hold/` and `…-1251-real-closefill-vs-vol_hold/`)
16 variants tried; PBO across them 18% (open fills) / 9% (close fills): low, so the ranking of variants is fairly stable between halves of the history.

| Variant | Dev Sharpe | Dev ΔSharpe vs vol_hold | better | Holdout ΔSharpe | DSR | Verdict (open fills) | Dev ΔSharpe / verdict (close fills) |
|---|---|---|---|---|---|---|---|
| miner_gdx_tilt | +0.21 | +0.09 | 100% | +0.04 | 0.62 | INCONCLUSIVE | +0.09 / INCONCLUSIVE |

**Consistent but just below the bar.** On the weights engine the miner-vs-GDX tilt gave +0.09 development Sharpe with *both* fills (better in 100% of resamples), +0.04 / +0.03 on the holdout, DSR 0.62 / 0.56. The earlier fill sensitivity (EXP-010) disappears here, so the effect looks real but small. It misses the +0.10 threshold, so **not adopted**; strongest candidate for the next round, re-tested on top of the GVZ-sized strategy.
