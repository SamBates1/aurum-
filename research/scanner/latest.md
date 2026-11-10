# Scanner results

Close of 2026-11-10. Alpaca SIP daily prices, 3,151 instruments analysed. What the rules rank highest, not advice; nothing places an order.

## Long-Term scanner (months to years)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,967 | eligible in the universe snapshot |
| 2. filter: kind | 3,967 | kinds: stock, etf, commodity etf |
| 2. filter: price | 3,666 | price at least $10 |
| 2. filter: volume | 2,563 | at least $20M traded a day |
| 3. analyse | 2,462 | 252+ days of history, signals computed |
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
| 5 | SNDK | 99 | 99% |
| 6 | MXL | 98 | 98% |
| 7 | KOD | 98 | 98% |
| 8 | AGL | 98 | 98% |
| 9 | TWST | 97 | 97% |
| 10 | TXG | 97 | 97% |
| 11 | ATEX | 97 | 97% |
| 12 | MU | 96 | 96% |
| 13 | LITE | 96 | 96% |
| 14 | CDNA | 96 | 96% |
| 15 | DELL | 95 | 95% |

## Swing scanner (1 to 8 weeks)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,967 | eligible in the universe snapshot |
| 2. filter: kind | 3,905 | kinds: stock, etf |
| 2. filter: price | 3,605 | price at least $10 |
| 2. filter: volume | 2,527 | at least $20M traded a day |
| 2. filter: volatility band | 1,909 | daily range 1% to 6% |
| 3. analyse | 1,887 | 200+ days of history, signals computed |
| 4. rank | 1,887 | equal weights (untested) |
| 5. risk check | 78 | 22 dropped: earnings within 8 weeks |

**Live test (owner decision D-045):** ranked by trend_strength alone. This signal did NOT pass its test (EXP-051a); it is being tried with paper money to learn, not because it is proven.

| # | Symbol | Score | trend_strength |
|---|---|---|---|
| 1 | XERS | 100 | 100% |
| 2 | GDYN | 100 | 100% |
| 3 | VIA | 100 | 100% |
| 4 | SGRY | 99 | 99% |
| 5 | EPAM | 99 | 99% |
| 6 | ETON | 99 | 99% |
| 7 | TBBB | 99 | 99% |
| 8 | FIGS | 99 | 99% |
| 9 | ARHS | 99 | 99% |
| 10 | WING | 98 | 98% |
| 11 | CERT | 98 | 98% |
| 12 | VERX | 98 | 98% |
| 13 | DXC | 98 | 98% |
| 14 | VFC | 98 | 98% |
| 15 | PGNY | 97 | 97% |

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
| 1 | FELV | 85 | 96% | 88% | 71% |
| 2 | IWX | 84 | 96% | 88% | 69% |
| 3 | IUS | 84 | 94% | 87% | 72% |
| 4 | TVAL | 84 | 95% | 87% | 72% |
| 5 | VONV | 84 | 96% | 86% | 70% |
| 6 | IWD | 84 | 95% | 86% | 70% |
| 7 | DFLV | 84 | 91% | 86% | 73% |
| 8 | PVAL | 83 | 92% | 85% | 70% |
| 9 | SCHD | 83 | 96% | 88% | 64% |
| 10 | DFUV | 83 | 89% | 86% | 72% |
| 11 | FNDX | 82 | 91% | 83% | 73% |
| 12 | HDV | 82 | 96% | 85% | 65% |
| 13 | LVHI | 82 | 90% | 81% | 75% |
| 14 | AVLV | 82 | 88% | 89% | 69% |
| 15 | PRF | 82 | 90% | 83% | 72% |

Run time 124s.
