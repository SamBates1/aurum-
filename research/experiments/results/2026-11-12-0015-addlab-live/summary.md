# EXP-053 results: add to swing winners or not

Run 2026-11-12 00:15 UTC. 2025 trades (same entries as EXP-052). Profit per trade as a share of the original position's value, after 5 bps per fill. Same-day ties: stop first.

**Corrected re-run (audit, D-048):** live scanner filters and the live one-day limit entry; original pass rule, unchanged.

| Variant | Mean | Median | Win rate | Avg win | Avg loss | Worst | Best | Added | Exits |
|---|---|---|---|---|---|---|---|---|---|
| A_no_add | +0.58% | -2.45% | 41% | +10.65% | -6.48% | -29.67% | +52.77% | 0% | stop 52%, time 25%, target 23%, end 0% |
| B_add_half | +0.15% | -3.55% | 31% | +13.60% | -5.93% | -31.42% | +73.60% | 45% | stop 45%, breakeven 19%, target 19%, time 17%, end 0% |
| C_add_full | +0.07% | -4.68% | 30% | +16.26% | -6.94% | -45.51% | +94.42% | 45% | stop 45%, breakeven 19%, target 19%, time 17%, end 0% |

| Variant vs A | Mean difference | NW t | 2017-20 | 2021-26 | 2024+ | Optimistic | Passes |
|---|---|---|---|---|---|---|---|
| B_add_half | -0.39% | -3.28 | -0.28% | -0.47% | -0.77% | -0.37% | **no** |
| C_add_full | -0.44% | -2.74 | -0.21% | -0.60% | -0.99% | -0.42% | **no** |

**Decision under the pre-registered rule: A_no_add.**

Run time 155s.
