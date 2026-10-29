# Continuous improvement plan (brief §12.10)

Goal: notice when the strategy stops working, and test new ideas, **without** fitting the bot to recent luck.

## Monitoring (automatic, once paper trading runs)
| What | How often | Alarm when |
|---|---|---|
| Rolling return vs "what normal looks like" | Daily | Below the 1st percentile for the elapsed window ([paper-trading-plan.md](paper-trading-plan.md)) |
| Tracking vs backtest replay | Weekly | Weights more than 2 points off on more than 5% of days, or return gap above 2 points |
| Costs and fill quality | Monthly | More than 2× the assumed costs |
| Data health (Yahoo, FRED, GVZ, Alpaca) | Every run | Stale or missing data; GVZ fallback in use for more than 5 days |
| Realised volatility | Monthly | Outside 8%–18% a year for 3 months running |
| Safety checks | Every run | Any blocked order, duplicate, or record/broker mismatch |

## Re-testing on genuinely new data
- Each quarter, rerun `run_plab.py` and `run_lab.py`. The months since 2026-10-29 are **new out-of-sample data**: they
  were not available when any rule was chosen, so they are the fairest test the project has.
- Report the strategy's results on the new months separately from the history.

## Adding a new idea
1. Write it in `experiments/EXP-xxx.md` with fixed parameters and acceptance rules **before** running.
2. Test it with the lab rules (development, pre-2013, holdout, other assets, 2× costs, DSR).
3. If it passes, also require it to hold on the months **after** its registration date before adopting it.
4. Count every idea ever tried. About 70 variants have been tried so far; the deflated Sharpe ratio must allow for
   all of them, so a new idea needs a bigger result to count.
5. Record the result, pass or fail, in the registry, the transfer matrix and `decisions.md`.

## What is never done
- Re-tuning parameters on the latest months (the robustness grid showed the current settings sit in a flat region,
  so there is nothing to gain and much to lose).
- Switching strategies after a bad quarter that is inside the normal range.
- Raising risk, enabling real money or removing a safeguard without the owner's recorded approval.

## Review
Every 6 months: a short written review (what happened, against which expectations, what was learned), added to
`PROJECT_LOG.md`.
