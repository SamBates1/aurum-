# EXP-025: Speculative positioning (CFTC Commitments of Traders)

| Field | |
|---|---|
| Status | Run 2026-10-29: contrarian inconclusive, flow rejected; not adopted |
| Origin | Stage 6; replaces EXP-008; CFTC [S15, S30]; hedging-pressure literature (Basu & Miffre 2013) [S26] |

## Data
CFTC disaggregated futures-only reports, 2006 onwards (`fut_disagg_txt_hist_2006_2016.zip` and yearly files).
COMEX gold (code 088691), silver (084691) for SLV and SIL. Managed-money net position = (long − short) / open interest.
Positions are as of Tuesday, released Friday 15:30 ET; used from the **following Monday** (report date + 4 business days).

## Two competing hypotheses (both pre-registered, both counted as trials)
- `cot_contrarian`: crowded speculative longs precede weaker returns. z = 156-week z-score of net position;
  weight × (1 − 0.25 × clip(z/2, −1, 1)).
- `cot_flow`: speculators' recent buying continues (hedging pressure / flows). z = 156-week z-score of the 4-week
  change in net position; weight × (1 + 0.25 × clip(z/2, −1, 1)).

## Acceptance criteria
Lab rules plus EXP-021 criterion 2. If both pass, that is suspicious (they are near-opposites) and neither is adopted
without explanation.

Lab rules (README, 'Research lab'); run with `python run_lab.py --set core` (and `--fill close`, `--set other`).

## Results (real data, 2026-10-29; `results/2026-10-29-1337-lab-core-real/`, `…-1337-lab-core-real-closefill/`, `…-1332-lab-other-real/`; CFTC data loaded from 2006-06-19, 1,063 weekly reports)
| Variant | Core, open: pre / dev / holdout ΔSharpe | Core, close | Other assets | Verdict |
|---|---|---|---|---|
| cot_contrarian | −0.03 / +0.02 / −0.08 | −0.03 / +0.01 / −0.09 | −0.01 / 0.00 / −0.04 | INCONCLUSIVE |
| cot_flow | +0.02 / −0.01 / +0.01 | +0.02 / −0.02 / 0.00 | −0.03 / −0.02 / +0.03 | REJECT |

Speculative positioning adds nothing measurable to the always-invested strategy in either direction.
