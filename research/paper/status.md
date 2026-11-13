# Paper trading status (simulated money)

## A: 70/30 SPY/GLD, monthly rebalance (MAIN)

- Equity **$9,883.45** (-1.17% since 2026-10-29), cash $0.00
- Holdings: GLD 30%, SPY 70%
- Last processed close: 2026-11-13; next decision day: 2026-12-01
- Pending orders: none
- Orders so far: 2; fees $2.30

## B: 70/30 SPY/GLD with 20% risk cap (SHADOW, evidence only)

- Equity **$9,926.31** (-0.74% since 2026-10-29), cash $1,378.42
- Holdings: GLD 23%, SPY 63%
- Last processed close: 2026-11-13; next decision day: 2026-11-16
- Pending orders: SPY 64%, GLD 22% (decided 2026-11-13)
- Orders so far: 4; fees $2.65

## C: 70/30 SPY/GLD, rebalanced every day (SHADOW, evidence only)

- Equity **$9,886.34** (-1.14% since 2026-10-29), cash $0.00
- Holdings: GLD 30%, SPY 70%
- Last processed close: 2026-11-13; next decision day: 2026-11-16
- Pending orders: SPY 70%, GLD 30% (decided 2026-11-13)
- Orders so far: 22; fees $2.46

Decisions use completed daily prices and fill at the next official open, exactly as backtested.
