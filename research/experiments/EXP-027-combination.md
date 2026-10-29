# EXP-027: Combining what passed (stage 8)

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, before any lab result on real data |
| Origin | Stage 8 |

## Rule (fixed before any stage 5–7 result)
Only tilts that are **adopted** under the lab rules and EXP-021 are combined. The combination is the product of their
multipliers on the traded weight, capped at full investment: no re-weighting, no new parameters. Run with
`python run_lab.py --set core --combine name1,name2` and the same on `--set other`.
It is adopted only if it meets the lab rules against the traded strategy **and** is not worse (ΔSharpe ≥ 0) than the
best single tilt in development and pre-2013. If no tilt passes, this experiment is not run, and that is recorded.

Lab rules (README, 'Research lab'); run with `python run_lab.py --set core` (and `--fill close`, `--set other`).

## Results
_Not yet run on real data._
