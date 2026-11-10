# EXP-053: Should the swing pot add to trades that are working?

| Field | |
|---|---|
| Status | Pre-registered 2026-11-10, before any run |
| Origin | Owner: "evaluate which stocks are doing well and buy more". EXP-052 found swing profits come from a few trades that run far, which makes adding plausible; EXP-032 (gold assets, +25% in uptrends) found no gain |
| Scope | Swing pot only |

## Data and entries
Identical to EXP-052: the 1,000 largest eligible US stocks, Alpaca daily adjusted prices, trades from 2017-01-01, the
top 10 `trend_strength` stocks each Friday, the live swing stop, a single 2R target, the 28-day time stop, 5 bps per
fill, and a day touching both the stop and another level counts the stop first (optimistic ordering reported).

## Variants (three, fixed; no others will be run)
| ID | Rule |
|---|---|
| A (control) | no adding (today's rule) |
| B add half | the first time the price reaches `C + 1R`, buy 50% more shares at that level (at the open if it gaps above) and move the stop for the whole position to `C`. Position cap 15% of the pot |
| C add full | as B, but buy 100% more. Position cap 20% of the pot |
The target (`C + 2R`) and the time stop apply to the whole position. On the day of the add, if the low also reaches
`C`, the add is assumed to come first and the stop after it (the worst case).

## Measure
Profit per trade after costs as a share of the *original* position's value (so a trade with an add can earn or lose
more than one without), plus win rate, worst trade, exits, and how often an add happened.

## Pass rule (fixed before running)
B or C is adopted only if, against A: mean profit per trade higher with a Newey-West t of at least 2.0 on weekly
averages of the paired difference; positive in 2017–2020 and in 2021–2026; not negative since 2024; still positive with
the optimistic ordering; **and** its worst trade is no worse than A's. If both pass, the one with the larger t is
chosen. Otherwise the swing pot does not add.

## Limitations
As EXP-052: daily bars, survivorship bias (equal for all variants), and the entry signal itself failed EXP-051a.
