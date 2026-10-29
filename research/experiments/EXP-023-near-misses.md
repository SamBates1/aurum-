# EXP-023: Near-misses re-tested on the traded strategy

| Field | |
|---|---|
| Status | Run 2026-10-29: miner tilt inconclusive again; chandelier stop **rejected** (closes EXP-009) |
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

## Results (real data, 2026-10-29; `results/2026-10-29-1337-lab-core-real/`, `…-1337-lab-core-real-closefill/`, `…-1332-lab-other-real/`)
ΔSharpe vs the traded strategy, pre / dev / holdout (share of resamples better in dev), DSR:

| Variant | Core, open fills | Core, close fills | Other assets | Verdict |
|---|---|---|---|---|
| miner_gdx_tilt | −0.01 / +0.08 (100%) / +0.06, DSR 0.80 | −0.01 / +0.07 / +0.06 | +0.01 / −0.03 / +0.05 | INCONCLUSIVE |
| chandelier_3atr | −0.02 / −0.03 / −0.26 | +0.02 / −0.07 / −0.16 | +0.16 / −0.09 / +0.06 | REJECT |

The miner tilt is the most consistent small effect found so far in development (better in 100% of resamples) but is
below the +0.10 bar, does not help before 2013, and is negative on the other miners: not adopted. The chandelier
stop cuts drawdowns but costs too much return; with EXP-005's result this closes EXP-009.
