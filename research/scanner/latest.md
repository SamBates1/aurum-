# Scanner results

Close of 2026-11-20. Alpaca SIP daily prices, 3,138 instruments analysed. What the rules rank highest, not advice; nothing places an order.

## Long-Term scanner (months to years)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,954 | eligible in the universe snapshot |
| 2. filter: kind | 3,954 | kinds: stock, etf, commodity etf |
| 2. filter: price | 3,658 | price at least $10 |
| 2. filter: volume | 2,544 | at least $20M traded a day |
| 3. analyse | 2,444 | 252+ days of history, signals computed |
| 3b. company accounts | 0 | SEC unavailable today |
| 4. rank | 300 | equal weights (untested) |
| 5. risk check | 300 | portfolio checks added in phase 5 |

**Live test (owner decision D-045):** ranked by momentum alone. This signal did NOT pass its test (EXP-051a); it is being tried with paper money to learn, not because it is proven.

| # | Symbol | Score | momentum |
|---|---|---|---|
| 1 | BWET | 100 | 100% |
| 2 | MRNA | 100 | 100% |
| 3 | AGL | 99 | 99% |
| 4 | TWST | 99 | 99% |
| 5 | SNDK | 99 | 99% |
| 6 | AXTI | 98 | 98% |
| 7 | ERAS | 98 | 98% |
| 8 | MXL | 98 | 98% |
| 9 | TXG | 97 | 97% |
| 10 | KOD | 97 | 97% |
| 11 | CDNA | 97 | 97% |
| 12 | PLSE | 96 | 96% |
| 13 | DELL | 96 | 96% |
| 14 | SYRE | 96 | 96% |
| 15 | MU | 95 | 95% |

## Swing scanner (1 to 8 weeks)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,954 | eligible in the universe snapshot |
| 2. filter: kind | 3,891 | kinds: stock, etf |
| 2. filter: price | 3,595 | price at least $10 |
| 2. filter: volume | 2,507 | at least $20M traded a day |
| 2. filter: volatility band | 1,768 | daily range 1% to 6% |
| 3. analyse | 1,750 | 200+ days of history, signals computed |
| 4. rank | 1,750 | equal weights (untested) |
| 5. risk check | 86 | 14 dropped: earnings within 8 weeks |

**Live test (owner decision D-045):** ranked by trend_strength alone. This signal did NOT pass its test (EXP-051a); it is being tried with paper money to learn, not because it is proven.

| # | Symbol | Score | trend_strength |
|---|---|---|---|
| 1 | XERS | 100 | 100% |
| 2 | SGRY | 100 | 100% |
| 3 | GDYN | 100 | 100% |
| 4 | GMAB | 99 | 99% |
| 5 | OSPN | 99 | 99% |
| 6 | PGNY | 99 | 99% |
| 7 | EPAM | 98 | 98% |
| 8 | DFIN | 98 | 98% |
| 9 | UPBD | 98 | 98% |
| 10 | VCEL | 98 | 98% |
| 11 | VFC | 97 | 97% |
| 12 | RGR | 97 | 97% |
| 13 | ENR | 97 | 97% |
| 14 | RXO | 97 | 97% |
| 15 | FCN | 96 | 96% |

## Cross-Asset scanner (months)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,954 | eligible in the universe snapshot |
| 2. filter: kind | 1,228 | kinds: etf, commodity etf |
| 2. filter: price | 1,228 | price at least $5 |
| 2. filter: volume | 1,228 | at least $5M traded a day |
| 3. analyse | 1,185 | 252+ days of history, signals computed |
| 4. rank | 1,185 | equal weights (untested) |
| 5. risk check | 1,185 | portfolio checks added in phase 5 |

**Not supported by evidence:** no signal has passed its test, so all count equally and the ranking is for information only.

| # | Symbol | Score | trend | momentum | low_volatility |
|---|---|---|---|---|---|
| 1 | HDV | 86 | 97% | 90% | 70% |
| 2 | FELV | 85 | 94% | 91% | 71% |
| 3 | IWX | 85 | 94% | 91% | 70% |
| 4 | SCHD | 85 | 95% | 93% | 67% |
| 5 | VONV | 85 | 93% | 90% | 70% |
| 6 | IWD | 84 | 93% | 90% | 70% |
| 7 | TVAL | 84 | 91% | 90% | 71% |
| 8 | IUS | 84 | 91% | 90% | 71% |
| 9 | DIVB | 84 | 98% | 95% | 59% |
| 10 | IMCV | 83 | 93% | 88% | 69% |
| 11 | FDL | 82 | 94% | 89% | 65% |
| 12 | QVAL | 82 | 96% | 94% | 57% |
| 13 | FDV | 82 | 94% | 84% | 68% |
| 14 | LVHI | 81 | 87% | 83% | 74% |
| 15 | PVAL | 81 | 87% | 86% | 70% |

Run time 107s.
