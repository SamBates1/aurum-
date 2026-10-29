# EXP-032: How to enter and add: lump sum vs spreading in, adding to winners, averaging down, buying dips

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, before any portfolio-lab result on real data |
| Origin | Owner's brief (2026-10-29) §2, §3, §5 |

## Hypotheses and variants (fixed before running)
All are changes to the traded rule's target weight per asset; ×1.25 is the single pre-set size of every "add", and no
asset ever exceeds its full sleeve (no borrowing, no unlimited averaging down, no martingale).
- `dca_12m` (descriptive): put the starting capital in over 12 monthly steps instead of at once. Judged mainly by the
  **rolling-start study**: from every monthly start date, 3-year outcome of spreading vs investing at once.
  Prior evidence (Vanguard, 2012 [S34], and standard theory): investing at once wins about two-thirds of the time when
  expected returns are positive, while spreading reduces regret.
- `add_to_winners` (pyramiding): ×1.25 while above the 200-day average and up over 3 months.
- `average_down`: ×1.25 while more than 15% below the 1-year high (one addition only).
- `buy_pullbacks`: ×1.25 while in an uptrend (above the 200-day average) after a 10-day fall bigger than one
  10-day standard deviation.

## Acceptance criteria
Lab rules (signal or risk path in development, 2× costs, DSR ≥ 0.5; must hold on holdout **and** pre-2013), plus the
out-of-asset check (other set: ΔSharpe ≥ 0 in at least two of three periods). For `average_down`, also report whether
it deepens the worst fall: a pass on Sharpe with a deeper worst fall in any period is recorded as "increases tail risk"
and not adopted.

Portfolio-lab rules (README, 'Portfolio lab'); run with `python run_plab.py --set core` (and `--fill close`, `--set other`).

## Results
_Not yet run on real data._
