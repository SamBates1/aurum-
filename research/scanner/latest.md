# Scanner results

Close of 2026-11-17. Alpaca SIP daily prices, 3,138 instruments analysed. What the rules rank highest, not advice; nothing places an order.

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
| 4 | MXL | 99 | 99% |
| 5 | AXTI | 99 | 99% |
| 6 | SNDK | 98 | 98% |
| 7 | ERAS | 98 | 98% |
| 8 | TWST | 98 | 98% |
| 9 | KOD | 97 | 97% |
| 10 | TXG | 97 | 97% |
| 11 | PACS | 97 | 97% |
| 12 | CDNA | 96 | 96% |
| 13 | MU | 96 | 96% |
| 14 | AAOI | 96 | 96% |
| 15 | SYRE | 95 | 95% |

## Swing scanner (1 to 8 weeks)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,954 | eligible in the universe snapshot |
| 2. filter: kind | 3,891 | kinds: stock, etf |
| 2. filter: price | 3,595 | price at least $10 |
| 2. filter: volume | 2,507 | at least $20M traded a day |
| 2. filter: volatility band | 1,838 | daily range 1% to 6% |
| 3. analyse | 1,819 | 200+ days of history, signals computed |
| 4. rank | 1,819 | equal weights (untested) |
| 5. risk check | 86 | 14 dropped: earnings within 8 weeks |

**Live test (owner decision D-045):** ranked by trend_strength alone. This signal did NOT pass its test (EXP-051a); it is being tried with paper money to learn, not because it is proven.

| # | Symbol | Score | trend_strength |
|---|---|---|---|
| 1 | SGRY | 100 | 100% |
| 2 | XERS | 100 | 100% |
| 3 | GMAB | 100 | 100% |
| 4 | PGNY | 99 | 99% |
| 5 | EPAM | 99 | 99% |
| 6 | VFC | 99 | 99% |
| 7 | ANDG | 99 | 99% |
| 8 | ACHC | 99 | 99% |
| 9 | DFIN | 98 | 98% |
| 10 | TBBB | 98 | 98% |
| 11 | BILL | 98 | 98% |
| 12 | RGR | 98 | 98% |
| 13 | FCN | 98 | 98% |
| 14 | VCEL | 98 | 98% |
| 15 | GRDN | 97 | 97% |

## Cross-Asset scanner (months)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,954 | eligible in the universe snapshot |
| 2. filter: kind | 1,228 | kinds: etf, commodity etf |
| 2. filter: price | 1,228 | price at least $5 |
| 2. filter: volume | 1,228 | at least $5M traded a day |
| 3. analyse | 1,182 | 252+ days of history, signals computed |
| 4. rank | 1,182 | equal weights (untested) |
| 5. risk check | 1,182 | portfolio checks added in phase 5 |

**Not supported by evidence:** no signal has passed its test, so all count equally and the ranking is for information only.

| # | Symbol | Score | trend | momentum | low_volatility |
|---|---|---|---|---|---|
| 1 | FELV | 86 | 95% | 90% | 72% |
| 2 | IWX | 85 | 95% | 90% | 69% |
| 3 | IUS | 85 | 93% | 89% | 72% |
| 4 | TVAL | 85 | 93% | 89% | 72% |
| 5 | VONV | 84 | 95% | 89% | 70% |
| 6 | SCHD | 84 | 96% | 91% | 66% |
| 7 | HDV | 84 | 97% | 88% | 68% |
| 8 | IWD | 84 | 95% | 89% | 70% |
| 9 | DFLV | 84 | 90% | 89% | 73% |
| 10 | LVHI | 83 | 92% | 84% | 74% |
| 11 | PVAL | 83 | 92% | 87% | 70% |
| 12 | FNDX | 83 | 90% | 86% | 72% |
| 13 | DIVB | 83 | 98% | 93% | 57% |
| 14 | FNDB | 82 | 88% | 86% | 72% |
| 15 | IMCV | 82 | 94% | 84% | 68% |

Run time 138s.
