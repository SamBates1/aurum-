# EXP-024: Gold fair value from real yields and the dollar

| Field | |
|---|---|
| Status | Run 2026-10-29: inconclusive; not adopted |
| Origin | Stage 5; Erb & Harvey (2013) [S3]; the real-yield link broke after 2021 |

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

## Results (real data, 2026-10-29; `results/2026-10-29-1337-lab-core-real/`, `…-1337-lab-core-real-closefill/`, `…-1332-lab-other-real/`)
| Variant | Core, open: pre / dev / holdout ΔSharpe | Core, close | Other assets | Verdict |
|---|---|---|---|---|
| fv_rolling | −0.04 / +0.03 / −0.06 | −0.04 / +0.01 / −0.07 | 0.00 / 0.00 / −0.06 | INCONCLUSIVE |
| fv_expanding | −0.04 / +0.02 / −0.02 | −0.04 / +0.02 / −0.01 | 0.00 / +0.01 / −0.01 | INCONCLUSIVE |

A gold "fair value" from real yields and the dollar did not help: slightly positive in development, negative before
2013 and in 2024–2026. Fair-value tilts did reduce the holdout drawdown (−13.4% → −10.6%), by holding less during
gold's 2025 rally, which also cost return (23.5% → 19.0% a year).
