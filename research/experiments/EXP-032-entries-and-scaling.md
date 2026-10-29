# EXP-032: How to enter and add: lump sum vs spreading in, adding to winners, averaging down, buying dips

| Field | |
|---|---|
| Status | Run 2026-10-29: nothing adopted; investing at once and spreading in are a coin-flip |
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

## Results (real data, 2026-10-29; `results/2026-10-29-1440-plab-core-real/` (open fills), `…-1441-plab-core-real-closefill/`, `…-1442-plab-other-real/`)
ΔSharpe vs the traded rule, pre / dev / holdout (core, open fills); close fills and other assets agree unless noted.

| Variant | Core, open | Core, close | Other assets | Verdict |
|---|---|---|---|---|
| add_to_winners | +0.02 / −0.04 / +0.01 | +0.02 / −0.06 / +0.01 | −0.02 / −0.00 / −0.01 | REJECT |
| average_down | −0.01 / +0.03 / −0.01 | 0.00 / +0.02 / −0.03 | −0.06 / +0.01 / −0.05 | INCONCLUSIVE; **deepens the worst fall** (−39.1% → −43.3%) |
| buy_pullbacks | 0.00 / −0.00 / 0.00 | 0.00 / −0.01 / −0.01 | −0.00 / −0.01 / +0.03 | REJECT |

**Lump sum vs spreading over 12 months** (3-year outcome from every monthly start): core set, 207 starts — spreading
ended ahead in 46%; average 3-year return 15.5% (lump) vs 14.6% (spread); worst 3 years −30.4% vs −27.0%; average
worst fall −18.1% vs −16.1%. Other assets, 160 starts: spreading ahead in 56%, averages 9.7% vs 9.9%.

**Conclusion:** because the strategy already sizes by risk, how money goes in matters little. Investing at once
earns slightly more on average; spreading in slightly softens the worst cases. Adding to winners and buying dips do
nothing; averaging down adds tail risk for no reliable gain, so it is rejected under the rule fixed in advance.
