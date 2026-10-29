# EXP-037: Can Aurum-style portfolios beat the S&P 500?

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, before any real-data run |
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

## Results
_Not yet run on real data._
