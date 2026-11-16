# Universe coverage

Snapshot 2026-11-16 00:29 UTC from Alpaca asset list + SIP daily bars. Only instruments in this list are covered.

| | Count |
|---|---|
| Listed by Alpaca (US equities and ETFs) | 14,406 |
| Eligible for analysis | 3,954 |
| of which stocks | 2,726 |
| of which ETFs | 1,228 |
| of which commodity ETFs | 63 |

## Why instruments were excluded

| Reason | Count |
|---|---|
| trades N a day (needs N) | 5,729 |
| price $N.N below $N | 2,249 |
| not tradable at Alpaca | 908 |
| leveraged or inverse ETF (decays over time) | 871 |
| only N days of history | 365 |
| exchange OTC (OTC or other) | 311 |
| exchange TXSE (OTC or other) | 12 |
| no trade for N business days | 6 |
| no price data | 1 |

## Changes since the last snapshot

New: 47 · removed: 31 · likely ticker changes: 9

- ACHV -> QUIT
- CLGN -> OPHI
- EZRA -> XGPU
- KAZR -> CRMN
- PTLE -> ZYN
- RITRF -> RITRD
- SHNY -> GLLD
- TCBI -> TXCP
- TCBI.PRB -> TXCP.PRB

Rules: price at least $5; average daily trading at least $5M over 20 days; a trade within 5 business days; at least 60 days of history; no leveraged or inverse ETFs; listed on a main exchange.

Built in 50s; 13,174 symbols returned bars.
