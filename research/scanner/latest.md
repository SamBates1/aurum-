# Scanner results

Close of 2026-11-18. Alpaca SIP daily prices, 3,138 instruments analysed. What the rules rank highest, not advice; nothing places an order.

## Long-Term scanner (months to years)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,954 | eligible in the universe snapshot |
| 2. filter: kind | 3,954 | kinds: stock, etf, commodity etf |
| 2. filter: price | 3,658 | price at least $10 |
| 2. filter: volume | 2,544 | at least $20M traded a day |
| 3. analyse | 2,443 | 252+ days of history, signals computed |
| 3b. company accounts | 0 | SEC unavailable today |
| 4. rank | 300 | equal weights (untested) |
| 5. risk check | 300 | portfolio checks added in phase 5 |

**Live test (owner decision D-045):** ranked by momentum alone. This signal did NOT pass its test (EXP-051a); it is being tried with paper money to learn, not because it is proven.

| # | Symbol | Score | momentum |
|---|---|---|---|
| 1 | BWET | 100 | 100% |
| 2 | MRNA | 100 | 100% |
| 3 | AGL | 99 | 99% |
| 4 | AXTI | 99 | 99% |
| 5 | MXL | 99 | 99% |
| 6 | TWST | 98 | 98% |
| 7 | SNDK | 98 | 98% |
| 8 | ERAS | 98 | 98% |
| 9 | KOD | 97 | 97% |
| 10 | TXG | 97 | 97% |
| 11 | CDNA | 97 | 97% |
| 12 | DELL | 96 | 96% |
| 13 | SYRE | 96 | 96% |
| 14 | ATEX | 96 | 96% |
| 15 | MU | 95 | 95% |

## Swing scanner (1 to 8 weeks)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,954 | eligible in the universe snapshot |
| 2. filter: kind | 3,891 | kinds: stock, etf |
| 2. filter: price | 3,595 | price at least $10 |
| 2. filter: volume | 2,507 | at least $20M traded a day |
| 2. filter: volatility band | 1,855 | daily range 1% to 6% |
| 3. analyse | 1,836 | 200+ days of history, signals computed |
| 4. rank | 1,836 | equal weights (untested) |
| 5. risk check | 84 | 16 dropped: earnings within 8 weeks |

**Live test (owner decision D-045):** ranked by trend_strength alone. This signal did NOT pass its test (EXP-051a); it is being tried with paper money to learn, not because it is proven.

| # | Symbol | Score | trend_strength |
|---|---|---|---|
| 1 | XERS | 100 | 100% |
| 2 | SGRY | 100 | 100% |
| 3 | GMAB | 99 | 99% |
| 4 | VFC | 99 | 99% |
| 5 | UPBD | 99 | 99% |
| 6 | EPAM | 99 | 99% |
| 7 | ACHC | 98 | 98% |
| 8 | PGNY | 98 | 98% |
| 9 | VCEL | 98 | 98% |
| 10 | BILL | 98 | 98% |
| 11 | DFIN | 98 | 98% |
| 12 | TBBB | 98 | 98% |
| 13 | RGR | 97 | 97% |
| 14 | ENR | 97 | 97% |
| 15 | FCN | 97 | 97% |

## Cross-Asset scanner (months)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,954 | eligible in the universe snapshot |
| 2. filter: kind | 1,228 | kinds: etf, commodity etf |
| 2. filter: price | 1,228 | price at least $5 |
| 2. filter: volume | 1,228 | at least $5M traded a day |
| 3. analyse | 1,183 | 252+ days of history, signals computed |
| 4. rank | 1,183 | equal weights (untested) |
| 5. risk check | 1,183 | portfolio checks added in phase 5 |

**Not supported by evidence:** no signal has passed its test, so all count equally and the ranking is for information only.

| # | Symbol | Score | trend | momentum | low_volatility |
|---|---|---|---|---|---|
| 1 | FELV | 85 | 95% | 90% | 72% |
| 2 | IWX | 85 | 95% | 90% | 70% |
| 3 | VONV | 85 | 94% | 89% | 71% |
| 4 | IUS | 85 | 93% | 89% | 72% |
| 5 | TVAL | 85 | 93% | 89% | 72% |
| 6 | IWD | 84 | 94% | 89% | 70% |
| 7 | HDV | 84 | 96% | 88% | 68% |
| 8 | SCHD | 84 | 95% | 92% | 65% |
| 9 | DFLV | 84 | 89% | 89% | 73% |
| 10 | PVAL | 83 | 93% | 86% | 71% |
| 11 | FNDX | 83 | 90% | 86% | 73% |
| 12 | IMCV | 82 | 94% | 86% | 68% |
| 13 | DIVB | 82 | 98% | 94% | 55% |
| 14 | LVHI | 82 | 90% | 82% | 74% |
| 15 | FNDB | 82 | 88% | 85% | 73% |

Run time 172s.
