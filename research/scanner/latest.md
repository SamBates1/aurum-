# Scanner results

Close of 2026-11-12. Alpaca SIP daily prices, 3,151 instruments analysed. What the rules rank highest, not advice; nothing places an order.

## Long-Term scanner (months to years)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,967 | eligible in the universe snapshot |
| 2. filter: kind | 3,967 | kinds: stock, etf, commodity etf |
| 2. filter: price | 3,666 | price at least $10 |
| 2. filter: volume | 2,563 | at least $20M traded a day |
| 3. analyse | 2,463 | 252+ days of history, signals computed |
| 3b. company accounts | 0 | SEC unavailable today |
| 4. rank | 300 | equal weights (untested) |
| 5. risk check | 300 | portfolio checks added in phase 5 |

**Live test (owner decision D-045):** ranked by momentum alone. This signal did NOT pass its test (EXP-051a); it is being tried with paper money to learn, not because it is proven.

| # | Symbol | Score | momentum |
|---|---|---|---|
| 1 | BWET | 100 | 100% |
| 2 | MRNA | 100 | 100% |
| 3 | ERAS | 99 | 99% |
| 4 | AXTI | 99 | 99% |
| 5 | AGL | 99 | 99% |
| 6 | MXL | 98 | 98% |
| 7 | SNDK | 98 | 98% |
| 8 | TWST | 98 | 98% |
| 9 | ATEX | 97 | 97% |
| 10 | TXG | 97 | 97% |
| 11 | KOD | 97 | 97% |
| 12 | CDNA | 96 | 96% |
| 13 | MU | 96 | 96% |
| 14 | DELL | 96 | 96% |
| 15 | PACS | 95 | 95% |

## Swing scanner (1 to 8 weeks)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,967 | eligible in the universe snapshot |
| 2. filter: kind | 3,905 | kinds: stock, etf |
| 2. filter: price | 3,605 | price at least $10 |
| 2. filter: volume | 2,527 | at least $20M traded a day |
| 2. filter: volatility band | 1,920 | daily range 1% to 6% |
| 3. analyse | 1,899 | 200+ days of history, signals computed |
| 4. rank | 1,899 | equal weights (untested) |
| 5. risk check | 79 | 21 dropped: earnings within 8 weeks |

**Live test (owner decision D-045):** ranked by trend_strength alone. This signal did NOT pass its test (EXP-051a); it is being tried with paper money to learn, not because it is proven.

| # | Symbol | Score | trend_strength |
|---|---|---|---|
| 1 | XERS | 100 | 100% |
| 2 | SGRY | 100 | 100% |
| 3 | EPAM | 100 | 100% |
| 4 | APPN | 99 | 99% |
| 5 | CERT | 99 | 99% |
| 6 | ECO | 99 | 99% |
| 7 | TBBB | 99 | 99% |
| 8 | DFIN | 98 | 98% |
| 9 | ADMA | 98 | 98% |
| 10 | VERX | 98 | 98% |
| 11 | PGNY | 98 | 98% |
| 12 | VRDN | 98 | 98% |
| 13 | ARHS | 98 | 98% |
| 14 | DXC | 97 | 97% |
| 15 | HNGE | 97 | 97% |

## Cross-Asset scanner (months)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,967 | eligible in the universe snapshot |
| 2. filter: kind | 1,234 | kinds: etf, commodity etf |
| 2. filter: price | 1,234 | price at least $5 |
| 2. filter: volume | 1,234 | at least $5M traded a day |
| 3. analyse | 1,186 | 252+ days of history, signals computed |
| 4. rank | 1,186 | equal weights (untested) |
| 5. risk check | 1,186 | portfolio checks added in phase 5 |

**Not supported by evidence:** no signal has passed its test, so all count equally and the ranking is for information only.

| # | Symbol | Score | trend | momentum | low_volatility |
|---|---|---|---|---|---|
| 1 | FELV | 85 | 95% | 89% | 71% |
| 2 | IWX | 85 | 96% | 90% | 70% |
| 3 | TVAL | 85 | 94% | 88% | 72% |
| 4 | IUS | 85 | 94% | 89% | 72% |
| 5 | VONV | 85 | 95% | 88% | 70% |
| 6 | IWD | 84 | 95% | 88% | 70% |
| 7 | DFLV | 84 | 91% | 88% | 73% |
| 8 | SCHD | 84 | 96% | 91% | 64% |
| 9 | PVAL | 84 | 93% | 87% | 71% |
| 10 | HDV | 84 | 96% | 89% | 66% |
| 11 | LVHI | 84 | 90% | 85% | 75% |
| 12 | FNDX | 83 | 91% | 86% | 72% |
| 13 | DFUV | 83 | 89% | 88% | 72% |
| 14 | PRF | 83 | 90% | 86% | 72% |
| 15 | AVLV | 82 | 88% | 91% | 69% |

Run time 152s.
