# EXP-049: Do a stop-loss and take-profit improve the 70/30 strategy?

| Field | |
|---|---|
| Status | Pre-registered 2026-10-30 15:20 UK; run 2026-10-30 on real data: none passed (2 failed, 1 inconclusive) |
| Origin | Live-charts build plan, stage 3 (trade plans need tested exits); owner's end goal D-036 |

## Question
The trade-plan panel shows a stop and targets for every ticker. Before any strategy *uses* them, test whether adding a
per-asset stop-loss / take-profit to the main strategy (A: 70/30 SPY/GLD, monthly rebalance) would have helped.

## Method (fixed before running)
- New engine exit `stop_target`: levels fixed at the close on which a position starts; a daily close at or beyond
  either level sells that asset at the next open; it stays out for the cooldown, then is bought again if the rules
  still want it (fresh levels). Exits are acted on at that close, not at the next month-end.
- Three variants, all identical to A otherwise (benchmark: A itself):
  1. `exp049-atr-2-4`: stop 2 x ATR(14), target 4 x ATR(14), 10 days out after an exit
  2. `exp049-atr-3-6`: stop 3 x ATR(14), target 6 x ATR(14), 10 days out
  3. `exp049-pct-10-stop`: 10% stop, no target, 21 days out
- Judged by the standard Fair Test (designer run on real data since 2006): signal path (ΔSharpe ≥ 0.10, ≥ 80% of
  bootstrap resamples better, still ≥ 0 at 2x costs) or risk path (worst fall or volatility ≥ 20% better), then DSR
  ≥ 0.5 (trials counted from the registry + 100 earlier variants), then the 2024+ holdout AND pre-2013 must both
  hold, plus look-ahead, accounting, execution-delay and ±20% sensitivity checks. Each variant is one registered trial.
- **Prior expectation: fail.** EXP-033 rejected every stop and exit tried on these assets (smaller worst falls, but
  more return lost than saved); EXP-005 and EXP-023 rejected ATR trailing stops.
- Decision rule: a pass makes a variant a *candidate* shadow strategy only; nothing changes in A or the paper
  accounts without the owner's approval. A fail means trade plans keep showing stops as information, labelled as
  untested for this strategy.

## Results (real data, 2006-06 to 2026-10-30; `research/designer/2026-10-30-1512-real/`, reports in `research/fairtests/2026-10-30-exp049-*`)
Benchmark A: development Sharpe 0.73, CAGR 10.3%, whole-period worst fall −38.5%.

| Variant | Verdict | Development Sharpe (A 0.73) | Dev CAGR (A 10.3%) | Whole-period worst fall | Why |
|---|---|---|---|---|---|
| ATR stop 2 / target 4 | **FAILED** | 0.54 | 6.3% | −32.3% | Sells winners too early; 60 orders a year; lower return than the smaller falls save. DSR 0.20 |
| ATR stop 3 / target 6 | **FAILED** | 0.69 | 8.4% | −42.8% (worse than A) | Whipsaw in 2008: stopped out, bought back higher, fell again. Also fails the delay and ±20% checks |
| 10% stop, no target | **INCONCLUSIVE** | 0.73 | 10.3% | −29.2% | Never triggers in 2013-2026 (identical to A); only helped in 2008. DSR 0.40 |

**Conclusion (as predicted):** a fixed stop-loss or take-profit does not improve the 70/30 strategy. Take-profit
targets hurt the most, by selling the winners. The 10% stop only mattered once (2008), which is one event, not
evidence. Consistent with EXP-033. Nothing changes in A or the paper accounts. The trade plan keeps showing a stop and
targets as risk information, and the summary says they are not part of the tested strategy.
