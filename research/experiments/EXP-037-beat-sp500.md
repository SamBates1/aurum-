# EXP-037: Can Aurum-style portfolios beat the S&P 500?

| Field | |
|---|---|
| Status | Run 2026-10-29: **nothing beat the S&P 500**; SPY 70% + GLD 30% matched its return with less risk |
| Origin | Owner: 'I want this bot to be more profitable than the S&P 500' |

## Variants (fixed before running)
SPY buy & hold (benchmark); the adopted Aurum strategy (core set) held as a fund; 60/40 SPY/IEF; SPY + Aurum at 80/20,
70/30, 60/40 and SPY + GLD 70/30, all rebalanced on the first trading day of each month; Aurum's volatility rule on seven
assets (SPY, EFA, TLT, IEF, GLD, DBC, GDX; equal sleeves, 15% / 21-day vol); risk parity (inverse 63-day volatility
across SPY, EFA, TLT, IEF, GLD, DBC, scaled to 10% forecast portfolio volatility with a 126-day covariance, monthly);
risk parity levered 1.25×, 1.5× and 2× and the seven-asset rule levered 1.5×, with borrowing charged at T-bill + 1.5%
a year (sensitivity: T-bill + 3%).

## Pre-registered test
A variant **beats the S&P 500** only if its CAGR (net of costs and financing) is higher than SPY's in **every** period
(pre, dev, holdout) and over the whole sample, **and** its whole-sample worst fall is no deeper than SPY's. A variant
with a higher Sharpe ratio but lower CAGR is reported as "higher return per unit of risk, lower return".
Leverage is **not** enabled in Aurum by this experiment; borrowing needs the owner's explicit approval (and a margin
account), so any leverage result is research only.

Cross-asset lab rules (README, 'Cross-asset lab'): universe SPY, QQQ, IWM, EFA, TLT, IEF, GLD, SLV, GDX, DBC (CPER excluded: data audit found paired ±30–50% bad prints in 2014–15); costs SPY/QQQ 2, IWM/EFA/TLT/IEF/GLD 3, SLV/GDX 5, DBC 8 bps one way; one account, next-open fills, T-bill on cash; periods pre (to 2013-10-17), dev (to 2023), holdout (2024+); figures in each result folder's `figures/`.

## Results (real data, 2026-10-29; `results/2026-10-29-2126-xlab-sp500-real/` (summary.md, CSVs, figures/))
Whole period 2006-06-30 → 2026-10-29, net of costs and financing:

| Strategy | CAGR | Sharpe | Volatility | Max DD | Longest drawdown | Verdict (pre-registered) |
|---|---|---|---|---|---|---|
| SPY buy & hold | 11.3% | 0.56 | 19.3% | −55.2% | 1,223 days | benchmark |
| Aurum (adopted, core) | 5.5% | 0.37 | 12.1% | −39.1% | 2,239 days | does not beat SPY |
| 60/40 SPY/IEF | 8.5% | 0.66 | 10.8% | −32.3% | 709 days | higher return per unit of risk, lower return |
| SPY 80% + Aurum 20% | 10.4% | 0.60 | 16.0% | −46.4% | 839 days | higher return per unit of risk, lower return |
| SPY 70% + Aurum 30% | 9.9% | 0.61 | 14.5% | −41.8% | 790 days | higher return per unit of risk, lower return |
| SPY 60% + Aurum 40% | 9.4% | 0.62 | 13.3% | −37.0% | 757 days | higher return per unit of risk, lower return |
| **SPY 70% + GLD 30%** | **11.3%** | **0.69** | 14.8% | **−38.5%** | **612 days** | higher return per unit of risk, same return (not "beats": lower CAGR in 2013–23) |
| Aurum rule on 7 assets | 5.4% | 0.51 | 7.6% | −17.0% | 1,237 days | does not beat SPY |
| Risk parity 10% vol | 5.7% | 0.59 | 7.0% | −17.5% | 630 days | higher return per unit of risk, lower return |
| Risk parity ×1.25 / ×1.5 / ×2 (T-bill + 1.5%) | 6.3% / 6.8% / 7.8% | 0.55 / 0.52 / 0.49 | | −22.0% / −26.3% / −34.3% | | does not beat SPY |
| Aurum rule on 7 assets ×1.5 | 6.6% | 0.48 | 11.4% | −26.1% | 1,325 days | does not beat SPY |

**Conclusions:**
1. No variant met the pre-registered test (higher CAGR than SPY in every period with no deeper worst fall).
2. **Leverage did not help**: risk parity's Sharpe (0.59) is about SPY's (0.56), and borrowing costs more than the
   extra return, so 2× leverage reached only 7.8% a year with a −34% worst fall. Most of risk parity's weakness is
   2013–2023 (3.3% a year: bonds and commodities lagged, then 2022 hit stocks and bonds together).
3. **Adding gold to shares works as diversification**: 70% SPY + 30% GLD earned the same 11.3% a year with a higher Sharpe
   (0.69 vs 0.56, better in 93% of resamples), a worst fall of −38% instead of −55%, and half the longest drawdown.
   Adding the Aurum strategy instead of plain gold also raised Sharpe slightly but cost return, because Aurum holds
   gold assets only about half the time on average.
4. Beating the S&P 500's return over 2006–2026 was not achieved by any tested approach that respects the drawdown
   limit. That does not prove it is impossible, but it means there is no evidence-based way to promise it.

**Close-fill check (D-018):** the first attempt (`results/2026-10-29-2227-xlab-sp500-real-closefill/`) is **invalid**: a bug meant the ETF legs still filled at the open (only the Aurum leg used closes). Fixed with a regression test and re-run; see below.
