# Freqtrade

| | |
|---|---|
| Repository | https://github.com/freqtrade/freqtrade |
| Version inspected | commit `dafa0b6` (2026-10-26) |
| Licence | GPL-3.0: ideas may be reused, code may not be copied into Aurum without GPL-licensing Aurum |
| Type | Event-loop crypto bot with vectorised indicator calculation; backtesting, hyperopt, dry-run and live share one strategy class |
| Inspected by | Claude, 2026-10-27, by reading source |

## How it works (traced in source)

**Strategy contract.** A strategy computes indicators and entry/exit signal columns on a whole dataframe
(`populate_indicators`, `populate_entry_trend`, `populate_exit_trend`). The same class runs in backtest,
dry-run and live, which is how Freqtrade keeps backtest/live parity: one implementation of the rules.

**Look-ahead protection in the backtester.** `freqtrade/optimize/backtesting.py`, `_get_ohlcv_as_lists`
shifts every entry/exit signal column by one candle before the simulation loop (comment in source: signals
are taken from the previous candle to avoid using future data). Orders therefore act on the candle after
the signal. Aurum does the same (decide at close t, fill at open t+1).

**Look-ahead detection tool.** `freqtrade/optimize/analysis/lookahead.py`, class `LookaheadAnalysis`:
1. Runs a full backtest.
2. For each trade, re-runs the backtest on data truncated just after the trade's entry (and again after its
   exit) (`fill_entry_and_exit_varHolders`).
3. Flags bias if the trade no longer appears at the same time (`report_signal`) or if any indicator value
   differs between the full and truncated runs (`analyze_indicators`, using `DataFrame.compare`).
This tests the whole strategy, not just features. **Adopted in Aurum** as
`tests/test_research_tools.py::test_trade_level_lookahead_decisions_unchanged_by_future_data`.

**Recursive (warm-up) analysis.** `freqtrade/optimize/analysis/recursive.py` recomputes indicators with
different amounts of preceding history (`startup_candle` list, default 199…1999 candles) and reports
indicators whose latest values change: exponential averages (RSI, MACD) depend on where the data starts until
they have warmed up. **Adopted** as `test_recursive_analysis_features_independent_of_warmup_length`.

**Intrabar stop fills.** `_get_close_rate_for_stoploss` (backtesting.py): if the stop is above the candle's
high (price gapped through it), the exit fills at the open; otherwise at the stop price. For trailing stops
triggered on the entry candle it assumes the worst realistic path. `_get_order_filled` treats a limit
price as filled if it lies within the candle's low–high range.

**Protections (circuit breakers).** `freqtrade/plugins/protections/`:
- `max_drawdown_protection.py`: blocks trading for a period when drawdown over a lookback window exceeds
  `max_allowed_drawdown`, after at least `trade_limit` trades.
- `stoploss_guard.py`: blocks a pair (or everything) after `trade_limit` stop-outs within the lookback.
- `cooldown_period.py`, `low_profit_pairs.py`: pause after an exit / for persistently unprofitable pairs.
These are tested in Aurum as EXP-005 (`dd_breaker`, `stop_guard`).

**FreqAI (machine learning).** `freqtrade/freqai/data_kitchen.py`:
- Sliding training window of `train_period_days`, retrained every `backtest_period_days` (`split_timerange`).
  Aurum uses an expanding window instead.
- `set_weights_higher_recent`: exponential sample weights favouring recent data (`weight_factor`).
- Train/test split forces `shuffle=False` by default (time order kept).
- Outlier handling at prediction time: Dissimilarity Index (`DI_threshold`), optional SVM / DBSCAN outlier
  removal; predictions on unfamiliar inputs are marked `do_predict = 0`.
- No purge or embargo between training labels and the following period was found (`grep purge|embargo`
  only finds model-file housekeeping). Label horizon overlap is left to the user. Aurum purges explicitly.

**Hyperopt.** `freqtrade/optimize/hyperopt_loss/` offers loss functions on Sharpe, Sortino, Calmar,
drawdown and profit. No built-in correction for the number of parameter sets tried (deflated Sharpe, PBO)
was found in these modules, so heavy hyperopt invites overfitting that the tool itself does not quantify.

**Metrics (a caution).** `freqtrade/data/metrics.py`:
- `calculate_sortino` divides mean daily-ised profit by the standard deviation of *losing trades only*, and
  `calculate_sortino_from_balance` uses the std of negative daily returns. Neither is the textbook downside
  deviation (root-mean-square of below-target returns over all periods), the same error Aurum v0.1 had.
- `calculate_sharpe` mixes a per-day mean with a per-trade standard deviation.
Lesson: even mature, widely used tools report non-standard ratios; comparisons across tools need care.

**Testing.** 104 test files. `tests/optimize/test_backtest_detail.py` holds ~60 hand-built candle scenarios
(`BTContainer`: OHLC rows, signals, stop/ROI settings, expected trades and profit). This "scenario test"
pattern is exactly how Aurum's `tests/test_strategy.py` now checks fills, gaps and exits.

## Lessons for Aurum
| Idea | Status |
|---|---|
| Trade-level truncation test | Adopted (test) |
| Warm-up (recursive) test | Adopted (test) |
| Intrabar stop with gap → open | Adopted (D-012), quantified by EXP-001 |
| Drawdown / stop-loss circuit breakers | Experiment EXP-005 |
| Sliding window + recency weights (FreqAI) | Not yet tested; candidate future experiment |
| Outlier gating of predictions (DI) | Not yet tested; candidate future experiment |
| Non-standard Sortino/Sharpe | Rejected: Aurum keeps textbook definitions |
| Hyperopt without selection-bias correction | Rejected: Aurum fixes parameters a priori and reports DSR/PBO |
