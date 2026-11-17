# Paper trading status (simulated money)

## A: 70/30 SPY/GLD, monthly rebalance (MAIN)

- Equity **$9,657.22** (-3.43% since 2026-10-29), cash $0.00
- Holdings: GLD 30%, SPY 70%
- Last processed close: 2026-11-17; next decision day: 2026-12-01
- Pending orders: none
- Orders so far: 2; fees $2.30

## B: 70/30 SPY/GLD with 20% risk cap (SHADOW, evidence only)

- Equity **$9,724.44** (-2.76% since 2026-10-29), cash $1,378.42
- Holdings: GLD 23%, SPY 63%
- Last processed close: 2026-11-17; next decision day: 2026-11-18
- Pending orders: SPY 62%, GLD 22% (decided 2026-11-17)
- Orders so far: 4; fees $2.65

## C: 70/30 SPY/GLD, rebalanced every day (SHADOW, evidence only)

- Equity **$9,660.17** (-3.40% since 2026-10-29), cash $-0.00
- Holdings: GLD 30%, SPY 70%
- Last processed close: 2026-11-17; next decision day: 2026-11-18
- Pending orders: SPY 70%, GLD 30% (decided 2026-11-17)
- Orders so far: 26; fees $2.48

Decisions use completed daily prices and fill at the next official open, exactly as backtested.
