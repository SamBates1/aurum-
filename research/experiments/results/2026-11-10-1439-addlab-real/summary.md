# EXP-053 results: add to swing winners or not

Run 2026-11-10 14:39 UTC. 1487 trades (same entries as EXP-052). Profit per trade as a share of the original position's value, after 5 bps per fill. Same-day ties: stop first.

| Variant | Mean | Median | Win rate | Avg win | Avg loss | Worst | Best | Added | Exits |
|---|---|---|---|---|---|---|---|---|---|
| A_no_add | +2.21% | -2.58% | 44% | +16.92% | -9.31% | -55.61% | +99.79% | 0% | stop 47%, time 29%, target 24%, end 0% |
| B_add_half | +1.61% | -4.40% | 34% | +21.28% | -8.65% | -55.61% | +114.93% | 46% | stop 41%, time 21%, target 20%, breakeven 18%, end 0% |
| C_add_full | +1.72% | -5.60% | 33% | +25.45% | -10.09% | -66.35% | +133.12% | 46% | stop 41%, time 21%, target 20%, breakeven 18%, end 0% |

| Variant vs A | Mean difference | NW t | 2017-20 | 2021-26 | 2024+ | Optimistic | Passes |
|---|---|---|---|---|---|---|---|
| B_add_half | -0.39% | -1.53 | -0.22% | -0.50% | -0.43% | -0.37% | **no** |
| C_add_full | -0.14% | -0.39 | +0.10% | -0.30% | -0.13% | -0.12% | **no** |

**Decision under the pre-registered rule: A_no_add.**

Run time 338s.
