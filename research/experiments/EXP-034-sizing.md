# EXP-034: How much to invest: sizing and allocation frameworks

| Field | |
|---|---|
| Status | Run 2026-10-29: nothing adopted; volatility sizing trades a little Sharpe for much smaller falls |
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

## Results (real data, 2026-10-29; `results/2026-10-29-1440-plab-core-real/` (open fills), `…-1441-plab-core-real-closefill/`, `…-1442-plab-other-real/`)
| Variant | Core, open: pre / dev / holdout ΔSharpe | Core, close | Other assets | Whole period CAGR / Sharpe / max DD | Verdict |
|---|---|---|---|---|---|
| traded (reference) | – | – | – | 5.5% / 0.37 / −39.1% | baseline |
| fixed_weights (60% of sleeve) | +0.12 / +0.10 / −0.24 | +0.14 / +0.10 / −0.23 | +0.20 / +0.15 / −0.15 | 8.3% / 0.41 / −45.8% | REJECT (failed on holdout) |
| inverse_vol_alloc | −0.00 / +0.00 / +0.00 | 0.00 / −0.01 / 0.00 | 0.00 / 0.00 / +0.01 | 5.5% / 0.37 / −38.9% | INCONCLUSIVE |
| portfolio_vol_12 | +0.02 / −0.02 / +0.01 | +0.05 / −0.04 / +0.02 | −0.11 / +0.02 / +0.08 | 5.4% / 0.35 / −39.5% | REJECT |
| miners_cap_40 | −0.00 / +0.00 / +0.00 | 0.00 / −0.00 / 0.00 | +0.01 / +0.01 / 0.00 | 5.5% / 0.37 / −39.0% | INCONCLUSIVE |
| cash_reserve_10 | +0.00 / +0.01 / −0.01 | −0.00 / −0.01 / +0.01 | −0.00 / −0.00 / +0.00 | 5.2% / 0.37 / −35.4% | INCONCLUSIVE |
| fixed_fractional_atr (0.5% risk, 2-ATR stop) | −0.01 / −0.20 / −0.09 | −0.27 / −0.24 / −0.06 | +0.19 / −0.09 / +0.10 | 4.0% / 0.26 / −27.7% | REJECT |

**Conclusions:**
1. **Fixed weights beat volatility sizing on Sharpe in 2006–2023 on both asset sets** (signal path met in
   development, DSR 0.69), then lost badly in 2024–2026. Under the rule fixed in advance it is rejected. The honest
   reading: volatility sizing does **not** raise return per unit of risk; its value is smaller worst falls
   (−39% vs −46%, and much smaller in single crashes). This is consistent with the literature that volatility
   targeting helps equities more than commodities [S7].
2. Miners cap at 40% almost never binds: volatility sizing already keeps the four miners' combined weight low.
3. Allocation by inverse volatility, or targeting portfolio volatility with correlations, changes nothing: the
   per-asset rule already does the work.
4. The classic "risk x% per trade to a stop" formula is worse because it needs a stop, and stops hurt here.
