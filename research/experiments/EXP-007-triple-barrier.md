# EXP-007: Triple-barrier labels and trade-plan exits

| Field | |
|---|---|
| Status | Run 2026-10-29 on real data: see Results |
| Origin | López de Prado, *Advances in Financial Machine Learning* (2018), ch. 3; LEAN Insights (direction + period); the user's trade-plan idea (entry, stop, target, holding period). |
| Current Aurum equivalent | The model predicts a fixed 5-day direction, but trades are held for weeks with ATR stops: the label doesn't match the trade. |

## Hypothesis
Labels that mirror the actual trade (2-ATR target, 2-ATR stop, 20-day limit) give a more useful probability, and the matching exits give a concrete, testable trade plan.

## Variants (fixed before running)
`tb_model_tb_exits` (model trained on triple-barrier labels, exits at the same barriers); ablations `tb_model_base_exits` (new labels, old exits) and `base_model_tb_exits` (old labels, new exits). Barriers fixed at 2/2 ATR and 20 days a priori. Purge and point-in-time skill use the 20-day horizon.

## Acceptance criteria
Standard rules. If kept, this becomes the basis of the trade-plan feature. See [README](README.md#acceptance-criteria-applied-automatically-by-run_experimentspyverdict).

## Main risks and limitations
Same-day touches of both barriers count as losses (pessimistic). Longer horizon = fewer independent labels.

## Results (real data, run 2026-10-29, `results/2026-10-29-real/`)
Portfolio of 6 sleeves, net of costs, vs the baseline over identical dates. Development 2013-10-18 → 2023-12-31;
holdout from 2024-01-01. 26 variants tried in total; PBO across them 77%.

| Variant | Dev Sharpe | Dev ΔSharpe | better | ΔSharpe 2× cost | Dev max DD | Holdout ΔSharpe | DSR | Verdict |
|---|---|---|---|---|---|---|---|---|
| tb_model_tb_exits | +0.06 | +0.07 | 66% | -0.04 | -10.1% | +0.21 | 0.32 | INCONCLUSIVE |
| tb_model_base_exits | +0.13 | +0.14 | 87% | +0.13 | -13.2% | -0.10 | 0.40 | INCONCLUSIVE |
| base_model_tb_exits | -0.14 | -0.13 | 16% | -0.23 | -16.5% | +0.01 | 0.14 | REJECT |

Training the model on triple-barrier labels helped in development (+0.14, 87% of resamples) but not on the holdout (−0.10). Adding barrier exits to the baseline model was rejected. With barrier labels and exits combined: +0.07 development, +0.21 holdout, but it turns negative at 2× costs. **Conclusion: not adopted. The trade-plan idea (D-015) should not yet rely on fixed 2-ATR targets and 20-day exits.**
