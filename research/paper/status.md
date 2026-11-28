# Paper trading status (simulated money)

## A: 70/30 SPY/GLD, monthly rebalance (MAIN)

- Equity **$9,469.34** (-5.31% since 2026-10-29), cash $0.00
- Holdings: GLD 29%, SPY 71%
- Last processed close: 2026-11-27; next decision day: 2026-12-01
- Pending orders: none
- Orders so far: 2; fees $2.30

## B: 70/30 SPY/GLD with 20% risk cap (SHADOW, evidence only)

- Equity **$9,553.62** (-4.46% since 2026-10-29), cash $3,122.76
- Holdings: GLD 22%, SPY 45%
- Last processed close: 2026-11-27; next decision day: 2026-11-30
- Pending orders: SPY 44%, GLD 17% (decided 2026-11-27)
- Orders so far: 6; fees $3.00

## C: 70/30 SPY/GLD, rebalanced every day (SHADOW, evidence only)

- Equity **$9,473.19** (-5.27% since 2026-10-29), cash $-0.00
- Holdings: GLD 30%, SPY 70%
- Last processed close: 2026-11-27; next decision day: 2026-11-30
- Pending orders: SPY 70%, GLD 30% (decided 2026-11-27)
- Orders so far: 40; fees $2.59

Decisions use completed daily prices and fill at the next official open, exactly as backtested.
