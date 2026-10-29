# EXP-033: Stop-losses, exits and circuit breakers for an always-invested portfolio

| Field | |
|---|---|
| Status | Run 2026-10-29: every stop, exit and breaker rejected |
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

## Results (real data, 2026-10-29; `results/2026-10-29-1440-plab-core-real/` (open fills), `…-1441-plab-core-real-closefill/`, `…-1442-plab-other-real/`)
| Variant | Core, open: pre / dev / holdout ΔSharpe | Core, close | Other assets | Whole-period max DD (traded −39.1%) | Verdict |
|---|---|---|---|---|---|
| trail_15pct | −0.14 / −0.20 / −0.13 | −0.15 / −0.20 / −0.08 | −0.34 / −0.14 / −0.16 | −38.7% | REJECT |
| trail_25pct | −0.04 / −0.06 / −0.04 | −0.02 / −0.07 / −0.04 | −0.16 / −0.18 / −0.07 | −37.7% | REJECT |
| trend_exit_200 | +0.04 / −0.32 / +0.02 | +0.04 / −0.37 / −0.00 | +0.21 / −0.14 / −0.16 | −22.5% | REJECT |
| trend_half_200 | +0.02 / −0.13 / +0.03 | +0.02 / −0.16 / +0.02 | +0.07 / −0.03 / −0.05 | −31.1% | REJECT |
| trim_overextended | −0.01 / −0.00 / +0.06 | 0.00 / −0.01 / +0.05 | 0.00 / −0.01 / +0.02 | −38.9% | REJECT |
| breaker_15 | +0.07 / −0.04 / −0.00 | +0.07 / −0.18 / +0.02 | +0.07 / −0.11 / −0.02 | −29.4% | REJECT |
| breaker_25 | +0.02 / −0.06 / +0.00 | +0.02 / −0.08 / −0.00 | −0.06 / +0.00 / 0.00 | −33.6% | REJECT |
| weekly_loss_limit | −0.00 / −0.02 / +0.01 | −0.01 / −0.01 / +0.00 | −0.02 / +0.01 / +0.00 | −39.7% | REJECT |
| equity_curve_filter | −0.10 / −0.05 / +0.01 | −0.13 / −0.11 / +0.04 | −0.07 / −0.08 / +0.08 | −31.1% | REJECT |

**Conclusion:** stops and exits make the worst fall smaller but cost more in lost return than they save; this
confirms EXP-005, EXP-013 and EXP-023 in a fourth setting. The 15% drawdown breaker is the most interesting near-miss
(whole-period Sharpe 0.40 vs 0.37, worst fall −29% vs −39%, 2011–15 loss −28% vs −38%) but it fails in development,
badly with close fills (−0.18), so its gain depends on a few episodes: not adopted. The trend exit is the clearest
case of "less invested, not better": smallest falls, much lower return.
