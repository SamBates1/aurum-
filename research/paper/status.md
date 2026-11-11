# Paper trading status (simulated money)

## A: 70/30 SPY/GLD, monthly rebalance (MAIN)

- Equity **$10,014.10** (+0.14% since 2026-10-29), cash $0.00
- Holdings: GLD 30%, SPY 70%
- Last processed close: 2026-11-11; next decision day: 2026-12-01
- Pending orders: none
- Orders so far: 2; fees $2.30

## B: 70/30 SPY/GLD with 20% risk cap (SHADOW, evidence only)

- Equity **$10,038.31** (+0.38% since 2026-10-29), cash $742.04
- Holdings: GLD 23%, SPY 70%
- Last processed close: 2026-11-11; next decision day: 2026-11-12
- Pending orders: SPY 63%, GLD 22% (decided 2026-11-11)
- Orders so far: 3; fees $2.52

## C: 70/30 SPY/GLD, rebalanced every day (SHADOW, evidence only)

- Equity **$10,016.20** (+0.16% since 2026-10-29), cash $0.00
- Holdings: GLD 30%, SPY 70%
- Last processed close: 2026-11-11; next decision day: 2026-11-12
- Pending orders: SPY 70%, GLD 30% (decided 2026-11-11)
- Orders so far: 18; fees $2.42

Decisions use completed daily prices and fill at the next official open, exactly as backtested.
