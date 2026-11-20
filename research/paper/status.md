# Paper trading status (simulated money)

## A: 70/30 SPY/GLD, monthly rebalance (MAIN)

- Equity **$9,019.69** (-9.80% since 2026-10-29), cash $0.00
- Holdings: GLD 30%, SPY 70%
- Last processed close: 2026-11-20; next decision day: 2026-12-01
- Pending orders: none
- Orders so far: 2; fees $2.30

## B: 70/30 SPY/GLD with 20% risk cap (SHADOW, evidence only)

- Equity **$9,181.09** (-8.19% since 2026-10-29), cash $1,378.42
- Holdings: GLD 22%, SPY 63%
- Last processed close: 2026-11-20; next decision day: 2026-11-23
- Pending orders: SPY 55%, GLD 20% (decided 2026-11-20)
- Orders so far: 4; fees $2.65

## C: 70/30 SPY/GLD, rebalanced every day (SHADOW, evidence only)

- Equity **$9,023.58** (-9.76% since 2026-10-29), cash $0.00
- Holdings: GLD 30%, SPY 70%
- Last processed close: 2026-11-20; next decision day: 2026-11-23
- Pending orders: SPY 70%, GLD 30% (decided 2026-11-20)
- Orders so far: 32; fees $2.53

Decisions use completed daily prices and fill at the next official open, exactly as backtested.
