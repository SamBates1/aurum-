# Universe coverage

Snapshot 2026-10-30 19:30 UTC from Alpaca asset list + SIP daily bars. Only instruments in this list are covered.

| | Count |
|---|---|
| Listed by Alpaca (US equities and ETFs) | 14,409 |
| Eligible for analysis | 3,924 |
| of which stocks | 2,711 |
| of which ETFs | 1,213 |
| of which commodity ETFs | 59 |

## Why instruments were excluded

| Reason | Count |
|---|---|
| trades N a day (needs N) | 5,733 |
| price $N.N below $N | 2,233 |
| not tradable at Alpaca | 899 |
| leveraged or inverse ETF (decays over time) | 880 |
| only N days of history | 413 |
| exchange OTC (OTC or other) | 309 |
| exchange TXSE (OTC or other) | 10 |
| no trade for N business days | 6 |
| no price data | 2 |

## Changes since the last snapshot

New: 0 · removed: 0 · likely ticker changes: 0

Rules: price at least $5; average daily trading at least $5M over 20 days; a trade within 5 business days; at least 60 days of history; no leveraged or inverse ETFs; listed on a main exchange.

Built in 594s; 13,189 symbols returned bars.
