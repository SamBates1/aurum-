# EXP-045: Is "S&P 500 + gold" robust, and can it be protected in economic downturns?

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29 22:25, before running; follows EXP-037 (where 70/30 SPY/GLD stood out **after** results were seen) |
| Origin | Owner: wants profit (S&P-like return) and protection in an economic decline |

## Why this test exists
In EXP-037, 70% SPY + 30% GLD matched the S&P 500's return with less risk. It was one of 13 variants and was singled out
after seeing results, so it must be rechecked fairly before anyone relies on it.

## Variants (fixed before running)
- Benchmark: SPY buy & hold.
- Mixes of SPY and GLD, rebalanced on the first trading day of each month: 90/10, 80/20, 70/30, 60/40, 50/50.
- 70/30 rebalanced quarterly, yearly, or whenever a weight drifts more than 5 points (checked daily).
- SPY 60% / GLD 25% / IEF 15% (adds Treasuries, monthly).
- Downturn protection on 70/30: (a) **risk cap**: each sleeve × min(1, 20% / its 21-day volatility), the rest in cash;
  (b) **trend filter**: the SPY sleeve goes to cash while SPY is below its 200-day average.
- Reference: SPY 70% + the adopted Aurum strategy 30%.
All run with next-open fills and again with next-close fills; costs SPY 2, GLD 3, IEF 3 bps.

## Pre-registered tests
1. **Robust mix:** every mix from 80/20 to 60/40 has a higher Sharpe than SPY over the whole period **and** in at least
   two of the three periods (pre, dev, holdout); and 70/30's higher Sharpe holds with quarterly and yearly rebalancing
   and with close fills.
2. **Profit:** 70/30's whole-period CAGR within 1 percentage point of SPY's.
3. **Downturn protection:** a protection variant is useful if it loses less than plain 70/30 in **each** downturn window
   (2007-12 → 2009-06 and 2020-02 → 2020-04 US recessions; 2022 rate rises) **and** gives up no more than 1 percentage
   point a year of whole-period CAGR versus plain 70/30.

Reported also: calendar-year returns, rolling 3-year returns vs SPY, worst fall and recovery time.

## Results
_Not yet run on real data._
