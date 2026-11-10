# EXP-052 results: one 2R target vs a profit-taking ladder (swing trades)

Run 2026-11-10 13:16 UTC. 1000 stocks, Alpaca daily adjusted prices to 2026-11-09 00:00:00. 1487 trades from 2017-01-01 (top 10 `trend_strength` each Friday); skipped: {'no_next_day': 10, 'outside_entry_zone': 970, 'bad_levels': 0, 'already_held': 2676}. Costs 5 bps per fill. Same-day stop and target: stop first.

**Survivorship bias:** today's survivors only; it flatters every variant equally (same entries).

| Variant | Mean per trade | Median | Mean R | Win rate | Avg win | Avg loss | Worst | Exits |
|---|---|---|---|---|---|---|---|---|
| A_single_2R | +2.21% | -2.58% | +0.11 | 44% | +16.94% | -9.31% | -55.63% | stop 47%, time 29%, target 24%, end 0% |
| B_ladder | +1.42% | -0.44% | +0.07 | 49% | +11.23% | -8.03% | -55.63% | stop 47%, time 29%, target 24%, end 0% |
| C_ladder_breakeven | +0.24% | +0.73% | -0.01 | 64% | +5.34% | -8.81% | -55.63% | breakeven 49%, stop 28%, target 12%, time 10%, end 0% |

## Paired comparison with A (per trade, weekly averages)

| Variant | Mean difference | NW t | 2017-20 | 2021-26 | 2024+ | Optimistic ordering | Passes |
|---|---|---|---|---|---|---|---|
| B_ladder | -0.88% | -3.81 | -0.90% | -0.87% | -1.07% | -0.86% | **no** |
| C_ladder_breakeven | -2.03% | -4.63 | -1.93% | -2.10% | -2.57% | -1.99% | **no** |

**Decision under the pre-registered rule: A_single_2R.**

Pass rule: mean difference > 0 with NW t >= 2, positive in both halves, not negative since 2024, and still positive with the optimistic ordering.

Run time 140s.
