# Scanner results

Close of 2026-11-05. Alpaca SIP daily prices, 3,072 instruments analysed. What the rules rank highest, not advice; nothing places an order.

## Long-Term scanner (months to years)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,924 | eligible in the universe snapshot |
| 2. filter: kind | 3,924 | kinds: stock, etf, commodity etf |
| 2. filter: price | 3,639 | price at least $10 |
| 2. filter: volume | 2,493 | at least $20M traded a day |
| 3. analyse | 2,386 | 252+ days of history, signals computed |
| 3b. company accounts | 0 | SEC unavailable today |
| 4. rank | 300 | equal weights (untested) |
| 5. risk check | 300 | portfolio checks added in phase 5 |

**Live test (owner decision D-045):** ranked by momentum alone. This signal did NOT pass its test (EXP-051a); it is being tried with paper money to learn, not because it is proven.

| # | Symbol | Score | momentum |
|---|---|---|---|
| 1 | BWET | 100 | 100% |
| 2 | AXTI | 100 | 100% |
| 3 | SNDK | 99 | 99% |
| 4 | MRNA | 99 | 99% |
| 5 | MXL | 99 | 99% |
| 6 | ERAS | 98 | 98% |
| 7 | LITE | 98 | 98% |
| 8 | TXG | 98 | 98% |
| 9 | TWST | 97 | 97% |
| 10 | KOD | 97 | 97% |
| 11 | MU | 97 | 97% |
| 12 | CDNA | 96 | 96% |
| 13 | ATEX | 96 | 96% |
| 14 | AAOI | 96 | 96% |
| 15 | BAND | 95 | 95% |

## Swing scanner (1 to 8 weeks)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,924 | eligible in the universe snapshot |
| 2. filter: kind | 3,865 | kinds: stock, etf |
| 2. filter: price | 3,581 | price at least $10 |
| 2. filter: volume | 2,458 | at least $20M traded a day |
| 2. filter: volatility band | 1,851 | daily range 1% to 6% |
| 3. analyse | 1,837 | 200+ days of history, signals computed |
| 4. rank | 1,837 | equal weights (untested) |
| 5. risk check | 58 | 42 dropped: earnings within 8 weeks |

**Live test (owner decision D-045):** ranked by trend_strength alone. This signal did NOT pass its test (EXP-051a); it is being tried with paper money to learn, not because it is proven.

| # | Symbol | Score | trend_strength |
|---|---|---|---|
| 1 | GMAB | 99 | 99% |
| 2 | TBBB | 99 | 99% |
| 3 | ATRC | 98 | 98% |
| 4 | AMPL | 98 | 98% |
| 5 | WING | 98 | 98% |
| 6 | FIGS | 98 | 98% |
| 7 | CPRI | 97 | 97% |
| 8 | TYL | 97 | 97% |
| 9 | SSL | 96 | 96% |
| 10 | VFC | 96 | 96% |
| 11 | RGR | 96 | 96% |
| 12 | ADMA | 96 | 96% |
| 13 | PCOR | 95 | 95% |
| 14 | GDDY | 95 | 95% |
| 15 | RVTY | 95 | 95% |

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
| 2 | FELV | 84 | 95% | 87% | 70% |
| 3 | IWX | 84 | 96% | 87% | 68% |
| 4 | VONV | 83 | 95% | 85% | 70% |
| 5 | TVAL | 83 | 93% | 85% | 71% |
| 6 | DFLV | 83 | 90% | 86% | 72% |
| 7 | IWD | 83 | 95% | 85% | 69% |
| 8 | LVHI | 82 | 90% | 83% | 74% |
| 9 | PVAL | 82 | 91% | 85% | 70% |
| 10 | DFUV | 82 | 87% | 86% | 72% |
| 11 | FNDX | 81 | 90% | 82% | 72% |
| 12 | AVLV | 81 | 86% | 88% | 69% |
| 13 | SCHD | 81 | 96% | 87% | 60% |
| 14 | PRF | 81 | 89% | 83% | 71% |
| 15 | FNDB | 81 | 89% | 81% | 72% |

Run time 150s.
