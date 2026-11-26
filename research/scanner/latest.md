# Scanner results

Close of 2026-11-25. Alpaca SIP daily prices, 3,167 instruments analysed. What the rules rank highest, not advice; nothing places an order.

## Long-Term scanner (months to years)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,958 | eligible in the universe snapshot |
| 2. filter: kind | 3,958 | kinds: stock, etf, commodity etf |
| 2. filter: price | 3,634 | price at least $10 |
| 2. filter: volume | 2,555 | at least $20M traded a day |
| 3. analyse | 2,453 | 252+ days of history, signals computed |
| 3b. company accounts | 0 | SEC unavailable today |
| 4. rank | 300 | equal weights (untested) |
| 5. risk check | 300 | portfolio checks added in phase 5 |

**Live test (owner decision D-045):** ranked by momentum alone. This signal did NOT pass its test (EXP-051a); it is being tried with paper money to learn, not because it is proven.

| # | Symbol | Score | momentum |
|---|---|---|---|
| 1 | BWET | 100 | 100% |
| 2 | MRNA | 100 | 100% |
| 3 | SLS | 99 | 99% |
| 4 | AXTI | 99 | 99% |
| 5 | SNDK | 99 | 99% |
| 6 | AGL | 98 | 98% |
| 7 | TWST | 98 | 98% |
| 8 | ERAS | 98 | 98% |
| 9 | MXL | 97 | 97% |
| 10 | ATEX | 97 | 97% |
| 11 | KOD | 97 | 97% |
| 12 | MU | 96 | 96% |
| 13 | PLSE | 96 | 96% |
| 14 | DELL | 96 | 96% |
| 15 | CDNA | 95 | 95% |

## Swing scanner (1 to 8 weeks)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,958 | eligible in the universe snapshot |
| 2. filter: kind | 3,890 | kinds: stock, etf |
| 2. filter: price | 3,566 | price at least $10 |
| 2. filter: volume | 2,514 | at least $20M traded a day |
| 2. filter: volatility band | 1,921 | daily range 1% to 6% |
| 3. analyse | 1,902 | 200+ days of history, signals computed |
| 4. rank | 1,902 | equal weights (untested) |
| 5. risk check | 88 | 12 dropped: earnings within 8 weeks |

**Live test (owner decision D-045):** ranked by trend_strength alone. This signal did NOT pass its test (EXP-051a); it is being tried with paper money to learn, not because it is proven.

| # | Symbol | Score | trend_strength |
|---|---|---|---|
| 1 | XERS | 100 | 100% |
| 2 | SGRY | 100 | 100% |
| 3 | GDYN | 100 | 100% |
| 4 | GMAB | 99 | 99% |
| 5 | VRDN | 99 | 99% |
| 6 | VFC | 99 | 99% |
| 7 | ADMA | 98 | 98% |
| 8 | IBTA | 98 | 98% |
| 9 | VCEL | 98 | 98% |
| 10 | KSS | 98 | 98% |
| 11 | EPAM | 97 | 97% |
| 12 | UPBD | 97 | 97% |
| 13 | OSPN | 97 | 97% |
| 14 | GKOS | 97 | 97% |
| 15 | COLM | 96 | 96% |

## Cross-Asset scanner (months)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,958 | eligible in the universe snapshot |
| 2. filter: kind | 1,276 | kinds: etf, commodity etf |
| 2. filter: price | 1,276 | price at least $5 |
| 2. filter: volume | 1,276 | at least $5M traded a day |
| 3. analyse | 1,231 | 252+ days of history, signals computed |
| 4. rank | 1,231 | equal weights (untested) |
| 5. risk check | 1,231 | portfolio checks added in phase 5 |

**Not supported by evidence:** no signal has passed its test, so all count equally and the ranking is for information only.

| # | Symbol | Score | trend | momentum | low_volatility |
|---|---|---|---|---|---|
| 1 | HDV | 85 | 96% | 88% | 72% |
| 2 | SCHD | 85 | 96% | 92% | 66% |
| 3 | FELV | 85 | 94% | 90% | 70% |
| 4 | IWX | 84 | 94% | 89% | 69% |
| 5 | IWD | 84 | 94% | 88% | 70% |
| 6 | TVAL | 84 | 92% | 89% | 71% |
| 7 | VONV | 84 | 94% | 88% | 69% |
| 8 | DIVB | 84 | 98% | 93% | 59% |
| 9 | IUS | 83 | 92% | 87% | 69% |
| 10 | DFLV | 83 | 88% | 89% | 71% |
| 11 | QVAL | 82 | 96% | 92% | 58% |
| 12 | LVHI | 82 | 89% | 84% | 74% |
| 13 | FNDX | 82 | 90% | 85% | 71% |
| 14 | FDL | 82 | 94% | 86% | 65% |
| 15 | PVAL | 82 | 90% | 86% | 69% |

Run time 132s.
