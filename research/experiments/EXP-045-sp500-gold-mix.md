# EXP-045: Is "S&P 500 + gold" robust, and can it be protected in economic downturns?

| Field | |
|---|---|
| Status | Run 2026-10-29: **S&P + gold mix confirmed robust** (tests 1–2 pass, both fills); both downturn protections **fail** the strict test (risk cap: near miss) |
| Pre-registered | 2026-10-29 22:25, before running; follows EXP-037 (where 70/30 SPY/GLD stood out **after** results were seen) |
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

## Results (real data, 2026-10-29; `results/2026-10-29-2226-xlab-mix-real/` and `…-2227-xlab-mix-real-closefill/`)
Whole period 2006-06-30 → 2026-10-29, net of costs (next-open fills; close fills within ±0.01 Sharpe):

| Strategy | CAGR | Sharpe | Volatility | Worst fall | Longest drawdown | 2008–09 | 2020 | 2022 |
|---|---|---|---|---|---|---|---|---|
| SPY buy & hold | 11.3% | 0.56 | 19.3% | −55.2% | 1,223 days | −35.1% | −9.9% | −18.2% |
| SPY/GLD 90/10 | 11.3% | 0.61 | 17.5% | −49.9% | 843 days | | | |
| SPY/GLD 80/20 | 11.3% | 0.65 | 16.0% | −44.3% | 758 days | | | |
| **SPY/GLD 70/30** | **11.3%** | **0.69** | 14.8% | **−38.5%** | 612 days | −20.3% | −4.3% | −15.4% |
| SPY/GLD 60/40 | 11.1% | 0.71 | 13.9% | −35.7% | 383 days | −15.2% | −2.6% | −14.5% |
| SPY/GLD 50/50 | 11.0% | 0.71 | 13.6% | −33.0% | 428 days | | | |
| 70/30 quarterly / yearly / 5-pt band | 11.2% / 10.9% / 11.4% | 0.69 / 0.68 / 0.69 | | −38.9% / −37.9% / −38.0% | | | | |
| SPY/GLD/IEF 60/25/15 | 10.2% | 0.71 | 12.4% | −32.7% | 485 days | | | |
| 70/30 + risk cap (20% vol) | 11.0% | **0.81** | 11.8% | **−25.8%** | 510 days | −13.8% | −6.2% | −14.2% |
| 70/30 + SPY 200-day trend filter | 9.3% | 0.76 | 10.3% | −15.8% | 424 days | +0.7% | −8.7% | −9.0% |
| SPY 70% + Aurum 30% | 9.9% | 0.61 | 14.5% | −41.8% | 790 days | −23.8% | −6.2% | −14.7% |

**Pre-registered tests (same outcome with open and close fills):**
1a. Every mix from 80/20 to 60/40 beats SPY's Sharpe overall and in at least two of three periods: **PASS**.
1b. 70/30 keeps its advantage with quarterly and yearly rebalancing: **PASS**.
2. 70/30's return within 1 point of SPY's (11.3% vs 11.3%): **PASS**.
3. Risk cap: lost less than 70/30 in 2008–09 and 2022 but **more** in the 2020 crash (−6.2% vs −4.3%, too fast for a
   21-day volatility measure), costing 0.3% a year: **FAIL** (near miss: best Sharpe, 0.81, and a −26% worst fall).
   Trend filter: lost less in every downturn with close fills but costs 2.0% a year: **FAIL**.

**Conclusion:** adding 20–40% gold to the S&P 500 is a robust improvement over 2006–2026: about the same return with
a much shallower worst fall and shorter drawdowns, at every mix, rebalancing frequency and fill convention tested. It is
diversification, not prediction, and it relies on gold and shares continuing to move fairly independently. Gold here
returned roughly as much as shares over 2006–2026; if gold lags shares badly for a decade, the mix will trail the S&P.
