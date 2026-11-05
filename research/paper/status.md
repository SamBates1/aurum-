# Paper trading status (simulated money)

## A: 70/30 SPY/GLD, monthly rebalance (MAIN)

- Equity **$9,853.29** (-1.47% since 2026-10-29), cash $0.00
- Holdings: GLD 32%, SPY 68%
- Last processed close: 2026-11-05; next decision day: 2026-12-01
- Pending orders: none
- Orders so far: 2; fees $2.30

## B: 70/30 SPY/GLD with 20% risk cap (SHADOW, evidence only)

- Equity **$9,857.22** (-1.43% since 2026-10-29), cash $742.04
- Holdings: GLD 24%, SPY 68%
- Last processed close: 2026-11-05; next decision day: 2026-11-06
- Pending orders: SPY 70%, GLD 24% (decided 2026-11-05)
- Orders so far: 3; fees $2.52

## C: 70/30 SPY/GLD, rebalanced every day (SHADOW, evidence only)

- Equity **$9,849.20** (-1.51% since 2026-10-29), cash $0.00
- Holdings: GLD 31%, SPY 69%
- Last processed close: 2026-11-05; next decision day: 2026-11-06
- Pending orders: SPY 70%, GLD 30% (decided 2026-11-05)
- Orders so far: 10; fees $2.34

Decisions use completed daily prices and fill at the next official open, exactly as backtested.
