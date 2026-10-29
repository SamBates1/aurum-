# EXP-033: Stop-losses, exits and circuit breakers for an always-invested portfolio

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, before any portfolio-lab result on real data |
| Origin | Owner's brief §4, §5, §6 |

## Stop-order mechanics (for the record)
A **stop trigger** is the price that activates the order. A **stop-market** order then sells at the best available price:
it always executes, but after a gap it can fill well below the trigger. A **stop-limit** order sells only at the limit
price or better: it controls the price but may not execute at all in a fast fall, leaving the position open. Aurum's
backtests fill stops at the trigger, or at the open if the price gapped through it (D-012), which models a stop-market.

## Variants (fixed before running)
- `trail_15pct`, `trail_25pct`: an asset goes to cash for 21 trading days when its close is 15% (25%) below the highest
  close since (re-)entry. (ATR trailing stops were already rejected: EXP-005, EXP-023.)
- `trend_exit_200`: an asset is held only while above its 200-day average (signal-based exit). `trend_half_200`: half
  weight below it.
- `trim_overextended` (partial profit-taking): ×0.75 while more than 20% above the 200-day average.
- Portfolio circuit breakers on the account's own equity: `breaker_15` (halve everything when 15% below the peak, until
  back within 7.5% or 126 days pass), `breaker_25` (25% / 12.5%), `weekly_loss_limit` (halve for 5 days after a 5% loss
  over 5 days), `equity_curve_filter` (halve while equity is below its own 100-day average).
- Time-based exits do not apply to an always-invested strategy (there is no "trade" to time out).

## Acceptance criteria
Lab rules plus the out-of-asset check. A rule that passes only by holding less on average (lower exposure, same Sharpe)
is reported as "less invested, not better": the risk path already measures drawdown per unit of volatility for this
reason. A rule that cuts risk after losses and re-buys later is examined for "delayed recognition" through its recovery
time (longest period below a previous peak) and its stress-window losses, compared with the traded rule.

Portfolio-lab rules (README, 'Portfolio lab'); run with `python run_plab.py --set core` (and `--fill close`, `--set other`).

## Results
_Not yet run on real data._
