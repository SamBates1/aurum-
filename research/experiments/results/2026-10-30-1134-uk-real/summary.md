# EXP-046, EXP-047, EXP-048 results (2026-10-30 11:34 UTC)

Code 26347595f61f, commit a5a8299. Historical simulations, net of the stated costs; not forecasts and not personal financial advice.

## EXP-046: 70/30 as a UK investor (pounds, UK funds, fees, ISA)

Daily 2006-06-01 to 2026-10-29. Decisions from US prices; accounting in pounds at each day's GBP/USD; UK fund drag S&P +0.22%/yr, gold −0.28%/yr vs the US ETFs; platform fee 0.25%/yr; 5 bps per trade; cash at the UK 3-month rate. Historical simulation, not a forecast.

| Strategy | CAGR in £ | CAGR in $ | Sharpe (£) | Worst fall (£) | Worst fall ($) | Volatility (£) | Worst year (£) |
|---|---|---|---|---|---|---|---|
| S&P fund only | 12.5% | 11.2% | 0.58 | -35.5% | -55.2% | 20.2% | -14.7% |
| 70/30 (main) | 12.7% | 11.1% | 0.69 | -19.3% | -38.5% | 16.1% | -2.8% |
| 70/30 + risk cap (shadow) | 11.6% | 11.0% | 0.73 | -15.3% | -25.8% | 13.6% | -2.9% |

Measured on month-end values in pounds (the MAIN risk figures: the pound/dollar rate is recorded hours away from the US close, which adds day-to-day noise that cancels within a month, so the daily volatility above is overstated):

| Strategy | CAGR | Volatility | Sharpe (vs UK cash) | Worst fall (month-end) | Worst year |
|---|---|---|---|---|---|
| S&P fund only | 12.5% | 13.3% | 0.80 | -31.1% | -14.7% |
| 70/30 (main) | 12.7% | 10.6% | 0.99 | -10.2% | -2.8% |
| 70/30 + risk cap (shadow) | 11.7% | 9.7% | 0.98 | -8.3% | -2.9% |

Downturns (return over the window, in pounds then dollars):

| Strategy | 2008-09 | 2020 | 2022 |
|---|---|---|---|
| S&P fund only | -19.2% (in $ -35.1%) | -4.8% (in $ -9.9%) | -5.0% (in $ -18.2%) |
| 70/30 (main) | -0.7% (in $ -20.3%) | +1.0% (in $ -4.3%) | -1.6% (in $ -15.4%) |
| 70/30 + risk cap (shadow) | -3.6% (in $ -13.8%) | -2.6% (in $ -6.2%) | -1.9% (in $ -14.2%) |

Model check (modelled UK fund vs the real fund's price, month-end, annual return):

| Fund | Months | Real | Model | Difference | Correlation of monthly returns | Pence/pound fixes | Bad months dropped |
|---|---|---|---|---|---|---|---|
| VUSA.L | 2012-05 to 2026-10 | 15.7% | 16.0% | +0.3% | 0.96 | 0 | 0 |
| SGLN.L | 2011-05 to 2026-10 | 7.6% | 7.8% | +0.1% | 0.98 | 0 | 1 |

**Test 1 (model realistic, < 0.5 pt/yr):** PASS. **Test 2 (70/30 CAGR within 1 pt of the S&P fund):** PASS. **Test 3 (higher Sharpe and smaller worst fall):** PASS.

## EXP-047: 70/30 over 1972-2026 (monthly averages)

Data: Shiller S&P 500 total return (dividends known to 2023-06, then a 1.58% yield), World Bank gold, pounds per dollar. Costs 0.10% per trade, fund fees 0.2% (S&P) and 0.25% (gold) a year. **Monthly averages smooth falls inside a month**: see the check at the end. 

### In dollars

| Strategy | CAGR | Volatility | Sharpe | Worst fall | Worst year |
|---|---|---|---|---|---|
| S&P 500 | 11.0% | 12.5% | 0.55 | -49.2% | -39.4% |
| 70/30 S&P/gold | 10.7% | 10.2% | 0.62 | -32.7% | -28.3% |
| Gold | 8.5% | 17.2% | 0.30 | -63.9% | -27.7% |

| Bear market | S&P 500 | 70/30 | 70/30 fell less? |
|---|---|---|---|
| 1973-74 oil shock | -38.8% | +0.0% | yes |
| 1980-82 recession | -11.5% | -21.3% | **no** |
| 1987 crash | -21.3% | -13.2% | yes |
| 2000-02 dot-com | -40.4% | -27.4% | yes |
| 2007-09 financial crisis | -47.7% | -30.1% | yes |
| 2020 Covid | -15.4% | -8.6% | yes |
| 2022 rate rises | -19.4% | -15.8% | yes |

| Sub-period | S&P Sharpe | 70/30 Sharpe |
|---|---|---|
| 1972-1989 | 0.31 | 0.41 |
| 1990-2007 | 0.57 | 0.55 |
| 2008-2026 | 0.76 | 0.95 |

| Decade | S&P 500 | 70/30 |
|---|---|---|
| 1970s | +48.7% | +182.4% |
| 1980s | +382.2% | +207.4% |
| 1990s | +412.7% | +187.1% |
| 2000s | -8.9% | +47.3% |
| 2010s | +242.1% | +161.0% |
| 2020s | +165.3% | +177.3% |

Worst 10-year return a year: S&P -3.7%, 70/30 +1.3%. 70/30 beat the S&P in 31% of 10-year periods.

**Test 1 (fell less in every bear market):** FAIL. **Test 2 (higher Sharpe overall and in 2 of 3 sub-periods):** PASS. **Test 3 (better worst decade):** PASS.

### In pounds

| Strategy | CAGR | Volatility | Sharpe | Worst fall | Worst year |
|---|---|---|---|---|---|
| S&P 500 | 12.3% | 14.0% | 0.44 | -47.6% | -27.6% |
| 70/30 S&P/gold | 12.0% | 11.3% | 0.50 | -32.7% | -20.0% |
| Gold | 9.8% | 17.0% | 0.25 | -52.1% | -28.7% |

| Bear market | S&P 500 | 70/30 | 70/30 fell less? |
|---|---|---|---|
| 1973-74 oil shock | -38.4% | +0.7% | yes |
| 1980-82 recession | +22.8% | +9.3% | **no** |
| 1987 crash | -30.8% | -23.6% | yes |
| 2000-02 dot-com | -42.3% | -29.7% | yes |
| 2007-09 financial crisis | -25.5% | -0.5% | yes |
| 2020 Covid | -10.9% | -3.8% | yes |
| 2022 rate rises | -5.4% | -1.1% | yes |

| Sub-period | S&P Sharpe | 70/30 Sharpe |
|---|---|---|
| 1972-1989 | 0.24 | 0.34 |
| 1990-2007 | 0.21 | 0.09 |
| 2008-2026 | 0.95 | 1.21 |

| Decade | S&P 500 | 70/30 |
|---|---|---|
| 1970s | +70.7% | +224.2% |
| 1980s | +564.8% | +323.7% |
| 1990s | +407.3% | +184.1% |
| 2000s | -9.4% | +46.4% |
| 2010s | +323.4% | +223.1% |
| 2020s | +159.4% | +171.2% |

Worst 10-year return a year: S&P -2.7%, 70/30 +2.3%. 70/30 beat the S&P in 31% of 10-year periods.

**Test 1 (fell less in every bear market):** FAIL. **Test 2 (higher Sharpe overall and in 2 of 3 sub-periods):** PASS. **Test 3 (better worst decade):** PASS.

### How much monthly averages smooth things (2006-07 to 2026-09, dollars)

| Strategy | Monthly-average volatility | Worst fall (monthly avg) |
|---|---|---|
| S&P 500 | 12.9% | -49.2% |
| 70/30 S&P/gold | 9.8% | -32.7% |

Daily data over the same years (EXP-045/designer): S&P volatility 19.3%, worst fall −55.2%; 70/30 volatility 14.8%, worst fall −38.5%. Long-history worst falls and volatility are therefore understated; comparisons between the two strategies are on equal terms.

## EXP-048: the range of outcomes to expect (in pounds, after fees)

10,000 simulated futures (block bootstrap, 12-month blocks). Main view: true month-end returns from EXP-046's daily data in pounds, 2006-2026, after UK fund costs and the platform fee. Second view: 1972-2026 monthly series scaled to daily-data volatility. Nominal pounds, before inflation. The future can be worse than anything in the sample.

**Read this first:** 2006-2026 was unusually kind to a UK holder of 70/30 (gold rose about fourfold in pounds and the pound fell against the dollar, which lifts the value of dollar assets). The main view repeats those 20 years, so it is the OPTIMISTIC view. The 1972-2026 view includes harder decades (the early-1980s gold crash, the 1990s when gold fell) and is the more CAUTIOUS guide.

### 70/30 (main): £1,000 once

| Years | Paid in | Bad (1 in 20) | Below typical | Typical (median) | Above typical | Good (1 in 20) | Chance of ending below what you paid in | Chance of a 20%+ fall on the way |
|---|---|---|---|---|---|---|---|---|
| 1 | £1,000 | £992 | £1,063 | £1,120 | £1,188 | £1,320 | 6% | 0% |
| 3 | £1,000 | £1,151 | £1,299 | £1,428 | £1,567 | £1,795 | 0% | 0% |
| 5 | £1,000 | £1,371 | £1,616 | £1,813 | £2,040 | £2,412 | 0% | 0% |
| 10 | £1,000 | £2,238 | £2,806 | £3,296 | £3,856 | £4,906 | 0% | 0% |

### 70/30 (main): £1,000 + £100 a month

| Years | Paid in | Bad (1 in 20) | Below typical | Typical (median) | Above typical | Good (1 in 20) | Chance of ending below what you paid in | Chance of a 20%+ fall on the way |
|---|---|---|---|---|---|---|---|---|
| 1 | £2,100 | £2,085 | £2,194 | £2,286 | £2,394 | £2,582 | 6% | 0% |
| 3 | £4,500 | £4,875 | £5,283 | £5,636 | £6,016 | £6,622 | 0% | 0% |
| 5 | £6,900 | £8,221 | £9,147 | £9,896 | £10,692 | £12,069 | 0% | 0% |
| 10 | £12,900 | £20,131 | £23,497 | £26,232 | £29,304 | £34,727 | 0% | 0% |

### S&P fund only: £1,000 once

| Years | Paid in | Bad (1 in 20) | Below typical | Typical (median) | Above typical | Good (1 in 20) | Chance of ending below what you paid in | Chance of a 20%+ fall on the way |
|---|---|---|---|---|---|---|---|---|
| 1 | £1,000 | £912 | £1,055 | £1,129 | £1,214 | £1,335 | 13% | 3% |
| 3 | £1,000 | £1,013 | £1,285 | £1,455 | £1,617 | £1,869 | 5% | 13% |
| 5 | £1,000 | £1,178 | £1,572 | £1,853 | £2,127 | £2,553 | 1% | 22% |
| 10 | £1,000 | £1,821 | £2,648 | £3,332 | £4,133 | £5,356 | 0% | 41% |

### S&P fund only: £1,000 + £100 a month

| Years | Paid in | Bad (1 in 20) | Below typical | Typical (median) | Above typical | Good (1 in 20) | Chance of ending below what you paid in | Chance of a 20%+ fall on the way |
|---|---|---|---|---|---|---|---|---|
| 1 | £2,100 | £1,956 | £2,184 | £2,303 | £2,437 | £2,619 | 14% | 3% |
| 3 | £4,500 | £4,496 | £5,272 | £5,713 | £6,141 | £6,791 | 5% | 13% |
| 5 | £6,900 | £7,459 | £9,038 | £10,060 | £11,027 | £12,454 | 2% | 22% |
| 10 | £12,900 | £17,620 | £22,715 | £26,636 | £30,684 | £36,992 | 0% | 41% |

### Second view, 70/30 1972-2026 (volatility scaled x1.17): £1,000 + £100 a month

| Years | Paid in | Bad (1 in 20) | Typical | Good (1 in 20) | Chance below paid in |
|---|---|---|---|---|---|
| 1 | £2,100 | £1,867 | £2,283 | £2,722 | 21% |
| 3 | £4,500 | £4,184 | £5,583 | £7,277 | 10% |
| 5 | £6,900 | £6,744 | £9,681 | £13,618 | 6% |
| 10 | £12,900 | £14,772 | £25,018 | £40,938 | 2% |

## Figures

- [annual_returns_gbp.png](figures/annual_returns_gbp.png)
- [bear_markets_gbp.png](figures/bear_markets_gbp.png)
- [bear_markets_usd.png](figures/bear_markets_usd.png)
- [equity_drawdown_gbp.png](figures/equity_drawdown_gbp.png)
- [long_equity_gbp.png](figures/long_equity_gbp.png)
- [long_equity_usd.png](figures/long_equity_usd.png)
- [outcome_ranges.png](figures/outcome_ranges.png)
- [rolling_10y_gbp.png](figures/rolling_10y_gbp.png)
- [rolling_10y_usd.png](figures/rolling_10y_usd.png)
