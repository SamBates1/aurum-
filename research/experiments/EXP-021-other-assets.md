# EXP-021: Out-of-asset confirmation: eight precious-metal assets never tested

| Field | |
|---|---|
| Status | Run 2026-10-29: protection confirmed on new assets; GVZ sizing confirmed; no tilt confirmed |
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

## Results (real data, 2026-10-29; `results/2026-10-29-1332-lab-other-real/`, open fills)
Eight assets, portfolio from 2010-05-19. PBO across the 8 trial variants: 88% (the ranking of ideas does not repeat
between halves of the history: little real difference between them).

| Period | Strategy CAGR / Sharpe / Max DD | Buy & hold CAGR / Sharpe / Max DD |
|---|---|---|
| pre (2010-05 → 2013-10) | −2.8% / −0.21 / −27.8% | −3.7% / 0.02 / −51.3% |
| dev | 2.5% / 0.17 / −26.3% | 5.6% / 0.29 / −49.4% |
| holdout | 17.8% / 1.03 / −12.5% | 30.4% / 0.84 / −34.3% |
| whole 2010–2026 | 3.8% / 0.26 / −36.7% | 7.3% / 0.34 / −62.5% |

1. **Strategy vs buy & hold:** max DD 41% smaller over the whole period (yes); Sharpe −0.08 (yes, within 0.10), though
   −0.23 in the short pre period and −0.12 in development.
2. **Tilts:** none had ΔSharpe ≥ 0 in two of three periods *and* a pass in the core set; none is confirmed.
3. **GVZ vs plain 21-day vol:** whole-period Sharpe 0.26 vs 0.19 (dev +0.09, holdout +0.06, pre −0.09): **passes**.

**Conclusion:** the "smaller falls" result generalises to assets the strategy never saw; the higher returns of the
2024–2026 period are mostly gold's bull market.
