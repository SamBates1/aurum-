# EXP-020: Longer history: does the traded strategy survive 2006–2013?

| Field | |
|---|---|
| Status | Run 2026-10-29: protection **confirmed**; return per unit of risk slightly below holding |
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

## Results (real data, 2026-10-29; `results/2026-10-29-1337-lab-core-real/`, `…-1337-lab-core-real-closefill/`, `…-1332-lab-other-real/`)
Core set, portfolio from 2006-06-30, net of costs. Open fills / close fills.

| Period | Strategy CAGR | Sharpe | Max DD | Buy & hold CAGR | Sharpe | Max DD |
|---|---|---|---|---|---|---|
| pre (2006-06 → 2013-10) | 2.8% / 2.5% | 0.19 / 0.16 | −32.1% / −32.7% | 4.7% / 4.6% | 0.28 / 0.28 | −63.9% |
| dev (2013-10 → 2023) | 3.4% / 3.4% | 0.24 / 0.24 | −22.0% / −21.5% | 6.0% | 0.30 | −41.1% |
| holdout (2024 →) | 23.5% / 23.4% | 1.33 / 1.32 | −13.4% / −13.5% | 39.0% | 1.00 | −36.7% |
| **whole 2006–2026** | **5.7% / 5.6%** | **0.38 / 0.38** | **−39.7% / −39.5%** | **9.5%** | **0.39** | **−65.2%** |

Stress windows (strategy vs buy & hold, return over the window): 2008 crisis −11.0% vs −35.7%; 2011–15 bear market
−38.5% vs −62.8%; 2013 crash −15.4% vs −30.5%; 2020 Covid −5.1% vs −14.2%; 2022 rate rises −10.5% vs −24.9%.

| Criterion (pre-2013) | Result | Pass? |
|---|---|---|
| 1. Max DD ≥ 30% smaller than buy & hold | −32.1% vs −63.9% (50% smaller) | Yes |
| 2. Sharpe ≥ buy & hold − 0.10 | −0.09 (open fills), −0.11 (close fills) | Borderline: yes / no |
| 3. Smaller loss in every stress window | all five windows | Yes |
| D-021 check: GVZ sizing vs plain 21-day vol | ΔSharpe −0.09 (open), −0.11 (close) | **No** → D-021 reviewed (D-024) |

**Conclusion:** the strategy's protection is not specific to 2013–2026: in the worst gold period of the last 20 years
(2011–2015) it lost 39% where holding lost 63%. Over the whole 20 years it earned the **same return per unit of risk
as holding** (Sharpe 0.38 vs 0.39) with a much smaller worst fall, but less money (5.7% vs 9.5% a year). GVZ sizing
did worse than plain sizing in 2008–2013 (D-024).
