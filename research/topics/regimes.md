# Regime detection

Priority 3. Status: literature reviewed 2026-10-27; simple regime gates pre-registered as EXP-003.

## Question
Should Aurum change behaviour when real yields, the dollar, volatility or the trend change, or does regime
switching add complexity without measurable benefit?

## Evidence
- **HMM regime allocation can work out of sample**, per a DTU study (Nystrup et al.): an adaptively estimated
  two-state Gaussian HMM outperformed static rebalancing after costs, with a realistic delay, on a
  stock/bond/commodity index universe. It is one study on one universe, and success depended on modelling
  non-stationarity. [S8]
- **But regime classifiers often don't create a tradable edge.** A Quantpedia analysis of four-state HMMs
  (2010–2023 test window) found the model mainly *reduced exposure in stress*: lower drawdown, but it did not
  beat a static portfolio with the same average exposure or a simple volatility-targeting rule, and a
  permutation test showed no timing skill. It also lists the traps: using smoothed (future-aware) instead of
  filtered state estimates, fitting scalers/parameters on test data, single random starts, and selection
  metrics dominated by calm periods. [S9]
- **The gold/real-yield regime itself shifted in 2022** (see [gold-evidence.md](gold-evidence.md)): any regime
  rule learned on 2010–2021 is exposed to that break.

## Design decision for Aurum
- Start with **transparent, rule-based gates** using information known at each close (real-yield direction
  over 63 days, VIX > 30, dollar above its 200-day average, gold below its 200-day average). These are
  interpretable and cheap to test; see EXP-003.
- Compare against a **matched-exposure baseline**: the acceptance rule for risk improvements uses
  drawdown *per unit of volatility*, so a gate that simply holds more cash doesn't count as better.
- **HMMs: deferred** (transfer matrix: Reject for now). Reasons: the evidence that they beat vol targeting is
  weak, they add estimation risk (local optima, state-label switching), and Aurum already volatility-targets.
  Reconsider only if a rule-based gate shows value and a smoother version is wanted.

## Already in Aurum
`aurum/stats.py::make_regimes` reports returns by asset trend, VIX level and real-yield direction (labels
shifted one day so they are known in advance), in the research report.
