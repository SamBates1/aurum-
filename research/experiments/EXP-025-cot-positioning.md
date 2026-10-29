# EXP-025: Speculative positioning (CFTC Commitments of Traders)

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, before any lab result on real data |
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

## Results
_Not yet run on real data._
