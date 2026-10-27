# EXP-007: Triple-barrier labels and trade-plan exits

| Field | |
|---|---|
| Status | Pre-registered 2026-10-27, awaiting a real-data run |
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

## Results
_Not yet run on real data._ After `python run_experiments.py`, copy the rows for this experiment from
`results/<date>-real/summary.md` here, with the verdict and any decision recorded in `../decisions.md`.
