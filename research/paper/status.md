# Paper trading status (simulated money)

## A: 70/30 SPY/GLD, monthly rebalance (MAIN)

- Equity **$9,904.08** (-0.96% since 2026-10-29), cash $0.00
- Holdings: GLD 30%, SPY 70%
- Last processed close: 2026-11-12; next decision day: 2026-12-01
- Pending orders: none
- Orders so far: 2; fees $2.30

## B: 70/30 SPY/GLD with 20% risk cap (SHADOW, evidence only)

- Equity **$9,945.72** (-0.54% since 2026-10-29), cash $1,378.42
- Holdings: GLD 23%, SPY 64%
- Last processed close: 2026-11-12; next decision day: 2026-11-13
- Pending orders: SPY 64%, GLD 21% (decided 2026-11-12)
- Orders so far: 4; fees $2.65

## C: 70/30 SPY/GLD, rebalanced every day (SHADOW, evidence only)

- Equity **$9,906.85** (-0.93% since 2026-10-29), cash $0.00
- Holdings: GLD 30%, SPY 70%
- Last processed close: 2026-11-12; next decision day: 2026-11-13
- Pending orders: SPY 70%, GLD 30% (decided 2026-11-12)
- Orders so far: 20; fees $2.45

Decisions use completed daily prices and fill at the next official open, exactly as backtested.
