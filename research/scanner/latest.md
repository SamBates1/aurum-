# Scanner results

Close of 2026-11-09. Alpaca SIP daily prices, 3,151 instruments analysed. What the rules rank highest, not advice; nothing places an order.

## Long-Term scanner (months to years)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,967 | eligible in the universe snapshot |
| 2. filter: kind | 3,967 | kinds: stock, etf, commodity etf |
| 2. filter: price | 3,666 | price at least $10 |
| 2. filter: volume | 2,563 | at least $20M traded a day |
| 3. analyse | 2,460 | 252+ days of history, signals computed |
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
| 10 | AGL | 97 | 97% |
| 11 | ATEX | 97 | 97% |
| 12 | LITE | 96 | 96% |
| 13 | MU | 96 | 96% |
| 14 | CDNA | 96 | 96% |
| 15 | ICHR | 95 | 95% |

## Swing scanner (1 to 8 weeks)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,967 | eligible in the universe snapshot |
| 2. filter: kind | 3,905 | kinds: stock, etf |
| 2. filter: price | 3,605 | price at least $10 |
| 2. filter: volume | 2,527 | at least $20M traded a day |
| 2. filter: volatility band | 1,933 | daily range 1% to 6% |
| 3. analyse | 1,911 | 200+ days of history, signals computed |
| 4. rank | 1,911 | equal weights (untested) |
| 5. risk check | 76 | 24 dropped: earnings within 8 weeks |

**Live test (owner decision D-045):** ranked by trend_strength alone. This signal did NOT pass its test (EXP-051a); it is being tried with paper money to learn, not because it is proven.

| # | Symbol | Score | trend_strength |
|---|---|---|---|
| 1 | SG | 100 | 100% |
| 2 | XERS | 100 | 100% |
| 3 | GMAB | 100 | 100% |
| 4 | GDYN | 99 | 99% |
| 5 | TBBB | 99 | 99% |
| 6 | WING | 99 | 99% |
| 7 | EPAM | 99 | 99% |
| 8 | ARHS | 98 | 98% |
| 9 | FIGS | 98 | 98% |
| 10 | CERT | 98 | 98% |
| 11 | DFIN | 98 | 98% |
| 12 | VFC | 98 | 98% |
| 13 | VERX | 98 | 98% |
| 14 | DXC | 97 | 97% |
| 15 | EXEL | 97 | 97% |

## Cross-Asset scanner (months)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,967 | eligible in the universe snapshot |
| 2. filter: kind | 1,234 | kinds: etf, commodity etf |
| 2. filter: price | 1,234 | price at least $5 |
| 2. filter: volume | 1,234 | at least $5M traded a day |
| 3. analyse | 1,185 | 252+ days of history, signals computed |
| 4. rank | 1,185 | equal weights (untested) |
| 5. risk check | 1,185 | portfolio checks added in phase 5 |

**Not supported by evidence:** no signal has passed its test, so all count equally and the ranking is for information only.

| # | Symbol | Score | trend | momentum | low_volatility |
|---|---|---|---|---|---|
| 1 | FELV | 84 | 96% | 87% | 71% |
| 2 | IWX | 84 | 96% | 87% | 69% |
| 3 | TVAL | 84 | 94% | 86% | 72% |
| 4 | IUS | 84 | 94% | 86% | 72% |
| 5 | VONV | 84 | 96% | 85% | 70% |
| 6 | IWD | 84 | 95% | 85% | 70% |
| 7 | DFLV | 83 | 91% | 86% | 73% |
| 8 | PVAL | 83 | 93% | 85% | 70% |
| 9 | DFUV | 82 | 89% | 86% | 72% |
| 10 | SCHD | 82 | 96% | 87% | 64% |
| 11 | FNDX | 82 | 91% | 82% | 73% |
| 12 | LVHI | 82 | 89% | 81% | 74% |
| 13 | HDV | 81 | 96% | 84% | 65% |
| 14 | AVLV | 81 | 87% | 88% | 69% |
| 15 | PRF | 81 | 90% | 82% | 72% |

Run time 123s.
