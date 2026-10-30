# EXP-046: 70/30 re-tested as a UK investor (pounds, UK funds, real fees)

| Field | |
|---|---|
| Status | Pre-registered 2026-10-30 10:55 UK, before running |
| Origin | Owner (D-036): will invest in pounds through UK-listed funds; every earlier test was in US dollars on US ETFs |

## Question
What would the owner actually have experienced, in pounds, holding the UK funds (VUSA for the S&P 500, SGLN for gold)
inside an ISA (no UK tax), after fund fees, dividend withholding and a platform fee?

## Method (fixed before running)
- Daily data 2006-06-01 → latest: SPY and GLD adjusted prices (Yahoo) converted to pounds with GBP/USD (Yahoo
  `GBPUSD=X`, the rate known at each US close). The strategy's decisions still come from the US prices, exactly as the
  Decision Board and paper trader make them; only the accounting is in pounds.
- UK fund costs relative to the US ETFs, as a daily drag: S&P fund +0.22% a year (VUSA 0.07% fee + 15% US withholding
  on a ~1.6% dividend yield, minus SPY's 0.0945% fee already in its price); gold fund −0.28% a year (SGLN 0.12% vs
  GLD 0.40%). Platform fee 0.25% a year on the whole account (typical percentage-fee platform; flat-fee platforms
  differ). Trading cost 5 bps per trade (spread; £0 commission). Cash earns the UK 3-month interbank rate (FRED
  IR3TIB01GBM156N), published with a lag.
- Strategies: S&P fund only (buy and hold), 70/30 monthly (main), 70/30 + 20% risk cap (shadow); each also in dollars
  for reference.
- Model check: the modelled pound returns of the S&P and gold funds are compared with the actual UK funds' prices
  (VUSA.L, SGLN.L on Yahoo) over every common year.

## Pre-registered tests
1. **Model is realistic:** modelled vs actual UK fund return differs by less than 0.5 percentage points a year (each fund).
2. **Profit in pounds:** 70/30's CAGR in pounds is within 1 percentage point of the S&P fund's.
3. **Risk in pounds:** 70/30 has a higher Sharpe ratio (against pound cash) and a smaller worst fall than the S&P fund.
Reported also: worst year, the 2008-09 / 2020 / 2022 downturns in pounds, and how much the pound changed each result.

## Correction after the first run (2026-10-30 11:30 UK; no test or threshold changed)
The first run (`results/2026-10-30-1107-uk-real/`) exposed two measurement problems, fixed before reading any
conclusion: (1) daily returns in pounds had autocorrelation of about −0.18 because Yahoo's GBP/USD close is recorded
hours away from the US close; that noise cancels within a month, so risk figures (volatility, Sharpe, worst fall, test 3)
are now measured on month-end values, with the daily figures kept for reference; (2) the real-fund check compared daily
returns across different closing times and could not handle Yahoo's pence/pound switches (SGLN.L showed an impossible
−21.9% a year); it now uses month-end prices and corrects 10x jumps, reporting how many. The model's assumptions are
unchanged.
