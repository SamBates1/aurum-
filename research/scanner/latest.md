# Scanner results

Close of 2026-11-03. Alpaca SIP daily prices, 3,072 instruments analysed. What the rules rank highest, not advice; nothing places an order.

## Long-Term scanner (months to years)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,924 | eligible in the universe snapshot |
| 2. filter: kind | 3,924 | kinds: stock, etf, commodity etf |
| 2. filter: price | 3,639 | price at least $10 |
| 2. filter: volume | 2,493 | at least $20M traded a day |
| 3. analyse | 2,384 | 252+ days of history, signals computed |
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
| 5 | TXG | 99 | 99% |
| 6 | MXL | 98 | 98% |
| 7 | TWST | 98 | 98% |
| 8 | ERAS | 98 | 98% |
| 9 | LITE | 97 | 97% |
| 10 | KOD | 97 | 97% |
| 11 | MU | 97 | 97% |
| 12 | CDNA | 96 | 96% |
| 13 | ATEX | 96 | 96% |
| 14 | AEHR | 96 | 96% |
| 15 | BAND | 95 | 95% |

## Swing scanner (1 to 8 weeks)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,924 | eligible in the universe snapshot |
| 2. filter: kind | 3,865 | kinds: stock, etf |
| 2. filter: price | 3,581 | price at least $10 |
| 2. filter: volume | 2,458 | at least $20M traded a day |
| 2. filter: volatility band | 1,945 | daily range 1% to 6% |
| 3. analyse | 1,925 | 200+ days of history, signals computed |
| 4. rank | 1,925 | equal weights (untested) |
| 5. risk check | 41 | 59 dropped: earnings within 8 weeks |

**Live test (owner decision D-045):** ranked by trend_strength alone. This signal did NOT pass its test (EXP-051a); it is being tried with paper money to learn, not because it is proven.

| # | Symbol | Score | trend_strength |
|---|---|---|---|
| 1 | SSL | 97 | 97% |
| 2 | HNGE | 96 | 96% |
| 3 | RRC | 95 | 95% |
| 4 | GKOS | 94 | 94% |
| 5 | RXO | 94 | 94% |
| 6 | SLDE | 93 | 93% |
| 7 | MANH | 93 | 93% |
| 8 | VFC | 93 | 93% |
| 9 | TYL | 93 | 93% |
| 10 | CACI | 92 | 92% |
| 11 | WING | 92 | 92% |
| 12 | HAS | 92 | 92% |
| 13 | EXPO | 92 | 92% |
| 14 | CART | 91 | 91% |
| 15 | HOG | 91 | 91% |

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
| 2 | FELV | 84 | 94% | 86% | 71% |
| 3 | DFLV | 84 | 92% | 86% | 74% |
| 4 | IWX | 84 | 94% | 86% | 71% |
| 5 | TVAL | 84 | 92% | 85% | 73% |
| 6 | DFUV | 83 | 90% | 87% | 74% |
| 7 | VFMF | 83 | 93% | 89% | 68% |
| 8 | IWD | 83 | 94% | 85% | 71% |
| 9 | VONV | 83 | 94% | 85% | 71% |
| 10 | PVAL | 83 | 92% | 85% | 73% |
| 11 | AVLV | 83 | 88% | 89% | 72% |
| 12 | FNDX | 82 | 90% | 81% | 74% |
| 13 | PRF | 82 | 89% | 82% | 74% |
| 14 | FNDB | 82 | 90% | 81% | 74% |
| 15 | MGV | 81 | 91% | 79% | 74% |

Run time 128s.
