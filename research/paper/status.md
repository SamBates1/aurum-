# Paper trading status (simulated money)

## A: 70/30 SPY/GLD, monthly rebalance (MAIN)

- Equity **$9,542.96** (-4.57% since 2026-10-29), cash $0.00
- Holdings: GLD 30%, SPY 70%
- Last processed close: 2026-11-18; next decision day: 2026-12-01
- Pending orders: none
- Orders so far: 2; fees $2.30

## B: 70/30 SPY/GLD with 20% risk cap (SHADOW, evidence only)

- Equity **$9,634.25** (-3.66% since 2026-10-29), cash $1,378.42
- Holdings: GLD 22%, SPY 63%
- Last processed close: 2026-11-18; next decision day: 2026-11-19
- Pending orders: SPY 62%, GLD 21% (decided 2026-11-18)
- Orders so far: 4; fees $2.65

## C: 70/30 SPY/GLD, rebalanced every day (SHADOW, evidence only)

- Equity **$9,546.09** (-4.54% since 2026-10-29), cash $0.00
- Holdings: GLD 30%, SPY 70%
- Last processed close: 2026-11-18; next decision day: 2026-11-19
- Pending orders: SPY 70%, GLD 30% (decided 2026-11-18)
- Orders so far: 28; fees $2.50

Decisions use completed daily prices and fill at the next official open, exactly as backtested.
