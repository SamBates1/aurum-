# How the leading backtesting engines work (and what Aurum takes from them)

Source-code notes for each system, at pinned commits:
[Freqtrade](freqtrade.md) · [LEAN](lean.md) · [Backtrader](backtrader.md) · [VectorBT](vectorbt.md) ·
[Zipline-reloaded](zipline-reloaded.md)

## Side-by-side

| Concern | Freqtrade | LEAN | Backtrader | VectorBT | Zipline-reloaded | Aurum v0.3 |
|---|---|---|---|---|---|---|
| Engine style | Vectorised indicators + event loop | Event-driven, C# | Event-driven | Vectorised (Numba) | Event-driven | Vectorised features + event loop per sleeve |
| When a signal fills | Next candle (signals shifted by 1) | Next data event; fill models per asset | Next bar open (unless `coc`/`coo` cheats) | **Same bar close by default** (`price=np.inf`) | Next bar close + impact | Next open |
| Stop fills | Stop price; open if gapped | Stop price; open if gapped | Trigger price; open if gapped | Stop price; open if gapped | Stop orders (fill logic not inspected) | Stop price; open if gapped (D-012) |
| Slippage | Via fees/price settings | Pluggable per security | `slip_perc`/`slip_fixed`, volume filler | `slippage` % | Volume-share quadratic impact, 2.5% volume cap | Per-ticker bps + sensitivity 0–50 bps |
| Look-ahead tooling | `lookahead-analysis` (truncation), `recursive-analysis` (warm-up) | Design: data delivered to the algorithm in time order | Design (relative indexing) | User's responsibility | 1-session shift in pipeline | Truncation tests for features, walk-forward, decisions; warm-up test |
| ML | FreqAI: sliding window, recency weights, outlier gating; no purge | Any via Python | None built in | None built in | None built in | Expanding walk-forward, purge, skill-weighted vote |
| Risk controls | Stoploss, trailing, ROI table, Protections | Risk models (drawdown, per-security, sector) | Stop/trail orders | sl/tp/trailing | Order types | ATR stop, vol targeting, sleeve caps; breakers under test |
| Overfitting control | Hyperopt losses; no selection-bias correction found | Parameter optimiser (not inspected) | Parameter optimiser (not inspected) | Deflated Sharpe function | None found | Pre-registration, holdout, block bootstrap, DSR, PBO |
| Backtest/live parity | Same strategy class (dry-run/live) | Same engine, swapped handlers | Live broker "stores" (not inspected) | Research only | Research only | Same `strategy.py` for backtest, dashboard, bot, paper |
| Sortino definition | Std of losing trades/days (non-standard) | n/a here | n/a here | Proper downside risk | n/a here | Proper downside deviation |
| Licence | GPL-3.0 | Apache-2.0 | GPL-3.0 | Apache-2.0 + Commons Clause | Apache-2.0 | – |

## Conclusions
1. **The industry convention for stops is intrabar with a gap rule.** All four engines that model stops fill
   at the stop price when the bar trades through it and at the open when the price gapped past it. Aurum
   v0.2 checked the close and exited the next morning, which also disagreed with its own paper trader.
   Fixed in v0.3 (D-012); EXP-001 measures the difference.
2. **Defaults are where look-ahead and mis-measurement hide**: VectorBT's same-bar close fills and 365-day
   year, Backtrader's annual-return Sharpe, Freqtrade's Sortino. Aurum documents every convention in code.
3. **Truncation testing at strategy level** (Freqtrade) is the most practical look-ahead defence and is now
   part of Aurum's test suite, along with the warm-up test.
4. **No framework should replace Aurum's engine now** (D-013). The engines solve problems Aurum doesn't have
   (thousands of symbols, intraday data, broker integrations) at the cost of heavy setup, and two are GPL.
   Aurum's simulator is ~300 lines, fully tested and easy to audit, which matters more for a research
   project. Revisit if Aurum moves to live broker execution (LEAN would then be the strongest candidate).
