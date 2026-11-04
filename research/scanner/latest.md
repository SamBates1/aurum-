# Scanner results

Close of 2026-11-04. Alpaca SIP daily prices, 3,072 instruments analysed. What the rules rank highest, not advice; nothing places an order.

## Long-Term scanner (months to years)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,924 | eligible in the universe snapshot |
| 2. filter: kind | 3,924 | kinds: stock, etf, commodity etf |
| 2. filter: price | 3,639 | price at least $10 |
| 2. filter: volume | 2,493 | at least $20M traded a day |
| 3. analyse | 2,385 | 252+ days of history, signals computed |
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
| 7 | TXG | 98 | 98% |
| 8 | LITE | 98 | 98% |
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
| 2. filter: volatility band | 1,939 | daily range 1% to 6% |
| 3. analyse | 1,921 | 200+ days of history, signals computed |
| 4. rank | 1,921 | equal weights (untested) |
| 5. risk check | 47 | 53 dropped: earnings within 8 weeks |

**Live test (owner decision D-045):** ranked by trend_strength alone. This signal did NOT pass its test (EXP-051a); it is being tried with paper money to learn, not because it is proven.

| # | Symbol | Score | trend_strength |
|---|---|---|---|
| 1 | CAI | 99 | 99% |
| 2 | ATRC | 98 | 98% |
| 3 | TBBB | 98 | 98% |
| 4 | AMPL | 98 | 98% |
| 5 | HNGE | 97 | 97% |
| 6 | GKOS | 96 | 96% |
| 7 | WING | 96 | 96% |
| 8 | VFC | 96 | 96% |
| 9 | CPRI | 95 | 95% |
| 10 | RXO | 95 | 95% |
| 11 | RVTY | 94 | 94% |
| 12 | EXEL | 94 | 94% |
| 13 | TYL | 94 | 94% |
| 14 | MANH | 93 | 93% |
| 15 | PCOR | 93 | 93% |

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
| 1 | LXP | 93 | - | 91% | 95% |
| 2 | FELV | 84 | 96% | 87% | 70% |
| 3 | DFLV | 84 | 90% | 87% | 74% |
| 4 | IWX | 84 | 96% | 88% | 67% |
| 5 | DFUV | 83 | 88% | 88% | 74% |
| 6 | TVAL | 83 | 93% | 86% | 71% |
| 7 | VFMF | 83 | 92% | 89% | 68% |
| 8 | VONV | 83 | 95% | 86% | 68% |
| 9 | IWD | 83 | 95% | 85% | 68% |
| 10 | PVAL | 83 | 92% | 85% | 71% |
| 11 | AVLV | 83 | 88% | 89% | 72% |
| 12 | FNDX | 82 | 90% | 82% | 73% |
| 13 | MGV | 82 | 90% | 81% | 74% |
| 14 | PRF | 81 | 89% | 82% | 73% |
| 15 | FNDB | 81 | 89% | 82% | 73% |

Run time 153s.
