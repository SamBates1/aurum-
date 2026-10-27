# Position sizing and risk management

Priority 5. Status: literature and framework review 2026-10-27; experiments EXP-001, EXP-005, EXP-007.

## Evidence
- **Stop-losses only help when returns trend.** Kaminski & Lo show that under a random walk a simple
  stop-loss always lowers expected return; with momentum or regime switching it can add value. Their
  1950–2004 test found stop-loss rules outperformed during stopped-out periods (before frictions). [S14]
  → Whether Aurum's 2-ATR stop helps is an empirical question about gold's serial correlation: EXP-005
  includes `no_stop`.
- **Volatility targeting** cuts tail risk in all asset classes but improves Sharpe mainly for equity-like
  assets (Harvey et al. 2018) [S7]; Moreira & Muir (2017) report large gains for equity factors. [S6]
- **Circuit breakers** in production systems: Freqtrade's `MaxDrawdown` and `StoplossGuard` protections and
  LEAN's `MaximumDrawdownPercentPortfolio` risk model pause or liquidate after losses
  (see [../frameworks/](../frameworks/README.md)).

## Execution realism (found in the framework review)
All four engines that model stop orders fill them **intrabar**: at the stop price when the bar trades through
it, at the open after a gap. Aurum v0.2 checked the close and exited next morning, which understated losses
on gap days in some cases and overstated them in others, and disagreed with its own paper trader (which
checks the live price). **Changed in v0.3** (D-012); EXP-001 quantifies the difference.

## Current Aurum rules
Long-only sleeves capped at min(20%, 1/N); exposure = min(1, 15% / realised vol), fixed at entry; 2-ATR stop
filled intrabar, never loosened; re-entry needs a fresh signal; no trading on stale data.

## Experiments
EXP-005: no stop, chandelier trailing stop (3 ATR), sleeve drawdown breaker (15%, 21-day pause), stop-loss
guard (2 stops in 60 days → 30-day pause), no vol targeting, 10% and 20% vol targets.
EXP-007: profit target and maximum holding period (triple-barrier exits).

## Not adopted
- **Correlation-aware construction (risk parity, mean-variance)**: with six highly correlated gold assets,
  estimation error would dominate; equal sleeves + vol targeting approximate risk parity. Revisit if the
  universe broadens (e.g. adding copper, oil, bonds).
- **Portfolio-level drawdown breaker**: needs a joint multi-asset simulation; the per-sleeve version is tested
  first.
