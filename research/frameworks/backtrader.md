# Backtrader

| | |
|---|---|
| Repository | https://github.com/mementum/backtrader |
| Version inspected | commit `b853d7c` (2023-04-19; no commits since, effectively unmaintained) |
| Licence | GPL-3.0: ideas only, no code copying |
| Type | Event-driven Python engine with "lines" (time-indexed series accessed relative to the current bar) |
| Inspected by | Claude, 2026-10-27, by reading source |

## How it works (traced in source)

**Look-ahead protection by indexing.** Strategies read `data.close[0]` (current bar) and `[-1]` (previous);
there is no positive index into the future in normal use, which makes look-ahead hard by construction.

**Market orders fill on the next bar's open.** `backtrader/brokers/bbroker.py`, `_try_exec_market`: an order
cannot execute on the bar that created it unless *cheat-on-open* (`coo`) is set; the fill price is the next
bar's open (with optional slippage). Setting *cheat-on-close* (`coc`) fills at the signal bar's close, a
documented convenience that is, in effect, a look-ahead switch. Aurum has no such switch.

**Stop orders.** `_try_exec_stop`: for a sell stop, if the bar opens at or below the trigger the fill is at the
open ("price penetrated with an open gap"); if the low reaches the trigger during the bar, the fill is at the
trigger. Trailing stops are adjusted on the close (`trailadjust`). Same convention as LEAN, VectorBT and
Freqtrade (Aurum D-012).

**Slippage.** Broker parameters `slip_perc` / `slip_fixed`, `slip_open`, `slip_match` (cap slippage at the
bar's high/low), `slip_out`. A volume `filler` can limit fills to a share of bar volume.

**Analyzer defaults (a caution).** `backtrader/analyzers/sharpe.py`, `SharpeRatio` defaults to
`timeframe=TimeFrame.Years`, `riskfreerate=0.01`, `annualize=False`, population standard deviation: a Sharpe
computed from a handful of annual returns unless the user changes it. Results from different tools are not
comparable without checking such defaults.

**Testing.** 83 test files, mostly indicator and analyzer regression checks against stored values.

## Lessons for Aurum
| Idea | Status |
|---|---|
| Next-bar-open market fills | Already in Aurum |
| Stop gap rule | Adopted (D-012) |
| Volume-limited fills | Not needed: Aurum's notional is tiny relative to GLD/miner volumes |
| `coc`-style shortcuts | Rejected: never offer a same-bar fill option |
| Framework adoption | Rejected: unmaintained since 2023, GPL |
