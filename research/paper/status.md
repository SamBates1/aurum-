# Paper trading status (simulated money)

## A: 70/30 SPY/GLD, monthly rebalance (MAIN)

- Equity **$9,304.86** (-6.95% since 2026-10-29), cash $0.00
- Holdings: GLD 29%, SPY 71%
- Last processed close: 2026-11-25; next decision day: 2026-12-01
- Pending orders: none
- Orders so far: 2; fees $2.30

## B: 70/30 SPY/GLD with 20% risk cap (SHADOW, evidence only)

- Equity **$9,440.79** (-5.59% since 2026-10-29), cash $3,122.76
- Holdings: GLD 22%, SPY 45%
- Last processed close: 2026-11-25; next decision day: 2026-11-26
- Pending orders: SPY 45%, GLD 18% (decided 2026-11-25)
- Orders so far: 6; fees $3.00

## C: 70/30 SPY/GLD, rebalanced every day (SHADOW, evidence only)

- Equity **$9,308.20** (-6.92% since 2026-10-29), cash $-0.00
- Holdings: GLD 30%, SPY 70%
- Last processed close: 2026-11-25; next decision day: 2026-11-26
- Pending orders: SPY 70%, GLD 30% (decided 2026-11-25)
- Orders so far: 38; fees $2.58

Decisions use completed daily prices and fill at the next official open, exactly as backtested.
