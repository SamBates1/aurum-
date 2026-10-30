# Scanner results

Close of 2026-10-30 00:00:00. Alpaca SIP daily prices, 3,072 instruments analysed. What the rules rank highest, not advice; nothing places an order.

## Long-Term scanner (months to years)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,924 | eligible in the universe snapshot |
| 2. filter: kind | 3,924 | kinds: stock, etf, commodity etf |
| 2. filter: price | 3,639 | price at least $10 |
| 2. filter: volume | 2,493 | at least $20M traded a day |
| 3. analyse | 2,430 | 252+ days of history, signals computed |
| 3b. company accounts | 0 | SEC unavailable today |
| 4. rank | 300 | equal weights (untested) |
| 5. risk check | 300 | portfolio checks added in phase 5 |

**Not supported by evidence:** no signal has passed its test, so all count equally and the ranking is for information only.

| # | Symbol | Score | momentum | low_volatility | near_52w_high |
|---|---|---|---|---|---|
| 1 | SCHD | 74 | 63% | 72% | 86% |
| 2 | HDV | 70 | 52% | 71% | 86% |
| 3 | IXC | 68 | 83% | 35% | 86% |
| 4 | IYE | 68 | 84% | 32% | 86% |
| 5 | FENY | 68 | 85% | 31% | 86% |
| 6 | LVHI | 67 | 57% | 82% | 64% |
| 7 | RPRX | 67 | 93% | 23% | 86% |
| 8 | XLE | 67 | 86% | 29% | 86% |
| 9 | VDE | 67 | 84% | 31% | 86% |
| 10 | FDL | 67 | 50% | 65% | 86% |
| 11 | PAGP | 66 | 92% | 43% | 63% |
| 12 | PAAA | 66 | 16% | 96% | 86% |
| 13 | SGOV | 66 | 11% | 100% | 86% |
| 14 | LXP | 66 | 73% | 38% | 86% |
| 15 | PAA | 66 | 90% | 39% | 68% |

## Swing scanner (1 to 8 weeks)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,924 | eligible in the universe snapshot |
| 2. filter: kind | 3,865 | kinds: stock, etf |
| 2. filter: price | 3,581 | price at least $10 |
| 2. filter: volume | 2,458 | at least $20M traded a day |
| 2. filter: volatility band | 1,963 | daily range 1% to 6% |
| 3. analyse | 1,941 | 200+ days of history, signals computed |
| 4. rank | 1,941 | equal weights (untested) |
| 5. risk check | 56 | 44 dropped: earnings within 8 weeks |

**Not supported by evidence:** no signal has passed its test, so all count equally and the ranking is for information only.

| # | Symbol | Score | short_term_reversal | breakout | pullback_in_uptrend | trend_strength |
|---|---|---|---|---|---|---|
| 1 | UMC | 100 | 100% | - | - | - |
| 2 | PSI | 100 | 100% | - | - | - |
| 3 | CAT | 100 | 100% | - | - | - |
| 4 | PLXS | 100 | 100% | - | - | - |
| 5 | AIS | 100 | 100% | - | - | - |
| 6 | GLW | 100 | 100% | - | - | - |
| 7 | TFII | 100 | 100% | - | - | - |
| 8 | SLM | 99 | 99% | - | - | - |
| 9 | KLAC | 99 | 99% | - | - | - |
| 10 | GTX | 99 | 99% | - | - | - |
| 11 | BHE | 99 | 99% | - | - | - |
| 12 | RIVN | 99 | 99% | - | - | - |
| 13 | CHAT | 99 | 99% | - | - | - |
| 14 | CHRW | 99 | 99% | - | - | - |
| 15 | SOXX | 99 | 99% | - | - | - |

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
| 2 | FELV | 84 | 94% | 88% | 72% |
| 3 | IWX | 84 | 94% | 88% | 72% |
| 4 | DFLV | 84 | 91% | 88% | 74% |
| 5 | TVAL | 84 | 92% | 87% | 73% |
| 6 | PVAL | 84 | 92% | 86% | 74% |
| 7 | DFUV | 83 | 90% | 88% | 72% |
| 8 | VFMF | 83 | 93% | 90% | 67% |
| 9 | IWD | 83 | 93% | 86% | 71% |
| 10 | VONV | 83 | 93% | 86% | 71% |
| 11 | AVLV | 83 | 89% | 89% | 72% |
| 12 | LVHI | 82 | 87% | 86% | 75% |
| 13 | FNDX | 82 | 91% | 81% | 74% |
| 14 | PRF | 82 | 90% | 82% | 73% |
| 15 | MGV | 82 | 91% | 81% | 73% |

Run time 375s.
