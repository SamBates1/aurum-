# Master brief: final status report (2026-10-29)

Answer to *AURUM MASTER PROMPT — full quantitative research, implementation, validation and continuous improvement*.
Every performance number is a **historical backtest** (not paper or live trading), net of costs, with the data
period, universe, costs and validation design stated in the linked experiment file.

## 1. Repository, pull request and CI
| Item | Status |
|---|---|
| Branch with the Quant Desk work | `feature/quant-desk-chat`: PR #1 **merged into `main`** at the owner's request (2026-10-29 22:22) |
| CI failure in run 40948109121 (format) | **Implemented and verified**: fixed; PR CI run 40958394327 passed on Python 3.11 and 3.12 (lint, format, tests, backtest smoke test) |
| `main` CI | **Implemented and verified**: passing on the latest commits |
| Tests | 131 on the merged branch, all passing locally on Python 3.11 and 3.12 and in CI |
| Merging PR #1 | **Done** (owner approved) |

## 2. Quant Desk and daily report
| Item | Status |
|---|---|
| Desk roles and team debate | **Implemented and verified** with stubbed and local-server tests: the four specialist prompts are called, then the reviewer prompt; the desk now states that every role is the **same model with different prompts** |
| Connection to a real model | **Blocked**: no Ollama or hosted model is available in this environment. Verified instead: the full HTTP request path against a local OpenAI-compatible stub server, and a clear error when nothing is listening |
| Failure handling | **Implemented and verified**: unreachable endpoint, HTTP 429/500, timeout, invalid JSON, missing fields, empty answer, missing research files |
| Provider visibility, no secrets in logs, audit log of answers | **Implemented and verified** |
| Reading experiment records and results | **Implemented and verified**: by experiment ID only (no other paths), plus the registry and latest result folders |
| Daily report: documented command | **Bug fixed and verified**: it failed with `ModuleNotFoundError: aurum` |
| Daily report: stale-data flags, synthetic labelling, relative strength, drawdowns, correlations, strategy targets, chart | **Implemented and verified** offline |
| Daily report on real data | **Implemented and verified**: workflow run 40965317378 succeeded and uploaded its artifact (14-day retention); a copy generated the same way is committed at [monitoring/daily-report-2026-10-29.md](monitoring/daily-report-2026-10-29.md) and checked (last bar 2026-10-29, after the close; no stale tickers) |
| Scheduled workflow | **Configured** on `main` (weekdays 21:30 UTC); the first *scheduled* run will happen on the next weekday, so a scheduled run has not yet been observed |

## 3. Strategy integrity audit (Part B)
| Finding | Status |
|---|---|
| Headline result reproduced from scratch | **Verified**: 5.5% CAGR, Sharpe 0.36 (previously 0.37, one more day of data), worst fall −39.1%, exposure 47% (`experiments/results/2026-10-29-2105-plab-core-real/`, commit ee74907) |
| Backtest uses the documented rule | **Verified** (D-005 test; the ML score is not traded in vol_hold mode) |
| Overlapping 5-day labels | Deliberate and handled: purge gap = horizon; point-in-time skill; block bootstrap |
| Sortino formula; stops never lowered | Fixed in v0.2; regression tests present |
| Ledger: cash, fees, realised + unrealised P&L, restart | **Verified** by a new property test over random trades |
| Macro timing | FRED lagged 2 business days; latest revisions, not vintages (documented limitation) |
| Fundamentals and news sentiment | Live context only, weight 0, never in backtests (verified) |
| Execution timing | Next-open fills; robust to 1–5 days' delay (EXP-044) |
| Corporate actions, survivorship | Adjusted prices; survivorship remains a limitation (asset list chosen in 2026) |
| Data quality (35 series) | **Verified**: [audits/data-audit-2026-10-29.md](audits/data-audit-2026-10-29.md). Defects: CPER bad prints; FRED credit spread only 3 years; futures OHLC unreliable (D-031) |
| Cache could return too-short history | **Confirmed defect, fixed**, regression test |
| Checkpoints reusable after code changes | **Confirmed defect, fixed** (code fingerprint in the key), regression test |
| Results not tied to code/data versions | **Fixed**: git commit, code fingerprint and data fingerprint in every new result |
| Dashboard caching after config edits | Limitation: config is read at start-up, so restart the app after editing `config.yaml` |

## 4. Experiments completed (all pre-registered; figures in each result folder)
| ID | Question | Result |
|---|---|---|
| [EXP-037](experiments/EXP-037-beat-sp500.md) | Beat the S&P 500? (mixes, risk parity, leverage) | **Rejected after testing**: none beat SPY (11.3% a year); leverage did not help; 70/30 SPY/GLD matched SPY's return with Sharpe 0.69 vs 0.56 and −38% vs −55% worst fall |
| [EXP-038](experiments/EXP-038-trend-momentum.md) | 11 trend/momentum rules + cross-sectional momentum, 10 assets | **Rejected after testing** (halve drawdowns, give up equal return) |
| [EXP-039](experiments/EXP-039-mean-reversion-pairs.md) | Mean reversion; pairs and cointegration | **Rejected after testing**; no pair stably cointegrated |
| [EXP-040](experiments/EXP-040-volatility-models.md) | GARCH, EWMA, HAR, GVZ; VaR | GVZ best forecast and VaR calibration; portfolio effects inconclusive |
| [EXP-041](experiments/EXP-041-candlesticks.md) | 18 candlestick patterns, 492 tests | **Rejected after testing**: 0 discoveries after multiple-testing correction |
| [EXP-042](experiments/EXP-042-ml-models.md) | Logistic L1/L2, random forest, gradient boosting | **Rejected after testing**: AUC ≈ 0.50, no stable edge |
| [EXP-043](experiments/EXP-043-macro-lead-lag.md) | Dollar, real yields, breakevens, credit, VIX, copper, curve | 9 development-period links, **none confirmed** in both other periods |
| [EXP-044](experiments/EXP-044-execution-delay.md) | Execution delay and costs | **Passed**: Sharpe 0.36–0.37 with up to 5 days' delay; 0.35 at 2× costs |
| [EXP-045](experiments/EXP-045-sp500-gold-mix.md) | Is S&P + gold robust? Downturn protection? | **Mix confirmed robust** (80/20–60/40, any rebalancing, both fills): 11.3% a year like SPY, worst fall −38% vs −55%. Protections failed the strict test; risk cap a near miss (Sharpe 0.81, worst fall −26%) |

Earlier in the project: EXP-001…036 (registry in [experiments/README.md](experiments/README.md)).

## 5. Graphs generated
For each of EXP-037…044: equity and drawdown curves, rolling return/volatility/Sharpe/correlation with SPY, annual
returns, return distributions, tail losses, exposure and weights, turnover and costs, gross vs net, Sharpe by period
and by calendar year, rule × asset heatmaps, candlestick charts with SMA/EMA, Bollinger, Donchian, volume and RSI,
pattern t-statistics and effects, calibration/ROC/prediction distributions, AUC and information-coefficient heatmaps,
feature stability, signal-strength buckets, volatility forecasts, VaR breaches, cost/delay curves, gold vs dollar and
real yields, cross-asset levels, rolling correlations, lead-lag curves, correlation heatmaps, asset drawdowns.
Also for EXP-045: mix Sharpe grid, downturn bars, rolling 3-year returns. Not generated: SHAP plots (no model showed skill worth explaining) and trade-level entry/exit markers (the adopted
strategy rebalances rather than trading discrete entries and exits).

## 6. Paper trading
Safety checks (off switch, stale/bad prices, one order per asset per day, order and position limits, cash), structured
decision records, ledger reconciliation and restart are **implemented and verified** by tests; the dashboard shows a
clear "simulated" label, strategy/config/code version, orders against the daily limit and data freshness. Alpaca is
**not implemented** (needs the owner's paper account). Real money stays disabled.

## 7. Remaining risks and limitations
Backtests only; survivorship (asset list chosen in 2026); FRED latest revisions; free adjusted data; the 2024–2026
holdout has been viewed many times; ~100 portfolio variants and >500 statistical tests have now been run, so any new
"winner" needs a large, confirmed effect.

## 8. Recommended next actions (evidence-based)
1. Done: PR #1 merged and the daily report verified on real data.
2. **Owner chose both goals** (profit and downturn protection, D-033). Evidence-based options: 70/30 SPY/GLD (passed
   every test) or 70/30 with the 20%-volatility risk cap (near miss; smaller falls). Owner to choose which to paper-trade.
3. Connect Alpaca paper trading with the existing safety layer, then judge it by the pre-written rules in
   [paper-trading-plan.md](paper-trading-plan.md).
4. Quarterly: rerun the labs on months after 2026-10-29 (genuinely new data) before trusting any change.
