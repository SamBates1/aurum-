# EXP-049: Do a stop-loss and take-profit improve the 70/30 strategy?

| Field | |
|---|---|
| Status | Pre-registered 2026-10-30 15:20 UK, before any run on real data |
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

## Results
_Not run yet._
