# Scanner results

Close of 2026-10-29. Alpaca SIP daily prices, 3,072 instruments analysed. What the rules rank highest, not advice; nothing places an order.

## Long-Term scanner (months to years)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,924 | eligible in the universe snapshot |
| 2. filter: kind | 3,924 | kinds: stock, etf, commodity etf |
| 2. filter: price | 3,639 | price at least $10 |
| 2. filter: volume | 2,493 | at least $20M traded a day |
| 3. analyse | 2,381 | 252+ days of history, signals computed |
| 3b. company accounts | 0 | SEC unavailable today |
| 4. rank | 300 | equal weights (untested) |
| 5. risk check | 300 | portfolio checks added in phase 5 |

**Not supported by evidence:** no signal has passed its test, so all count equally and the ranking is for information only.

| # | Symbol | Score | momentum | low_volatility | near_52w_high |
|---|---|---|---|---|---|
| 1 | LVHI | 79 | 58% | 92% | 88% |
| 2 | IWX | 78 | 59% | 87% | 88% |
| 3 | DFLV | 78 | 58% | 87% | 88% |
| 4 | PVAL | 77 | 56% | 86% | 88% |
| 5 | SCHD | 76 | 60% | 82% | 88% |
| 6 | VONV | 76 | 55% | 85% | 88% |
| 7 | IWD | 76 | 55% | 85% | 88% |
| 8 | FNDX | 75 | 47% | 91% | 88% |
| 9 | MGV | 74 | 46% | 90% | 88% |
| 10 | VTV | 73 | 42% | 89% | 88% |
| 11 | PAA | 73 | 90% | 41% | 88% |
| 12 | HDV | 72 | 48% | 82% | 88% |
| 13 | TD | 72 | 85% | 44% | 88% |
| 14 | JQUA | 70 | 43% | 79% | 88% |
| 15 | BNS | 70 | 81% | 41% | 88% |

## Swing scanner (1 to 8 weeks)

| Stage | Kept | Note |
|---|---|---|
| 1. validate | 3,924 | eligible in the universe snapshot |
| 2. filter: kind | 3,865 | kinds: stock, etf |
| 2. filter: price | 3,581 | price at least $10 |
| 2. filter: volume | 2,458 | at least $20M traded a day |
| 2. filter: volatility band | 1,973 | daily range 1% to 6% |
| 3. analyse | 1,949 | 200+ days of history, signals computed |
| 4. rank | 1,949 | equal weights (untested) |
| 5. risk check | 35 | 65 dropped: earnings within 8 weeks |

**Not supported by evidence:** no signal has passed its test, so all count equally and the ranking is for information only.

| # | Symbol | Score | short_term_reversal | breakout | pullback_in_uptrend | trend_strength |
|---|---|---|---|---|---|---|
| 1 | FFIV | 49 | 99% | - | 96% | - |
| 2 | NEU | 48 | 94% | - | 100% | - |
| 3 | IYH | 38 | 35% | 50% | - | 66% |
| 4 | XLV | 37 | 32% | 50% | - | 66% |
| 5 | EFOR | 36 | 20% | - | 37% | 87% |
| 6 | FDN | 36 | 84% | - | 59% | - |
| 7 | ICLR | 35 | 2% | 50% | - | 88% |
| 8 | VFC | 34 | 1% | 50% | - | 86% |
| 9 | AVTR | 34 | 26% | - | 33% | 78% |
| 10 | HAS | 34 | 1% | 50% | - | 85% |
| 11 | DINO | 34 | 54% | - | - | 81% |
| 12 | IQV | 34 | 62% | - | - | 72% |
| 13 | ECL | 34 | 30% | 50% | - | 54% |
| 14 | AXGN | 33 | 8% | 50% | - | 74% |
| 15 | CLH | 33 | 71% | - | 61% | - |

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
| 2 | IWX | 84 | 93% | 88% | 72% |
| 3 | FELV | 84 | 92% | 87% | 72% |
| 4 | TVAL | 83 | 90% | 86% | 74% |
| 5 | DFLV | 83 | 90% | 87% | 74% |
| 6 | VONV | 83 | 92% | 85% | 71% |
| 7 | IWD | 83 | 92% | 85% | 71% |
| 8 | DFUV | 83 | 88% | 87% | 73% |
| 9 | PVAL | 83 | 90% | 85% | 73% |
| 10 | VFMF | 82 | 92% | 88% | 66% |
| 11 | AVLV | 82 | 86% | 89% | 71% |
| 12 | LVHI | 81 | 82% | 87% | 74% |
| 13 | BKDV | 81 | 87% | 84% | 72% |
| 14 | FNDX | 81 | 88% | 81% | 73% |
| 15 | PRF | 81 | 88% | 82% | 72% |

Run time 225s.
