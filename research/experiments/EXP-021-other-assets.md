# EXP-021: Out-of-asset confirmation: eight precious-metal assets never tested

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, before any lab result on real data |
| Origin | Stage A: an idea that works only on our six tickers is probably luck |

## Hypothesis
Everything the lab tests (the traded strategy and every stage 5–8 tilt) behaves the same on precious-metal assets
never used before: GDXJ (junior miners), SIL (silver miners), RGLD and FNV (royalty companies), KGC and AU (miners),
PPLT and PALL (platinum, palladium). Common start 2010 (SIL/PPLT/PALL), so the "pre" period is 2010–2013 only.
Costs: the default 10 bps each way (assumption: these trade less than GLD). Positioning signals use gold COT, silver
COT for SIL; news-risk tilts (EXP-026) apply only to GLD/SLV so are not tested here.

## Acceptance criteria
1. The traded strategy vs buy & hold on this set: same tests 1–2 as EXP-020, full period.
2. **Required for adopting any tilt:** on this set, the tilt's ΔSharpe vs the traded strategy is ≥ 0 in at least
   two of the three periods (pre, dev, holdout).
3. GVZ sizing vs plain 21-day vol on this set: ΔSharpe ≥ 0 (second D-021 check).

Lab rules (README, 'Research lab'); run with `python run_lab.py --set core` (and `--fill close`, `--set other`).

## Results
_Not yet run on real data._
