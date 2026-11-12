# EXP-052 results: one 2R target vs a profit-taking ladder (swing trades)

Run 2026-11-12 00:12 UTC. 1000 stocks, Alpaca daily adjusted prices to 2026-11-11 00:00:00. 2025 trades from 2017-01-01 (top 10 `trend_strength` each Friday); skipped: {'no_next_day': 10, 'outside_entry_zone': 114, 'bad_levels': 0, 'already_held': 2945}. Costs 5 bps per fill. Same-day stop and target: stop first.

**Survivorship bias:** today's survivors only; it flatters every variant equally (same entries).

**Corrected re-run (audit, D-048):** only stocks passing the live swing scanner's filters (price at least $10, $20M a day, ATR 1-6%), entered with the live one-day limit order. Original pass rule, unchanged.

**Against simply holding:** the single-target trades averaged +0.58% each; every stock in the test, held for the same 28 days, averaged +1.92%. Trades are often shorter than 28 days, so this is a rough comparison, not a test.

| Variant | Mean per trade | Median | Mean R | Win rate | Avg win | Avg loss | Worst | Exits |
|---|---|---|---|---|---|---|---|---|
| A_single_2R | +0.58% | -2.45% | +0.09 | 41% | +10.66% | -6.48% | -29.68% | stop 52%, time 25%, target 23%, end 0% |
| B_ladder | +0.36% | -0.53% | +0.06 | 47% | +7.01% | -5.55% | -29.68% | stop 52%, time 25%, target 23%, end 0% |
| C_ladder_breakeven | -0.29% | +0.30% | -0.03 | 55% | +3.65% | -5.15% | -29.68% | breakeven 49%, stop 33%, target 11%, time 7%, end 0% |

## Paired comparison with A (per trade, weekly averages)

| Variant | Mean difference | NW t | 2017-20 | 2021-26 | 2024+ | Optimistic ordering | Passes |
|---|---|---|---|---|---|---|---|
| B_ladder | -0.20% | -1.66 | -0.30% | -0.13% | -0.29% | -0.18% | **no** |
| C_ladder_breakeven | -0.72% | -3.18 | -0.76% | -0.69% | -1.34% | -0.68% | **no** |

**Decision under the pre-registered rule: A_single_2R.**

Pass rule: mean difference > 0 with NW t >= 2, positive in both halves, not negative since 2024, and still positive with the optimistic ordering.

Run time 159s.
