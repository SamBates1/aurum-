# EXP-051: Which stock signals have earned a place in the scanners?

| Field | |
|---|---|
| Status | Pre-registered 2026-10-30; amended before any run (051a / 051b). **051a run 2026-10-30: all 7 price signals FAILED**; 051b waits for SEC access |
| Origin | Market platform build plan (D-042), phase 2: scanner weights must come from evidence |

## Why this experiment, and why not EXP-050
The plan proposed EXP-050 (multi-asset mixes across the 10 ETFs). Those questions were **already answered** and are
not re-run, because re-testing them would only add trials and weaken every later Deflated Sharpe check:
risk parity in EXP-037 (Sharpe 0.59, lower return than SPY), trend filters and cross-sectional ETF momentum in EXP-038
(none adopted), inverse-volatility allocation in EXP-034 (no change), and the 70/30 mix in EXP-045 to EXP-048. The
cross-asset scanner will show those signals as context, labelled with these results.

EXP-051 tests what has never been tested here: **signals across individual US stocks**, for the long-term and swing
scanners.

## Data (fixed)
- Universe: the 1,000 largest eligible US common stocks by 20-day dollar volume in the phase 1 universe snapshot
  (ETFs excluded), daily consolidated prices from Alpaca, January 2016 to October 2026, split- and dividend-adjusted.
- Company accounts: SEC filings as known on each rebalance date (filing date on or before it).
- **Survivorship bias (stated in every result):** the universe is today's survivors. Companies that went bust or were
  taken over since 2016 are missing, which flatters every long-only result, most of all for cheap and weak companies.
  A signal must therefore clear a higher bar than usual (below).

## Long-term signals (monthly, 12-month view)
Ranked on the last trading day of each month; the top fifth held equal-weighted for one month from the next open.

| Signal | Definition |
|---|---|
| Momentum | 12-month return skipping the latest month |
| Low volatility | lowest 252-day volatility |
| Quality | return on invested capital (SEC, point-in-time) |
| Value | free-cash-flow yield (SEC free cash flow / market value) |
| Near 52-week high | close / 252-day high |
| Combined | average rank of momentum, quality and value |

## Swing signals (weekly, 4-week view)
Ranked each Friday close; the top fifth held equal-weighted for 4 weeks from the next open (overlapping cohorts).

| Signal | Definition |
|---|---|
| Short-term reversal | lowest 1-month return |
| Breakout | close at a 20-day high with volume above its 50-day average |
| Pullback in uptrend | above the 200-day average and 2-day RSI below 10 |
| Trend strength | ADX(14) above 25 and close above the 50-day average, ranked by 3-month return |

## Pass rule (all must hold)
Compared with holding **all 1,000 stocks equally** (same dates, same costs):
1. Extra return of at least **3% a year after costs** (one-way cost 10 bps for long-term, 15 bps for swing, on the
   actual turnover). The bar is 3%, not 2%, because of the survivorship bias above.
2. Newey-West t-statistic of the monthly extra return of at least **2.0**.
3. Extra return **positive in both halves** (2016-2020 and 2021-2026) and in 2024 onwards.
4. Survives the Benjamini-Hochberg false-discovery check at 10% across all 10 signals tested here.

## What the results decide
- A signal that passes gets a weight in its scanner, proportional to its t-statistic (signals that move together share
  their weight, so nothing is counted twice).
- A signal that fails is still shown on charts, labelled "tested: no evidence it helps (EXP-051)", with weight zero.
- If nothing passes, the scanners rank by the strongest signal for information only, every result says "not yet
  supported by evidence", and the experiment pots will mostly hold the benchmark or cash. That is a valid result.

## Amendment (2026-10-30 19:50 UTC, before any EXP-051 run on real data)
The SEC refused every request from GitHub's machines (HTTP 403 for six compliant request formats;
`research/universe/sec-probe.md`), so company accounts are not available yet. Rather than wait or change the test
after seeing results, the experiment is split now:
- **EXP-051a (run now):** the 7 price-based signals (momentum, low volatility, near 52-week high; short-term reversal,
  breakout, pullback in uptrend, trend strength). The Benjamini-Hochberg check runs across these 7.
- **EXP-051b (later):** quality, value and the combined signal, once SEC access works, with its own BH check across 3.
Every other rule (universe, dates, costs, the 3%-a-year bar, t >= 2, both halves and 2024+) is unchanged.

## Results: EXP-051a (real data, `results/2026-10-30-1945-factorlab-real/`)
1,000 largest eligible US stocks, Alpaca daily prices 2016-2026, tests from 2017, against holding all 1,000 equally.

| Signal | Family | Extra return / yr after costs | NW t | 2017-20 | 2021-26 | 2024+ | Verdict |
|---|---|---|---|---|---|---|---|
| Momentum | long-term | +6.4% | 1.98 | +11.4% | +2.9% | +11.0% | FAIL (t just under 2; BH) |
| Low volatility | long-term | -4.2% | -0.74 | -11.3% | +0.7% | -15.8% | FAIL |
| Near 52-week high | long-term | -0.5% | -0.09 | -7.1% | +4.2% | -3.9% | FAIL |
| Short-term reversal | swing | +4.1% | 1.39 | +3.6% | +4.5% | +1.7% | FAIL |
| Breakout | swing | +0.2% | 0.05 | -7.2% | +5.3% | +10.1% | FAIL |
| Pullback in uptrend | swing | -9.6% | -2.42 | -11.2% | -8.5% | -9.2% | FAIL (reliably harmful) |
| Trend strength | swing | +10.6% | 1.63 | +15.7% | +7.1% | +19.9% | FAIL |

**Conclusion:** no price signal earned a weight. Momentum and trend strength were positive in every period but not
strong enough to clear the pre-registered bar, which was raised to 3% a year and t >= 2 because the universe is
today's survivors (that bias flatters them further). Buying pullbacks in uptrends lost money reliably (t = -2.4), so
the swing scanner labels it as a warning, not a reason to buy. Scanner weights stay empty: every ranking is labelled
"not supported by evidence" and no assessment can say BUY. EXP-051b (quality, value, combined) waits for SEC access.
