# Aurum research knowledge base

The project's memory. Every investigation of a trading system, algorithm or market relationship is saved
here with its source, explanation, conclusion and proposed experiment, so later work builds on what is
already known instead of starting again.

## Start here
| File | What it holds |
|---|---|
| [PROJECT_LOG.md](PROJECT_LOG.md) | Chronological record of everything done and learned |
| [decisions.md](decisions.md) | Every design decision, its reason, and what would change it |
| [transfer-matrix.md](transfer-matrix.md) | All ideas found so far (43), classified Adopt / Adapt / Experiment / Reject |
| [sources.md](sources.md) | Papers, articles, repositories (pinned commits) and tools, with links |
| [frameworks/](frameworks/README.md) | Source-code notes: Freqtrade, LEAN, Backtrader, VectorBT, Zipline-reloaded |
| [topics/](topics/) | Evidence reviews: [gold](topics/gold-evidence.md), [regimes](topics/regimes.md), [ML vs simple](topics/ml-vs-simple.md), [sizing & risk](topics/sizing-and-risk.md), [mean reversion](topics/mean-reversion.md), [alternative signals](topics/alternative-signals.md), [new ideas 2026-10-29](topics/new-ideas-2026-10-29.md), [overfitting statistics](topics/overfitting-statistics.md), [intraday trading](topics/intraday.md) |
| [experiments/](experiments/README.md) | Protocol, acceptance rules, pre-registered experiments EXP-001…028, research lab, results |
| [templates/](templates/) | Templates for new source notes and experiments |

## Workflow for a new idea
1. **Discover** it; add the source to `sources.md`.
2. **Inspect** the implementation (pin the commit) or the paper; write a note in `frameworks/` or `topics/`
   using `templates/source-note.md`. Separate what was verified from what was assumed.
3. **Compare** with Aurum and add a row to `transfer-matrix.md`.
4. If it's worth testing, **pre-register** `experiments/EXP-xxx.md` (from the template) *before* running,
   and add the variant to `aurum/experiments.py`.
5. **Run** `python run_experiments.py` on real data and commit the results folder.
6. **Record** the verdict in the EXP file and any change of design in `decisions.md`; update `PROJECT_LOG.md`.

## Ground rules
- Never present synthetic or unreproduced results as real. Synthetic runs are git-ignored.
- Never copy code from GPL or Commons-Clause projects; reimplement from papers.
- Record failed ideas too; they are as valuable as successes.
