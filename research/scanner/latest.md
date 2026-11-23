# Scanner results

Close of 2026-11-23. Alpaca SIP daily prices, 3,167 instruments analysed. What the rules rank highest, not advice; nothing places an order.

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
| 4 | AGL | 99 | 99% |
| 5 | SNDK | 99 | 99% |
| 6 | AXTI | 98 | 98% |
| 7 | TWST | 98 | 98% |
| 8 | ERAS | 98 | 98% |
| 9 | MXL | 97 | 97% |
| 10 | KOD | 97 | 97% |
| 11 | CDNA | 97 | 97% |
| 12 | MU | 96 | 96% |
| 13 | TXG | 96 | 96% |
| 14 | PLSE | 96 | 96% |
| 15 | DELL | 95 | 95% |

## Swing scanner (1 to 8 weeks)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,958 | eligible in the universe snapshot |
| 2. filter: kind | 3,890 | kinds: stock, etf |
| 2. filter: price | 3,566 | price at least $10 |
| 2. filter: volume | 2,514 | at least $20M traded a day |
| 2. filter: volatility band | 1,804 | daily range 1% to 6% |
| 3. analyse | 1,785 | 200+ days of history, signals computed |
| 4. rank | 1,785 | equal weights (untested) |
| 5. risk check | 87 | 13 dropped: earnings within 8 weeks |

**Live test (owner decision D-045):** ranked by trend_strength alone. This signal did NOT pass its test (EXP-051a); it is being tried with paper money to learn, not because it is proven.

| # | Symbol | Score | trend_strength |
|---|---|---|---|
| 1 | XERS | 100 | 100% |
| 2 | SGRY | 100 | 100% |
| 3 | GDYN | 100 | 100% |
| 4 | GMAB | 99 | 99% |
| 5 | OSPN | 99 | 99% |
| 6 | VFC | 99 | 99% |
| 7 | IBTA | 98 | 98% |
| 8 | EPAM | 98 | 98% |
| 9 | UPBD | 98 | 98% |
| 10 | PGNY | 97 | 97% |
| 11 | GKOS | 97 | 97% |
| 12 | DFIN | 97 | 97% |
| 13 | VCEL | 97 | 97% |
| 14 | FCN | 96 | 96% |
| 15 | RXO | 96 | 96% |

## Cross-Asset scanner (months)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,958 | eligible in the universe snapshot |
| 2. filter: kind | 1,276 | kinds: etf, commodity etf |
| 2. filter: price | 1,276 | price at least $5 |
| 2. filter: volume | 1,276 | at least $5M traded a day |
| 3. analyse | 1,229 | 252+ days of history, signals computed |
| 4. rank | 1,229 | equal weights (untested) |
| 5. risk check | 1,229 | portfolio checks added in phase 5 |

**Not supported by evidence:** no signal has passed its test, so all count equally and the ranking is for information only.

| # | Symbol | Score | trend | momentum | low_volatility |
|---|---|---|---|---|---|
| 1 | HDV | 85 | 96% | 88% | 72% |
| 2 | FELV | 85 | 95% | 90% | 70% |
| 3 | SCHD | 85 | 95% | 92% | 67% |
| 4 | DIVB | 85 | 98% | 94% | 62% |
| 5 | IWX | 84 | 95% | 90% | 69% |
| 6 | TVAL | 84 | 93% | 88% | 71% |
| 7 | VONV | 84 | 94% | 89% | 69% |
| 8 | IWD | 84 | 94% | 88% | 69% |
| 9 | IUS | 83 | 93% | 88% | 69% |
| 10 | QVAL | 83 | 96% | 94% | 60% |
| 11 | DFLV | 83 | 89% | 89% | 71% |
| 12 | FNDX | 82 | 90% | 86% | 71% |
| 13 | LVHI | 82 | 90% | 82% | 74% |
| 14 | FDL | 82 | 93% | 87% | 66% |
| 15 | PVAL | 82 | 92% | 85% | 69% |

Run time 140s.
