# EXP-034: How much to invest: sizing and allocation frameworks

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, before any portfolio-lab result on real data |
| Origin | Owner's brief §3 |

## Variants (fixed before running)
Current rule, per asset: portfolio weight = sleeve × min(1, 15% / forecast volatility), sleeve = min(20%, 1/N).
- `fixed_weights`: no volatility sizing; every asset fixed at 60% of its sleeve (a round number close to the current
  average exposure).
- `inverse_vol_alloc`: same total exposure as the traded rule each day, shared between assets in proportion to
  1 / volatility (more to calm assets, less to volatile ones).
- `portfolio_vol_12`: inverse-volatility shares scaled so the portfolio's forecast volatility (126-day covariance,
  re-estimated every 21 days) is 12%, never above full investment. Accounts for correlation between assets.
- `miners_cap_40`: GDX, NEM, AEM and WPM (miners move together) at most 40% of the account in total (now up to 67%).
- `cash_reserve_10`: every target × 0.9.
- `fixed_fractional_atr`: weight = 0.5% of the account ÷ the distance to a 2-ATR trailing stop (the classic
  "risk x% per trade" formula), with that stop active and a 10-day re-entry delay. (1% would mean full investment
  almost always, so 0.5% is used.)
Not tested: Kelly sizing (needs a reliable estimate of the edge, which no tested signal provides); sizing by ML
confidence (already rejected: calibration poor, EXP-015).

## Acceptance criteria
Lab rules plus the out-of-asset check.

Portfolio-lab rules (README, 'Portfolio lab'); run with `python run_plab.py --set core` (and `--fill close`, `--set other`).

## Results
_Not yet run on real data._
