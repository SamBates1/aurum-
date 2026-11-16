# Scanner results

Close of 2026-11-16. Alpaca SIP daily prices, 3,138 instruments analysed. What the rules rank highest, not advice; nothing places an order.

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
| 4 | SNDK | 99 | 99% |
| 5 | ERAS | 99 | 99% |
| 6 | MXL | 98 | 98% |
| 7 | AXTI | 98 | 98% |
| 8 | KOD | 98 | 98% |
| 9 | TWST | 97 | 97% |
| 10 | PACS | 97 | 97% |
| 11 | TXG | 97 | 97% |
| 12 | CDNA | 96 | 96% |
| 13 | ATEX | 96 | 96% |
| 14 | MU | 96 | 96% |
| 15 | LITE | 95 | 95% |

## Swing scanner (1 to 8 weeks)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,954 | eligible in the universe snapshot |
| 2. filter: kind | 3,891 | kinds: stock, etf |
| 2. filter: price | 3,595 | price at least $10 |
| 2. filter: volume | 2,507 | at least $20M traded a day |
| 2. filter: volatility band | 1,864 | daily range 1% to 6% |
| 3. analyse | 1,844 | 200+ days of history, signals computed |
| 4. rank | 1,844 | equal weights (untested) |
| 5. risk check | 82 | 18 dropped: earnings within 8 weeks |

**Live test (owner decision D-045):** ranked by trend_strength alone. This signal did NOT pass its test (EXP-051a); it is being tried with paper money to learn, not because it is proven.

| # | Symbol | Score | trend_strength |
|---|---|---|---|
| 1 | XERS | 100 | 100% |
| 2 | SGRY | 100 | 100% |
| 3 | EPAM | 100 | 100% |
| 4 | DFIN | 99 | 99% |
| 5 | PGNY | 99 | 99% |
| 6 | VERX | 99 | 99% |
| 7 | TBBB | 99 | 99% |
| 8 | CPRI | 98 | 98% |
| 9 | CERT | 98 | 98% |
| 10 | VFC | 98 | 98% |
| 11 | AMPL | 98 | 98% |
| 12 | ACHC | 98 | 98% |
| 13 | CNXC | 98 | 98% |
| 14 | HNGE | 98 | 98% |
| 15 | ANDG | 97 | 97% |

## Cross-Asset scanner (months)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,954 | eligible in the universe snapshot |
| 2. filter: kind | 1,228 | kinds: etf, commodity etf |
| 2. filter: price | 1,228 | price at least $5 |
| 2. filter: volume | 1,228 | at least $5M traded a day |
| 3. analyse | 1,181 | 252+ days of history, signals computed |
| 4. rank | 1,181 | equal weights (untested) |
| 5. risk check | 1,181 | portfolio checks added in phase 5 |

**Not supported by evidence:** no signal has passed its test, so all count equally and the ranking is for information only.

| # | Symbol | Score | trend | momentum | low_volatility |
|---|---|---|---|---|---|
| 1 | FELV | 86 | 95% | 90% | 72% |
| 2 | IWX | 85 | 96% | 90% | 70% |
| 3 | IUS | 85 | 93% | 89% | 72% |
| 4 | TVAL | 85 | 93% | 89% | 72% |
| 5 | VONV | 85 | 95% | 89% | 70% |
| 6 | IWD | 84 | 95% | 88% | 70% |
| 7 | HDV | 84 | 97% | 90% | 67% |
| 8 | SCHD | 84 | 96% | 92% | 65% |
| 9 | LVHI | 84 | 92% | 86% | 75% |
| 10 | DFLV | 84 | 90% | 89% | 73% |
| 11 | FNDX | 83 | 90% | 87% | 73% |
| 12 | DIVB | 83 | 98% | 94% | 58% |
| 13 | PVAL | 83 | 91% | 87% | 70% |
| 14 | IMCV | 83 | 94% | 85% | 68% |
| 15 | FNDB | 82 | 89% | 86% | 73% |

Run time 137s.
