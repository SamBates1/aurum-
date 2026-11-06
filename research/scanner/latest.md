# Scanner results

Close of 2026-11-06. Alpaca SIP daily prices, 3,072 instruments analysed. What the rules rank highest, not advice; nothing places an order.

## Long-Term scanner (months to years)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,924 | eligible in the universe snapshot |
| 2. filter: kind | 3,924 | kinds: stock, etf, commodity etf |
| 2. filter: price | 3,639 | price at least $10 |
| 2. filter: volume | 2,493 | at least $20M traded a day |
| 3. analyse | 2,388 | 252+ days of history, signals computed |
| 3b. company accounts | 0 | SEC unavailable today |
| 4. rank | 300 | equal weights (untested) |
| 5. risk check | 300 | portfolio checks added in phase 5 |

**Live test (owner decision D-045):** ranked by momentum alone. This signal did NOT pass its test (EXP-051a); it is being tried with paper money to learn, not because it is proven.

| # | Symbol | Score | momentum |
|---|---|---|---|
| 1 | BWET | 100 | 100% |
| 2 | MRNA | 100 | 100% |
| 3 | AXTI | 99 | 99% |
| 4 | SNDK | 99 | 99% |
| 5 | ERAS | 99 | 99% |
| 6 | MXL | 98 | 98% |
| 7 | TXG | 98 | 98% |
| 8 | KOD | 98 | 98% |
| 9 | TWST | 97 | 97% |
| 10 | LITE | 97 | 97% |
| 11 | MU | 97 | 97% |
| 12 | ATEX | 96 | 96% |
| 13 | DELL | 96 | 96% |
| 14 | CDNA | 96 | 96% |
| 15 | QMCO | 95 | 95% |

## Swing scanner (1 to 8 weeks)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,924 | eligible in the universe snapshot |
| 2. filter: kind | 3,865 | kinds: stock, etf |
| 2. filter: price | 3,581 | price at least $10 |
| 2. filter: volume | 2,458 | at least $20M traded a day |
| 2. filter: volatility band | 1,847 | daily range 1% to 6% |
| 3. analyse | 1,834 | 200+ days of history, signals computed |
| 4. rank | 1,834 | equal weights (untested) |
| 5. risk check | 76 | 24 dropped: earnings within 8 weeks |

**Live test (owner decision D-045):** ranked by trend_strength alone. This signal did NOT pass its test (EXP-051a); it is being tried with paper money to learn, not because it is proven.

| # | Symbol | Score | trend_strength |
|---|---|---|---|
| 1 | XERS | 100 | 100% |
| 2 | GMAB | 100 | 100% |
| 3 | EPAM | 100 | 100% |
| 4 | TBBB | 99 | 99% |
| 5 | CERT | 99 | 99% |
| 6 | ATRC | 98 | 98% |
| 7 | WING | 98 | 98% |
| 8 | HAE | 98 | 98% |
| 9 | FIGS | 98 | 98% |
| 10 | VFC | 98 | 98% |
| 11 | AMPL | 98 | 98% |
| 12 | DXC | 98 | 98% |
| 13 | RGR | 97 | 97% |
| 14 | RVTY | 97 | 97% |
| 15 | CPRI | 97 | 97% |

## Cross-Asset scanner (months)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,924 | eligible in the universe snapshot |
| 2. filter: kind | 1,213 | kinds: etf, commodity etf |
| 2. filter: price | 1,213 | price at least $5 |
| 2. filter: volume | 1,213 | at least $5M traded a day |
| 3. analyse | 1,168 | 252+ days of history, signals computed |
| 4. rank | 1,168 | equal weights (untested) |
| 5. risk check | 1,168 | portfolio checks added in phase 5 |

**Not supported by evidence:** no signal has passed its test, so all count equally and the ranking is for information only.

| # | Symbol | Score | trend | momentum | low_volatility |
|---|---|---|---|---|---|
| 1 | LXP | 93 | - | 90% | 96% |
| 2 | FELV | 85 | 96% | 88% | 70% |
| 3 | IWX | 84 | 96% | 88% | 68% |
| 4 | IWD | 84 | 96% | 86% | 69% |
| 5 | VONV | 84 | 96% | 86% | 70% |
| 6 | TVAL | 84 | 93% | 87% | 71% |
| 7 | DFLV | 83 | 90% | 88% | 72% |
| 8 | PVAL | 83 | 92% | 86% | 70% |
| 9 | SCHD | 82 | 96% | 90% | 61% |
| 10 | LVHI | 82 | 90% | 83% | 74% |
| 11 | DFUV | 82 | 87% | 88% | 72% |
| 12 | FNDX | 82 | 90% | 84% | 72% |
| 13 | CERY | 82 | 88% | 95% | 62% |
| 14 | PRF | 82 | 89% | 84% | 71% |
| 15 | BKDV | 81 | 90% | 85% | 69% |

Run time 127s.
