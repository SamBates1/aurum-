# EXP-020: Longer history: does the traded strategy survive 2006–2013?

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, before any lab result on real data |
| Origin | Owner's request (stage A): test on bad times, not only on the period used so far |

## Hypothesis
The traded strategy (`vol_hold_gvz`) behaves on 2006-06 → 2013-10, data no earlier experiment used, as it did later:
smaller falls than buy & hold for a similar or better return per unit of risk. That period contains the 2008 crash,
gold's 2011 peak and the 2013 crash, so it is a stress test.

## Variants (fixed before running)
`vol_hold_gvz` (traded); references `buy_hold` and `vol_hold_21d` (sizing without GVZ). GVZ exists only from June
2008; before that the traded rule falls back to plain 21-day volatility, exactly as the live bot does.
WPM traded as Silver Wheaton (SLW) before 2017; Yahoo's adjusted history under WPM is used.

## Acceptance criteria
On the pre-2013 period, portfolio level, net of costs:
1. max drawdown at least 30% smaller than buy & hold's;
2. Sharpe no worse than buy & hold's minus 0.10;
3. a smaller loss than buy & hold in each stress window that falls in the data (2008 crisis, 2011–15 bear market, 2013 crash).
**D-021 check:** on 2008-06 → 2013-10, `vol_hold_gvz` vs `vol_hold_21d`: ΔSharpe ≥ 0 and volatility-adjusted drawdown
no worse. If it fails, D-021 is flagged for review (not reversed automatically).
If 1–3 fail, the strategy's protection is recorded as specific to 2013–2026, and the risk map (EXP-028) must use the
pre-2013 numbers when the owner chooses a risk level.

Lab rules (README, 'Research lab'); run with `python run_lab.py --set core` (and `--fill close`, `--set other`).

## Results
_Not yet run on real data._
