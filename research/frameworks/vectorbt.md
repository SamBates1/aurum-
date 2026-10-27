# VectorBT (open-source)

| | |
|---|---|
| Repository | https://github.com/polakowo/vectorbt |
| Version inspected | commit `8e30b8c` (2026-10-23) |
| Licence | Apache-2.0 **with Commons Clause** (no selling the software). Reimplement ideas from papers rather than copying code |
| Type | Vectorised, Numba-compiled backtester built for testing thousands of parameter combinations at once |
| Inspected by | Claude, 2026-10-27, by reading source |

## How it works (traced in source)

**Signals → portfolio.** `Portfolio.from_signals` (`vectorbt/portfolio/base.py`) turns boolean entry/exit
arrays into orders, broadcasting over parameter grids. The order price defaults to `np.inf`
(`vectorbt/portfolio/enums.py`, `Order.price`), which the engine interprets as the **current bar's close**.
A signal computed from bar t's close is therefore filled at that same close unless the user shifts signals
or supplies `price=open` with shifted signals: a common source of look-ahead in published VectorBT
backtests. Aurum fills at the next open.

**Stops.** `get_stop_price_nb` (`vectorbt/portfolio/nb.py`): a long stop at `entry × (1 − stop)` fills at the
open if the open is already through it, at the stop price if the bar's low–high range contains it, otherwise
not at all. Take-profits (`tp_stop`) and trailing stops (`sl_trail`) use the same logic. Same convention as
LEAN/Backtrader/Freqtrade (Aurum D-012).

**Annualisation default (a caution).** Returns statistics need `year_freq`; the global default in
`vectorbt/_settings.py` is `"365 days"`, suited to crypto. For daily stock data that mis-annualises Sharpe and
volatility unless set to 252 trading days.

**Overfitting statistics.** `vectorbt/returns/metrics.py` implements the expected maximum Sharpe under the
null and the Deflated Sharpe Ratio (Bailey & López de Prado). Aurum implements these independently from the
published formulas in `aurum/stats.py` (`expected_max_sharpe`, `deflated_sharpe`, `probabilistic_sharpe`),
plus PBO via CSCV, which VectorBT open-source does not provide.

**Downside risk** is computed correctly (`downside_risk_nb`, relative to a required return over all periods),
unlike Freqtrade's Sortino.

**Testing.** 13 test files (large ones) covering the Numba kernels.

## Lessons for Aurum
| Idea | Status |
|---|---|
| Parameter sweeps | Used carefully: experiment grids are small and pre-registered, with DSR/PBO reported |
| Deflated Sharpe | Adopted (own implementation) |
| Same-bar close fills by default | Rejected; documented as a pitfall |
| 365-day annualisation default | Rejected; Aurum uses 252 trading days |
| Adopting VectorBT | Rejected (D-013): Aurum's loop simulator is fast enough (~20 ms per run) and easier to audit; licence restricts commercial use |
