# EXP-023: Near-misses re-tested on the traded strategy

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, before any lab result on real data |
| Origin | EXP-019 (+0.09, just below the bar) and EXP-005 chandelier (failed DSR) |

## Hypotheses and variants (fixed before running)
- `miner_gdx_tilt`: single miners held at 1.5× their weight while cheap against GDX (60-day z of log ratio went
  below −2, until it is back above 0). Same rule as EXP-019, now on GVZ sizing and with pre-2013 and other-asset data.
- `chandelier_3atr`: always invested, but the sleeve goes to cash when the close falls more than 3 ATRs below the highest
  close since (re-)entry, and re-enters after 10 trading days. Same 3-ATR distance as EXP-005; the 10-day re-entry
  delay is the one fixed in EXP-013.

## Acceptance criteria
Lab rules (signal or risk path in development, DSR ≥ 0.5, then must hold on the holdout **and** pre-2013), plus
EXP-021 criterion 2. EXP-009 (chandelier confirmation on new data) is answered by this experiment.

Lab rules (README, 'Research lab'); run with `python run_lab.py --set core` (and `--fill close`, `--set other`).

## Results
_Not yet run on real data._
