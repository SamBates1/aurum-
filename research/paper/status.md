# Paper trading status (simulated money)

## A: 70/30 SPY/GLD, monthly rebalance (MAIN)

- Equity **$9,957.96** (-0.42% since 2026-10-29), cash $0.00
- Holdings: GLD 31%, SPY 69%
- Last processed close: 2026-11-10; next decision day: 2026-12-01
- Pending orders: none
- Orders so far: 2; fees $2.30

## B: 70/30 SPY/GLD with 20% risk cap (SHADOW, evidence only)

- Equity **$9,973.93** (-0.26% since 2026-10-29), cash $742.04
- Holdings: GLD 23%, SPY 69%
- Last processed close: 2026-11-10; next decision day: 2026-11-11
- Pending orders: SPY 65%, GLD 22% (decided 2026-11-10)
- Orders so far: 3; fees $2.52

## C: 70/30 SPY/GLD, rebalanced every day (SHADOW, evidence only)

- Equity **$9,958.31** (-0.42% since 2026-10-29), cash $0.00
- Holdings: GLD 30%, SPY 70%
- Last processed close: 2026-11-10; next decision day: 2026-11-11
- Pending orders: SPY 70%, GLD 30% (decided 2026-11-10)
- Orders so far: 16; fees $2.40

Decisions use completed daily prices and fill at the next official open, exactly as backtested.
