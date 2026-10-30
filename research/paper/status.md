# Paper trading status (simulated money)

## A: 70/30 SPY/GLD, monthly rebalance (MAIN)

- Equity **$9,898.59** (-1.01% since 2026-10-29), cash $0.00
- Holdings: GLD 30%, SPY 70%
- Last processed close: 2026-10-30; next decision day: 2026-11-02
- Pending orders: none
- Orders so far: 2; fees $2.30

## B: 70/30 SPY/GLD with 20% risk cap (SHADOW, evidence only)

- Equity **$9,898.59** (-1.01% since 2026-10-29), cash $0.00
- Holdings: GLD 30%, SPY 70%
- Last processed close: 2026-10-30; next decision day: 2026-11-02
- Pending orders: SPY 70%, GLD 29% (decided 2026-10-30)
- Orders so far: 2; fees $2.30

## C: 70/30 SPY/GLD, rebalanced every day (SHADOW, evidence only)

- Equity **$9,898.59** (-1.01% since 2026-10-29), cash $0.00
- Holdings: GLD 30%, SPY 70%
- Last processed close: 2026-10-30; next decision day: 2026-11-02
- Pending orders: SPY 70%, GLD 30% (decided 2026-10-30)
- Orders so far: 2; fees $2.30

Decisions use completed daily prices and fill at the next official open, exactly as backtested.
