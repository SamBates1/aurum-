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

**Not supported by evidence:** no signal has passed its test, so all count equally and the ranking is for information only.

| # | Symbol | Score | momentum | low_volatility | near_52w_high |
|---|---|---|---|---|---|
| 1 | LVHI | 78 | 53% | 93% | 89% |
| 2 | SCHD | 77 | 59% | 82% | 89% |
| 3 | PAA | 74 | 88% | 44% | 89% |
| 4 | HDV | 73 | 47% | 82% | 89% |
| 5 | PVAL | 71 | 53% | 86% | 74% |
| 6 | PAGP | 71 | 91% | 48% | 74% |
| 7 | VOE | 71 | 38% | 85% | 89% |
| 8 | DFLV | 71 | 56% | 88% | 68% |
| 9 | FDL | 70 | 45% | 76% | 89% |
| 10 | IXC | 70 | 81% | 39% | 89% |
| 11 | IYE | 69 | 83% | 36% | 89% |
| 12 | FENY | 69 | 84% | 35% | 89% |
| 13 | XLE | 69 | 85% | 33% | 89% |
| 14 | RPRX | 69 | 91% | 26% | 89% |
| 15 | VDE | 69 | 83% | 34% | 89% |

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
| 5. risk check | 47 | 53 dropped: earnings within 8 weeks |

**Not supported by evidence:** no signal has passed its test, so all count equally and the ranking is for information only.

| # | Symbol | Score | short_term_reversal | breakout | trend_strength |
|---|---|---|---|---|---|
| 1 | GILD | 50 | 11% | 50% | 89% |
| 2 | DINO | 49 | 58% | - | 88% |
| 3 | GDDY | 48 | 5% | 50% | 90% |
| 4 | MANH | 48 | 4% | 50% | 91% |
| 5 | TYL | 48 | 6% | 50% | 87% |
| 6 | TAK | 48 | 9% | 50% | 84% |
| 7 | IYH | 48 | 26% | 50% | 67% |
| 8 | VHT | 47 | 29% | 50% | 63% |
| 9 | XLV | 47 | 23% | 50% | 67% |
| 10 | EXEL | 47 | 6% | 50% | 85% |
| 11 | LLY | 46 | 3% | 50% | 86% |
| 12 | EXPO | 46 | 13% | 50% | 76% |
| 13 | HOG | 45 | 2% | 50% | 84% |
| 14 | IXJ | 45 | 22% | 50% | 64% |
| 15 | VLTO | 44 | 8% | 50% | 74% |

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
| 3 | DFLV | 84 | 91% | 88% | 74% |
| 4 | IWX | 84 | 94% | 88% | 72% |
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

Run time 183s.
