# EXP-024: Gold fair value from real yields and the dollar

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, before any lab result on real data |
| Origin | Stage 5; Erb & Harvey (2013) [S6]; the real-yield link broke after 2021 |

## Hypothesis
When gold is expensive relative to what real interest rates and the dollar imply, its next months are weaker (and vice
versa), so holding a little less when it is "rich" improves risk-adjusted return.

## Model (fixed before running)
log(gold futures) = a + b × 10-year TIPS real yield + c × log(dollar index), fitted by least squares on the last
756 trading days (`fv_rolling`) or on all history so far (`fv_expanding`, minimum 756 days), refitted every 21 days
using only data known on the fitting date (FRED lagged 2 business days). z = (actual − fitted) / residual standard
deviation. Weight × (1 − 0.25 × clip(z/2, −1, 1)): up to 25% less at z = +2, up to 25% more at z = −2 (capped at full
investment, so for low-volatility assets the upward tilt is often limited). Applied to every asset.

## Acceptance criteria
Lab rules plus EXP-021 criterion 2.

## Main risk
After 2021, central-bank buying broke the real-yield relationship; a rolling fit adapts, an expanding one does not.
If only the rolling version works, record why.

Lab rules (README, 'Research lab'); run with `python run_lab.py --set core` (and `--fill close`, `--set other`).

## Results
_Not yet run on real data._
