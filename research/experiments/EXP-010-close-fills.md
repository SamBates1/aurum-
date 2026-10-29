# EXP-010: Are results an artefact of opening-price fills?

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, before any close-fill run |
| Origin | Quantpedia, *Dangers of Relying on OHLC Prices* [S20]; see [../topics/new-ideas-2026-10-29.md](../topics/new-ideas-2026-10-29.md) |
| Current Aurum equivalent | Every order decided at the close of day t fills at the daily "open" of t+1 |

## Hypothesis
Aurum's conclusions do not depend on the opening-price assumption. Daily opens are the first print, often small
and not tradable in size; closing prices match the closing auction (market-on-close orders), which a retail
account can use. If the conclusions change when every order fills at the next **close**, the earlier results
were partly an artefact of unrealistic fills.

## Design
Rerun the whole experiment registry with `python run_experiments.py --fill close` (orders decided at close t
fill at the close of t+1; stops still fill intrabar). Same data, dates, costs and acceptance rules. This is a
robustness check of the *engine*, so it does not add trials to any variant's DSR.

## Acceptance criteria (stated before running)
Results are **robust** if, comparing the close-fill run with the open-fill run:
1. the baseline's development Sharpe changes by less than 0.10;
2. the baseline's ranking against buy & hold (better/worse Sharpe, smaller/larger drawdown) is unchanged;
3. no variant's verdict moves from REJECT to KEEP or from KEEP to REJECT.

If any of these fail, the open-fill results are treated as unreliable, and the default fill switches to
`close` (a decision recorded in `../decisions.md`).

## Results
_Not yet run._
