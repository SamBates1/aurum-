# EXP-035: Risk levels and robustness of the current settings

| Field | |
|---|---|
| Status | Run 2026-10-29: current settings sit in a flat region; one-account engine adopted as standard (D-028) |
| Origin | Owner's brief §3, §8 |

## What is produced (descriptive; nothing is selected by the code)
- Conservative (10%), moderate (15%, current) and aggressive (20%) volatility targets in one account.
- A **robustness grid**: Sharpe and return for volatility target 10–20% × rebalance band 0/2.5/5/10 points ×
  volatility window 10/21/63 days. The current setting should sit in a flat region; if it sits on a peak surrounded
  by much worse values, that is evidence of luck and is recorded.
- **Cost sensitivity**: 0, 5, 10, 25 and 50 bps one-way on every asset.
- Daily rebalancing (owner's choice, D-027) vs Fridays only, and the new one-account engine vs the old sleeve engine.

## Rule (fixed before running)
The one-account engine becomes the standard backtest because it is how the paper trader and a broker account work
(same rule everywhere, D-005). The difference from the sleeve engine is reported; if it is larger than 0.05 Sharpe in
any period, earlier sleeve-based headline numbers are restated.

Portfolio-lab rules (README, 'Portfolio lab'); run with `python run_plab.py --set core` (and `--fill close`, `--set other`).

## Results (real data, 2026-10-29; `results/2026-10-29-1440-plab-core-real/` (open fills), `…-1441-plab-core-real-closefill/`, `…-1442-plab-other-real/`)
**One-account engine vs sleeve engine** (same rule): ΔSharpe −0.04 / 0.00 / −0.04 (core, open), −0.03 / +0.01 / −0.03
(close), −0.04 / −0.02 / +0.08 (other assets): within the 0.05 threshold except the other set's holdout. Earlier
headline numbers stand; the one-account engine becomes the standard (D-028) because it is how the bot trades.

**Daily vs Friday-only decisions:** ΔSharpe (weekly vs daily) −0.03 / +0.02 / +0.02 (open), +0.01 / +0.01 / +0.05
(close): equivalent, as in EXP-022. Daily kept at the owner's choice (D-027).

**Robustness grid** (whole period Sharpe, core, open fills): every combination of target 10–20%, band 0–10 points
and 21-day volatility lies between 0.36 and 0.40; with 10-day volatility 0.33–0.37; with 63-day volatility 0.37–0.42.
The current setting (15%, 5 points, 21 days: 0.37) is in the middle of a flat region, not on a lucky peak. The
slightly better 63-day window is **not** adopted: picking the best cell of a grid is exactly the selection the rules
forbid, and the gain (≈ +0.03) is within noise.

**Risk levels (one account, whole period):** conservative 10%: 4.4% a year, worst fall −28.0%; moderate 15%
(current): 5.5%, −39.1%; aggressive 20%: 6.4%, −47.6%; all Sharpe 0.37.

**Costs** (same one-way cost on every asset, whole period): 0 bps 5.7% / 0.38; 10 bps 5.4% / 0.36; 25 bps 4.9% /
0.32; 50 bps 4.1% / 0.26. The strategy survives realistic costs; costs above ~25 bps would erode it materially.
