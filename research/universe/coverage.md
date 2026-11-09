# Universe coverage

Snapshot 2026-11-09 00:14 UTC from Alpaca asset list + SIP daily bars. Only instruments in this list are covered.

| | Count |
|---|---|
| Listed by Alpaca (US equities and ETFs) | 14,390 |
| Eligible for analysis | 3,967 |
| of which stocks | 2,733 |
| of which ETFs | 1,234 |
| of which commodity ETFs | 62 |

## Why instruments were excluded

| Reason | Count |
|---|---|
| trades N a day (needs N) | 5,705 |
| price $N.N below $N | 2,234 |
| not tradable at Alpaca | 903 |
| leveraged or inverse ETF (decays over time) | 871 |
| only N days of history | 384 |
| exchange OTC (OTC or other) | 309 |
| exchange TXSE (OTC or other) | 10 |
| no trade for N business days | 6 |
| no price data | 1 |

## Changes since the last snapshot

New: 23 · removed: 42 · likely ticker changes: 5

- ALDF -> ALDFF
- ALDFU -> ALDUF
- ALDFW -> ALDWF
- GNTA -> SAEN
- NMZ.RTWI -> NMZ.RT

Rules: price at least $5; average daily trading at least $5M over 20 days; a trade within 5 business days; at least 60 days of history; no leveraged or inverse ETFs; listed on a main exchange.

Built in 80s; 13,167 symbols returned bars.
