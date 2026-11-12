# EXP-054: Should long-term stock holdings have a loss limit?

| Field | |
|---|---|
| Status | Pre-registered 2026-11-12, before any run |
| Origin | Audit of 11 Nov 2026 (D-048): every stop test so far used funds or gold assets; the long-term stock pot has no exit at its own "invalidation level", and two holdings were down more than 20% with no rule that acts |
| Scope | Long-term pot only. Says nothing about whether the pot's stock picks beat the market (EXP-051a: they did not) |

## Hypothesis
A single company can fall and not recover in a way a fund usually does. A loss limit on each holding should make the
pot's worst fall clearly smaller without costing more return than it saves.

## Data
As EXP-051: the 1,000 largest eligible US stocks in the universe snapshot, Alpaca daily adjusted prices from
2016-01-01, results from 2017-01-01. Survivorship bias as stated there. It affects this test in a known direction:
stocks that collapsed and were delisted are missing, which **understates** what a loss limit would have saved.

## Rules shared by all variants (the long-term pot, simplified)
- On the first trading day of each month, at the close: rank stocks priced at least $10 with at least $20M traded a
  day (20-day average) by 12-1 month momentum (the pot's live-test signal).
- Hold up to 12 stocks. Fill empty places with the best-ranked stocks not already held, each bought at the next open
  with one twelfth of the pot's value at that time. (The live pot buys in thirds; that is left out to keep one
  difference between variants.)
- Sell at the next open a holding that is ranked below 150 or no longer eligible on a monthly check.
- 10 basis points per fill. Uninvested cash earns nothing.

## Variants (three, fixed; no others will be run)
| ID | Extra exit |
|---|---|
| A (control) | none (today's rule) |
| B plan level | sell at the next open after any daily close below the plan's own invalidation level, fixed on the day the stock was chosen: the lower of (200-day average − ATR(14)) and (close − 2 × ATR(14)), as `investplan.build` computes it |
| C fixed 20% | sell at the next open after any daily close 20% or more below the purchase price |
A stock sold by B or C can be bought again at a later monthly check if it still ranks in the top places.

## Measures
Growth a year, worst fall of the pot (peak to trough), Sharpe (daily, no risk-free rate), worst single holding,
number of trades, share of time invested.

## Pass rule (fixed before running; the shape of EXP-049's risk path)
B or C is adopted only if, against A, **all** hold:
1. its worst fall is at least 20% smaller (for example −40% to −32% or better);
2. its growth a year is no more than 1.0 percentage point lower;
3. its worst fall is not larger than A's in either half (2017–2020, 2021–2026).
If both pass, the one with the smaller worst fall is chosen. Otherwise the long-term pot keeps no loss limit.

## Trials
Two (B and C). Running total about 116.
