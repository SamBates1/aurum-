# EXP-052: Should swing trades take profit in steps (a "ladder") instead of all at one target?

| Field | |
|---|---|
| Status | Pre-registered 2026-11-10, before any run |
| Origin | Owner's question on the GILD swing trade (bought $171.02, stop $161.05, target $189.95): sell parts at $176, $179, $184 and $189.95 instead of all at $189.95? |
| Scope | Swing pot only. The long-term pot keeps no price targets (EXP-005, 013, 023, 033, 049) |

## Question
With the swing pot's existing entry, stop and 28-day time stop unchanged, does selling the position in four equal
parts on the way up give a better result per trade than selling it all at the 2R target?

## Data (fixed)
- Universe and prices: as EXP-051 (the 1,000 largest eligible US stocks in the universe snapshot, Alpaca daily
  consolidated prices from 2016-01-01, adjusted). Trades from 2017-01-01, so every level has a year of history. Survivorship bias as stated there; it affects all variants equally
  because they share the same entries.
- Entries: every Friday close, the **10** stocks with the highest `trend_strength` (3-month return, only where ADX(14)
  > 25 and the close is above the 50-day average): the signal the swing pot uses as its live test (D-045). Weekly
  rather than daily to keep the trade count manageable; a stock already in an open test trade is skipped.
- Every variant trades exactly the same entries; only the exits differ, so the comparison is paired.

## Trade rules (the live swing plan, `aurum/investplan.py`)
- Levels set at the signal close `C`: ATR(14); support = the highest confirmed swing low (5 bars either side, last 260
  days) below `C`; stop `S = max(support − 0.25·ATR, C − 2·ATR)`; risk per share `R = C − S`.
- Entry at the next open. If that open is more than 0.25·ATR away from `C` (outside the live entry zone), no trade.
- Each day: if the open is already beyond a level, that part fills at the open; otherwise a level touched by the day's
  low/high fills at the level. **If the stop and a target are both touched on the same day, the stop is assumed to come
  first** (conservative; the optimistic ordering is reported as a check).
- Time stop: whatever is left is sold at the first open at least 28 calendar days after entry.
- Costs: 5 basis points of the traded value on every fill (spread; Alpaca charges no commission).

## Variants (three, fixed in advance; no others will be run)
| ID | Exits |
|---|---|
| A (control) | all at `C + 2R` (today's rule) |
| B ladder | a quarter each at `C + 0.5R`, `C + 1R`, `C + 1.5R`, `C + 2R` (the owner's GILD ladder was 0.5R, 0.8R, 1.3R, 1.9R) |
| C ladder + breakeven | as B, and once the first quarter has sold, the stop on the rest moves up to `C` |

## Measures
Return per trade after costs (in % and in R), win rate, average win and loss, share of trades ending at each exit,
and the sum of weekly average trade returns over time. Paired differences B − A and C − A per trade.

## Pass rule (fixed before running)
A ladder variant replaces the single target in the swing pot only if **all** hold:
1. Its mean return per trade is higher than A's, with a Newey-West t-statistic of at least 2.0 on the weekly average
   paired difference (trades in the same week are not independent).
2. The difference is positive in both halves (2017–2020 and 2021–2026, as EXP-051).
3. It is not negative from 2024 onwards.
4. It still holds with the optimistic same-day ordering.
If both B and C pass, the one with the larger t-statistic is chosen. Otherwise the single 2R target stays. Two
comparisons are made, so a t of 2.0 is a modest bar; a near miss is reported as such, not adopted.

## Limitations stated in advance
Daily bars cannot show the order of moves within a day; the conservative ordering handles the worst case. The signal
itself failed EXP-051a, so this test can show which exit is better *for these entries*, not that swing trading pays.
