# EXP-047: 70/30 over 1972-2026, not just 2006-2026

| Field | |
|---|---|
| Status | Pre-registered 2026-10-30 10:55 UK, before running |
| Origin | The daily data start in 2006, so every earlier test saw one big crash (2008). Is 70/30's protection reliable? |

## Method (fixed before running)
- Monthly data from January 1972 (gold has floated freely since August 1971): S&P 500 total return (Shiller data via
  github.com/datasets/s-and-p-500: monthly average prices plus dividends; dividends after mid-2023 use the last known
  yield), gold (World Bank monthly average, github.com/datasets/gold-prices), pounds per dollar (github.com/datasets/
  exchange-rates), 3-month T-bill (FRED TB3MS) and UK 3-month rate (FRED IR3TIB01GBM156N; earlier months use the first
  available value).
- Strategies: 100% S&P, 70/30 rebalanced monthly, 100% gold; costs 0.10% per trade and modern fund fees (S&P 0.2%,
  gold 0.25% a year). In dollars and in pounds.
- Caveats stated up front: monthly AVERAGE prices smooth out falls inside a month, so worst falls look smaller than
  daily data would show (measured by repeating the test on 2006-2026 and comparing with the daily results); gold funds
  did not exist before 2004.

## Pre-registered tests
1. **Protection is reliable:** 70/30 falls less than the S&P in EVERY S&P bear market in the sample (1973-74, 1980-82,
   1987, 2000-02, 2007-09, 2020, 2022).
2. **Better risk-adjusted:** 70/30's Sharpe is higher than the S&P's over the whole period and in at least two of the
   three sub-periods 1972-1989, 1990-2007, 2008-2026.
3. **Better worst decade:** 70/30's worst rolling 10-year return is higher than the S&P's.
Reported also: CAGR gap, decade-by-decade returns, share of 10-year periods where 70/30 beat the S&P.

## Results (real data; `results/2026-10-30-1134-uk-real/`)
**Test 1 FAILS, tests 2 and 3 PASS** (same verdicts in dollars and pounds).
- 70/30 fell less than the S&P in 6 of 7 bear markets. The exception is **1980-82**: gold crashed from its 1980 peak,
  so 70/30 lost −21% (in dollars) while the S&P lost −12%.
- Whole period 1972-2026 (dollars, monthly averages): S&P 11.0% a year, worst fall −49%; 70/30 10.7% a year, worst
  fall −33%. In pounds: S&P 12.3%, 70/30 12.0%.
- Sharpe higher for 70/30 in 1972-1989 and 2008-2026, slightly lower in 1990-2007 (the gold bear market).
- Worst 10-year return a year: S&P −3.7%, 70/30 +1.3%. But 70/30 beat the S&P in only 31% of 10-year periods: in the
  1980s and 1990s holding only the S&P made far more.
- Monthly averages understate falls: over 2006-2026 they show −49% / −33% where daily data show −55% / −38.5%.
