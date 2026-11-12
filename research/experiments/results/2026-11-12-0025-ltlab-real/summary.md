# EXP-054 results: a loss limit for long-term stock holdings

Run 2026-11-12 00:25 UTC. 1000 stocks, Alpaca daily adjusted prices to 2026-11-11, results from 2017-01-01. Up to 12 stocks by 12-1 momentum, monthly; 10 bps per fill; cash earns nothing.

**Survivorship bias:** today's survivors only. It flatters every variant's return and understates what a loss limit would have saved (collapsed, delisted stocks are missing).

| Variant | Growth a year | Worst fall | Sharpe | Worst fall 2017-20 | Worst fall 2021-26 | Trades | Loss-limit exits | Worst holding | Invested | Passes |
|---|---|---|---|---|---|---|---|---|---|---|
| A_none | +30.5% | -61.1% | 0.80 | -45.2% | -61.1% | 145 | 0 | -76.8% | 99% | control |
| B_plan_level | +32.2% | -59.5% | 0.83 | -42.7% | -59.5% | 147 | 27 | -76.8% | 98% | **no** |
| C_fixed_20pct | +27.4% | -62.6% | 0.76 | -42.0% | -62.6% | 188 | 100 | -45.5% | 97% | **no** |

**Decision under the pre-registered rule: A_none.**

Pass rule: worst fall at least 20% smaller than the control's, growth no more than 1.0 point a year lower, and the worst fall not larger than the control's in either half.

Run time 183s.
