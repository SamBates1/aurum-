# EXP-051a (price signals) results: stock signals vs holding every stock equally

Run 2026-10-30 19:45 UTC. 1000 stocks with prices (2016-01-04 00:00:00 to 2026-10-30 00:00:00), Alpaca SIP daily, adjusted. SEC accounts found for 0 companies (0 failed). Tests from 2017 (one year of history first).

**Survivorship bias:** today's survivors only; long-only results are flattered. The pass bar is 3% a year.

| Signal | Family | Extra return / yr after costs | NW t | 2017-20 | 2021-26 | 2024+ | Turnover / period | Verdict |
|---|---|---|---|---|---|---|---|---|
| momentum | long-term | +6.4% | 1.98 | +11.4% | +2.9% | +11.0% | 0.45 | **FAIL** |
| low_volatility | long-term | -4.2% | -0.74 | -11.3% | +0.7% | -15.8% | 0.13 | **FAIL** |
| near_52w_high | long-term | -0.5% | -0.09 | -7.1% | +4.2% | -3.9% | 0.99 | **FAIL** |
| short_term_reversal | swing | +4.1% | 1.39 | +3.6% | +4.5% | +1.7% | 0.37 | **FAIL** |
| breakout | swing | +0.2% | 0.05 | -7.2% | +5.3% | +10.1% | 0.46 | **FAIL** |
| pullback_in_uptrend | swing | -9.6% | -2.42 | -11.2% | -8.5% | -9.2% | 0.46 | **FAIL** |
| trend_strength | swing | +10.6% | 1.63 | +15.7% | +7.1% | +19.9% | 0.34 | **FAIL** |

Pass rule (pre-registered): extra return at least 3% a year after costs, Newey-West t at least 2, positive in both halves and since 2024, and a Benjamini-Hochberg discovery at 10% across all signals.

Run time 312s.
