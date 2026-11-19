# Paper trading status (simulated money)

## A: 70/30 SPY/GLD, monthly rebalance (MAIN)

- Equity **$9,361.37** (-6.39% since 2026-10-29), cash $0.00
- Holdings: GLD 30%, SPY 70%
- Last processed close: 2026-11-19; next decision day: 2026-12-01
- Pending orders: none
- Orders so far: 2; fees $2.30

## B: 70/30 SPY/GLD with 20% risk cap (SHADOW, evidence only)

- Equity **$9,476.58** (-5.23% since 2026-10-29), cash $1,378.42
- Holdings: GLD 22%, SPY 63%
- Last processed close: 2026-11-19; next decision day: 2026-11-20
- Pending orders: SPY 61%, GLD 21% (decided 2026-11-19)
- Orders so far: 4; fees $2.65

## C: 70/30 SPY/GLD, rebalanced every day (SHADOW, evidence only)

- Equity **$9,365.19** (-6.35% since 2026-10-29), cash $-0.00
- Holdings: GLD 30%, SPY 70%
- Last processed close: 2026-11-19; next decision day: 2026-11-20
- Pending orders: SPY 70%, GLD 30% (decided 2026-11-19)
- Orders so far: 30; fees $2.52

Decisions use completed daily prices and fill at the next official open, exactly as backtested.
