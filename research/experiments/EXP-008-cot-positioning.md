# EXP-008: CFTC positioning (designed, not coded)

| Field | |
|---|---|
| Status | Designed, not coded |
| Origin | CFTC Commitments of Traders [S15]. |
| Current Aurum equivalent | No positioning data in Aurum. |

## Hypothesis
Extreme speculative positioning in gold futures predicts weaker subsequent gold returns (crowding), information not contained in prices.

## Variants (fixed before running)
Feature: z-score of managed-money net long as % of open interest (disaggregated report), aligned to the **Friday 15:30 ET release**, not the Tuesday as-of date; usable from the following Monday's decision. Variant: add to features (ML) and as an entry gate (top-decile crowding).

## Acceptance criteria
Standard rules; plus check the feature isn't redundant with 63-day momentum (correlation and ablation). See [README](README.md#acceptance-criteria-applied-automatically-by-run_experimentspyverdict).

## Main risks and limitations
Needs a historical CFTC download and parser; holiday-shifted release dates must be handled.

## Results
_Not yet run on real data._ After `python run_experiments.py`, copy the rows for this experiment from
`results/<date>-real/summary.md` here, with the verdict and any decision recorded in `../decisions.md`.
