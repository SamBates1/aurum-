# Paper-trading plan, promotion rules and deployment checklist

Written 2026-10-29, **before** paper trading starts, so the results cannot shape the rules (brief §11).

## Why the rules focus on behaviour, not profit
The strategy's long-run Sharpe ratio is about 0.37. At that level, telling skill from luck needs decades of returns;
six months of results say very little. In the backtest, **39% of all 3-month windows and 37% of 6-month windows lost
money** (EXP-036). So paper trading is judged mainly on whether the bot **behaves exactly as tested**, safely and
reliably, and on whether its results stay inside the range the backtest says is normal.

## What normal looks like (traded rule, every window 2006–2026, EXP-036)
| Window | 5th percentile | Median | 95th percentile | 1st percentile |
|---|---|---|---|---|
| 1 month | −5.1% | +0.5% | +6.0% | −7.6% |
| 3 months | −8.7% | +1.6% | +11.7% | −12.5% |
| 6 months | −10.7% | +2.9% | +19.0% | −17.2% |
| 1 year | −13.2% | +4.5% | +30.0% | −20.5% |

## Stage 1: dry run (at least 5 trading days)
The bot computes orders and writes decision records but sends nothing. Pass: every planned order matches a manual
check of the target weights; no check fails unexpectedly; records are complete.

## Stage 2: paper trading on Alpaca (at least 6 months and 120 trading days)
**Pass all of these** to be considered for real money:
1. **Reliability:** at least 99% of scheduled runs complete; no order is ever placed while a check fails; zero
   duplicate orders; any difference between the bot's records and Alpaca's positions is fixed within one trading day.
2. **Tracking the backtest:** each asset's weight within 2 points (of the account) of the backtest target on at least
   95% of days; the paper return differs from a backtest replay of the same days by less than 2 percentage points.
3. **Costs and fills:** average difference between fill price and the expected (opening) price, plus commissions, no
   more than 2× the assumed costs (3–10 bps one way).
4. **Risk:** realised volatility between 8% and 18% a year; drawdown never worse than the 1st percentile above for the
   elapsed window.
5. **Return:** inside the 5th–95th percentile range for the elapsed window. A positive return is **not** required,
   because a loss over 6 months happens in more than a third of all windows even for a working strategy; it is
   reported, not used as a pass mark.

**If any rule fails:** stop, diagnose the cause (code, data, execution or market), record it in `decisions.md`,
fix or return to research, and restart the 6-month clock. Never relax a rule to make the bot pass.

## Deployment checklist
**Before paper trading on Alpaca**
- [ ] Alpaca paper account created by the owner; API keys stored only as GitHub repository secrets (never in chat,
      code or files); `.env` git-ignored.
- [ ] Code refuses to run against Alpaca's live (real-money) address; paper address hard-coded.
- [ ] Off switch tested (`live.trading_enabled: false` and the `STOP_TRADING` file).
- [ ] All tests pass in CI, including execution-failure tests (stale data, bad price, duplicate order, API error).
- [ ] Stage 1 dry run passed.
- [ ] Daily summary and alert on any blocked order or mismatch working.

**Before any real money (separate decision by the owner; not automatic)**
- [ ] Stage 2 passed in full, recorded in `decisions.md`.
- [ ] Owner has read the strategy report, including its weaknesses: no better return per unit of risk than holding,
      falls of 30–40% possible, recovery can take years (about 9 years after 2011).
- [ ] Start with a controlled amount (no more than 10% of the intended capital) for at least 3 months, under the same
      rules; increase only by a further recorded decision.
- [ ] Separate real-money keys, and a written emergency procedure: off switch, then sell to cash manually if needed.

## Emergency procedure
1. Create the `STOP_TRADING` file or set `live.trading_enabled: false`: all new orders stop at once.
2. Check Alpaca's positions against the bot's records.
3. If positions must be closed, do it in the Alpaca dashboard (paper) by hand.
4. Record what happened and why in `decisions.md` before restarting.
