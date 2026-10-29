# EXP-035: Risk levels and robustness of the current settings

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, before any portfolio-lab result on real data |
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

## Results
_Not yet run on real data._
