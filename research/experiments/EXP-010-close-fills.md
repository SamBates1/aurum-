# EXP-010: Are results an artefact of opening-price fills?

| Field | |
|---|---|
| Status | Run 2026-10-29: results **robust** to the fill assumption |
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

## Results (real data, 2026-10-29 12:12 UTC; `results/2026-10-29-1212-real/` vs `results/2026-10-29-1212-real-closefill/`)

| Check | Open fills | Close fills | Pass? |
|---|---|---|---|
| 1. Baseline development Sharpe | −0.02 | −0.08 (change 0.06 < 0.10) | Yes |
| 2. Baseline vs buy & hold | Lower Sharpe (−0.02 vs 0.30), smaller max DD (−21.4% vs −43.0%) | Lower Sharpe (−0.08 vs 0.30), smaller max DD (−20.5% vs −43.0%) | Yes, same ranking |
| 3. Verdict flips REJECT ↔ KEEP | No KEEPs | No KEEPs | Yes |

**Conclusion: the earlier conclusions do not depend on opening-price fills.** Closing-price fills make the
baseline slightly worse (development CAGR 0.8% → 0.3%), so open fills were mildly flattering, but nothing changes
the overall picture. Default stays `open` (D-018); future headline results should also be checked with
`--fill close`.

Notable differences: several verdicts move between REJECT and INCONCLUSIVE, showing how close to zero most
effects are. The miner-vs-GDX relative-value rule (EXP-006) looks much stronger with close fills (ΔSharpe +0.25,
better in 96% of resamples, DSR 0.42) than with open fills (+0.08): worth a dedicated follow-up, since a result
that depends this much on the fill assumption needs explaining before it is trusted.
