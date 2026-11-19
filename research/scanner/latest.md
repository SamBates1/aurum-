# Scanner results

Close of 2026-11-19. Alpaca SIP daily prices, 3,138 instruments analysed. What the rules rank highest, not advice; nothing places an order.

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
| 9 | TXG | 97 | 97% |
| 10 | KOD | 97 | 97% |
| 11 | CDNA | 97 | 97% |
| 12 | MU | 96 | 96% |
| 13 | DELL | 96 | 96% |
| 14 | SYRE | 96 | 96% |
| 15 | PLSE | 95 | 95% |

## Swing scanner (1 to 8 weeks)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,954 | eligible in the universe snapshot |
| 2. filter: kind | 3,891 | kinds: stock, etf |
| 2. filter: price | 3,595 | price at least $10 |
| 2. filter: volume | 2,507 | at least $20M traded a day |
| 2. filter: volatility band | 1,829 | daily range 1% to 6% |
| 3. analyse | 1,811 | 200+ days of history, signals computed |
| 4. rank | 1,811 | equal weights (untested) |
| 5. risk check | 83 | 17 dropped: earnings within 8 weeks |

**Live test (owner decision D-045):** ranked by trend_strength alone. This signal did NOT pass its test (EXP-051a); it is being tried with paper money to learn, not because it is proven.

| # | Symbol | Score | trend_strength |
|---|---|---|---|
| 1 | XERS | 100 | 100% |
| 2 | SGRY | 100 | 100% |
| 3 | GDYN | 100 | 100% |
| 4 | GMAB | 99 | 99% |
| 5 | OSPN | 99 | 99% |
| 6 | VFC | 99 | 99% |
| 7 | PGNY | 98 | 98% |
| 8 | VCEL | 98 | 98% |
| 9 | EPAM | 98 | 98% |
| 10 | UPBD | 98 | 98% |
| 11 | DFIN | 98 | 98% |
| 12 | CPRI | 98 | 98% |
| 13 | BILL | 97 | 97% |
| 14 | RGR | 97 | 97% |
| 15 | VNT | 97 | 97% |

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
| 1 | FELV | 85 | 95% | 89% | 71% |
| 2 | IWX | 85 | 95% | 89% | 70% |
| 3 | VONV | 84 | 94% | 88% | 70% |
| 4 | TVAL | 84 | 93% | 88% | 71% |
| 5 | IWD | 84 | 94% | 88% | 70% |
| 6 | IUS | 84 | 92% | 88% | 71% |
| 7 | SCHD | 84 | 95% | 90% | 65% |
| 8 | HDV | 83 | 96% | 86% | 68% |
| 9 | DFLV | 83 | 88% | 88% | 72% |
| 10 | PVAL | 83 | 92% | 86% | 70% |
| 11 | LVHI | 82 | 91% | 82% | 74% |
| 12 | FNDX | 82 | 88% | 85% | 72% |
| 13 | IMCV | 82 | 93% | 84% | 68% |
| 14 | DIVB | 82 | 98% | 94% | 54% |
| 15 | FNDB | 81 | 87% | 84% | 72% |

Run time 135s.
