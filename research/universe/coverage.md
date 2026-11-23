# Universe coverage

Snapshot 2026-11-23 00:25 UTC from Alpaca asset list + SIP daily bars. Only instruments in this list are covered.

| | Count |
|---|---|
| Listed by Alpaca (US equities and ETFs) | 14,425 |
| Eligible for analysis | 3,958 |
| of which stocks | 2,682 |
| of which ETFs | 1,276 |
| of which commodity ETFs | 68 |

## Why instruments were excluded

| Reason | Count |
|---|---|
| trades N a day (needs N) | 5,616 |
| price $N.N below $N | 2,368 |
| not tradable at Alpaca | 916 |
| leveraged or inverse ETF (decays over time) | 868 |
| only N days of history | 370 |
| exchange OTC (OTC or other) | 308 |
| exchange TXSE (OTC or other) | 13 |
| no trade for N business days | 6 |
| no price data | 2 |

## Changes since the last snapshot

New: 61 · removed: 42 · likely ticker changes: 5

- ACH -> ACCH
- EVFM -> EVFMD
- GWHT -> GWHTQ
- MERC -> MERCQ
- PLCE -> PLCEQ

Rules: price at least $5; average daily trading at least $5M over 20 days; a trade within 5 business days; at least 60 days of history; no leveraged or inverse ETFs; listed on a main exchange.

Built in 106s; 13,186 symbols returned bars.
