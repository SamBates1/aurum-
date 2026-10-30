# Scanner results

Close of 2026-10-30. Alpaca SIP daily prices, 3,072 instruments analysed. What the rules rank highest, not advice; nothing places an order.

## Long-Term scanner (months to years)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,924 | eligible in the universe snapshot |
| 2. filter: kind | 3,924 | kinds: stock, etf, commodity etf |
| 2. filter: price | 3,639 | price at least $10 |
| 2. filter: volume | 2,493 | at least $20M traded a day |
| 3. analyse | 2,383 | 252+ days of history, signals computed |
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
| 6 | ERAS | 98 | 98% |
| 7 | MXL | 98 | 98% |
| 8 | TWST | 98 | 98% |
| 9 | KOD | 97 | 97% |
| 10 | LITE | 97 | 97% |
| 11 | MU | 97 | 97% |
| 12 | CDNA | 96 | 96% |
| 13 | ATEX | 96 | 96% |
| 14 | SYRE | 96 | 96% |
| 15 | AEHR | 95 | 95% |

## Swing scanner (1 to 8 weeks)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,924 | eligible in the universe snapshot |
| 2. filter: kind | 3,865 | kinds: stock, etf |
| 2. filter: price | 3,581 | price at least $10 |
| 2. filter: volume | 2,458 | at least $20M traded a day |
| 2. filter: volatility band | 1,964 | daily range 1% to 6% |
| 3. analyse | 1,942 | 200+ days of history, signals computed |
| 4. rank | 1,942 | equal weights (untested) |
| 5. risk check | 23 | 77 dropped: earnings within 8 weeks |

**Live test (owner decision D-045):** ranked by trend_strength alone. This signal did NOT pass its test (EXP-051a); it is being tried with paper money to learn, not because it is proven.

| # | Symbol | Score | trend_strength |
|---|---|---|---|
| 1 | SSL | 96 | 96% |
| 2 | GKOS | 93 | 93% |
| 3 | PSX | 93 | 93% |
| 4 | RRC | 92 | 92% |
| 5 | SLDE | 91 | 91% |
| 6 | ICLR | 91 | 91% |
| 7 | MANH | 91 | 91% |
| 8 | GDDY | 90 | 90% |
| 9 | RXO | 90 | 90% |
| 10 | HAS | 89 | 89% |
| 11 | GILD | 89 | 89% |
| 12 | DINO | 88 | 88% |
| 13 | TYL | 87 | 87% |
| 14 | EFOR | 87 | 87% |
| 15 | LLY | 86 | 86% |

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
| 1 | LXP | 94 | 95% | 92% | 95% |
| 2 | FELV | 85 | 94% | 88% | 72% |
| 3 | IWX | 84 | 94% | 88% | 72% |
| 4 | DFLV | 84 | 91% | 88% | 74% |
| 5 | TVAL | 84 | 92% | 87% | 73% |
| 6 | DFUV | 84 | 90% | 88% | 73% |
| 7 | PVAL | 84 | 92% | 86% | 73% |
| 8 | VONV | 83 | 93% | 86% | 71% |
| 9 | IWD | 83 | 93% | 86% | 71% |
| 10 | VFMF | 83 | 93% | 90% | 67% |
| 11 | AVLV | 83 | 89% | 89% | 72% |
| 12 | LVHI | 82 | 87% | 86% | 75% |
| 13 | FNDX | 82 | 91% | 81% | 74% |
| 14 | PRF | 82 | 90% | 82% | 73% |
| 15 | MGV | 82 | 91% | 81% | 73% |

Run time 128s.
