# Aurum

**A research system for gold, silver and gold-mining equities:** walk-forward machine learning, macro drivers, a
cost-aware backtester, honest benchmarks and a paper-trading dashboard.

[![CI](https://github.com/SamBates1/aurum-/actions/workflows/ci.yml/badge.svg)](https://github.com/SamBates1/aurum-/actions/workflows/ci.yml)

> Educational research project. Nothing here is investment advice, and paper trading uses simulated money only.

## Objective

Test, with realistic assumptions, whether a combination of macro data (real yields, the dollar, volatility),
technical signals and a machine-learning model can time gold and mining-equity exposure better than simply holding
them. The project prioritises correct methodology over headline returns: every result is out-of-sample, after costs,
compared against simple alternatives and reported with uncertainty intervals.

## Results

Results are generated, not written by hand. Run `python run_research.py` (needs internet) to produce
[`reports/latest/report.md`](reports/latest/report.md) with charts, tables, the untouched-holdout results and data
provenance. The report states the run date, git commit and config fingerprint. Offline runs produce a separate
`reports/latest-synthetic/` report, clearly marked as synthetic and never committed.

## Architecture

```mermaid
flowchart LR
    Y[Yahoo Finance<br/>prices, macro, news] --> D[data.py<br/>validate · cache · lag]
    F[FRED<br/>real yields, breakevens, T-bills] --> D
    D --> FE[features.py<br/>technical · macro · cross-asset]
    FE --> M[model.py<br/>walk-forward GBM]
    M --> S[strategy.py<br/>ONE scoring rule,<br/>sizing, stops, simulator]
    FE --> S
    S --> B[backtest.py + benchmarks.py<br/>metrics, portfolio]
    B --> R[run_research.py<br/>report, charts, bootstrap]
    S --> P[pipeline.decide<br/>live signal]
    P --> UI[app.py dashboard]
    P --> BOT[run_bot.py]
    UI --> PP[paper.py<br/>paper portfolio]
    BOT --> PP
```

The key design decision: **`strategy.py` defines the trading rule once.** The backtest, the live dashboard, the
headless bot and the paper portfolio all call it, and `tests/test_pipeline.py` checks that a live decision equals the
backtested decision for the same inputs.

```
aurum/
  config.py      loads config.yaml (every research choice lives there)
  data.py        downloads, validation, disk cache with provenance, publication lags
  features.py    technical, macro and cross-asset features; labels
  model.py       walk-forward training, purging, diagnostics (AUC, Brier, log loss, calibration)
  strategy.py    scoring rule, decisions, position sizing, stops, cash/share simulator
  backtest.py    performance metrics, benchmark-relative stats, portfolio aggregation
  benchmarks.py  buy & hold, cash, trend, momentum, ML-only, ML-without-macro
  stats.py       stationary block bootstrap, regimes, yearly returns
  signals.py     plain-English reasons; live-only sentiment/fundamental scores
  sentiment.py   headline sentiment (VADER + finance lexicon)
  paper.py       paper portfolio with the same rules as the backtest
  pipeline.py    research() (daily, slow) and decide() (every refresh, fast)
app.py           Streamlit dashboard
run_research.py  full study → results/<timestamp>/ and reports/latest/
run_experiments.py  pre-registered experiments vs the baseline → research/experiments/results/
aurum/experiments.py  experiment variants (EXP-001…007)
research/        knowledge base: framework source-code notes, evidence reviews, decisions, experiments
run_backtest.py  quick per-ticker backtest
run_bot.py       headless signal loop, optional paper trading
tests/           72 tests: look-ahead, accounting, metrics, risk controls, data handling, research tools
```

## Setup

Python 3.10+.

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

No API keys are needed: Yahoo Finance and FRED are used without credentials. `.env.example` lists optional settings.

## Running it

| Command | What it does |
|---|---|
| `python run_research.py` | Full study: strategy vs benchmarks, development vs holdout, model diagnostics, cost and threshold sensitivity, bootstrap intervals, regimes, charts and report (a few minutes) |
| `python -m streamlit run app.py` | Dashboard: live signals with reasons, backtest vs benchmarks, paper portfolio, macro charts |
| `python run_experiments.py` | Runs every pre-registered experiment (trend, regimes, models, risk overlays, mean reversion, triple-barrier) against the baseline with DSR, PBO and automatic verdicts (20–40 minutes) |
| `python run_backtest.py [TICKERS]` | Quick strategy backtest per ticker |
| `python run_bot.py --paper` | Headless loop: refresh, decide, paper-trade every 60 s |
| `AURUM_OFFLINE=1 <any command>` | Same, on clearly labelled synthetic data (no internet) |
| `pytest` / `ruff check .` | Tests and lint (also run by GitHub Actions on every push) |

Configuration is in [`config.yaml`](config.yaml): universe, macro series, model settings, strategy weights and
thresholds, risk limits, cost assumptions and the holdout date.

## Data

| Source | Series | Use | Limitations |
|---|---|---|---|
| Yahoo Finance | Daily OHLCV for GLD, SLV, GDX, NEM, AEM, WPM; dollar index, 10y yield, VIX, gold and oil futures, S&P 500 | Prices, execution, features | Split/dividend-adjusted; free data with occasional gaps; today's bar is partial until 16:00 New York |
| FRED | 10y TIPS real yield (DFII10), 10y breakeven (T10YIE), 3-month T-bill (DTB3) | Macro features, cash return, risk-free rate | Latest revision rather than original vintage; shifted 2 business days to the date it was known |
| Yahoo Finance | Headlines, fundamentals snapshot | Live context only | No point-in-time history, so never used in backtests and weight 0 by default |

Every download is validated (sorted unique dates, positive prices) and cached under `data/cache/` with its source and
retrieval time. A failed download falls back to the cache **with a visible warning**; nothing is fabricated.

## Strategy (v0.4: always invested, sized by risk)

Adopted on 2026-10-29 after experiments EXP-014 and EXP-017 passed their pre-registered rules on real data
with both open- and close-price fills ([decisions D-020, D-021](research/decisions.md)).

For each of the six assets, every day at the close:

1. **Forecast its risk.** 21-day realised volatility, scaled by gold's implied/realised volatility ratio: the CBOE
   gold volatility index (GVZ) divided by GLD's own 21-day volatility, clipped to 0.5–2. When options price more
   risk than has recently occurred, every position is cut; when they price less, positions grow.
2. **Set the target weight** = min(1, 15% / forecast volatility) of the asset's sleeve (each sleeve is
   `min(20%, 1/N)` of the portfolio). Always invested, never leveraged.
3. **Rebalance** at the next open only if the current weight is more than 5 points off target, which limits
   turnover. Per-ticker one-way costs of 3–10 bps.
4. **Safety:** no trading on stale or missing data; if GVZ is unavailable, sizing falls back to plain 21-day
   volatility with a visible warning.

The ML model and technical signals still run and are shown on the dashboard with their reasons, but they no longer
drive trades: tilting positions by the model's predictions (5-, 21- and 63-day horizons) added nothing on top of
risk-based sizing (EXP-015). The v0.2 BUY/SELL timing strategy (`strategy.mode: timing`) is kept for comparison as
`timing_v02` in every report.

**Headline results** (real data, six-asset portfolio, after costs; full tables in
[research/experiments/](research/experiments/README.md)):

| | Development 2013–2023: CAGR / Sharpe / max DD | Holdout 2024–2026: CAGR / max DD |
|---|---|---|
| v0.2 timing strategy | 0.8% / −0.02 / −21.4% | 20.8% / −17.2% |
| Always invested, volatility-sized | 2.0% / 0.12 / −27.8% | 24.6% / −13.7% |
| … with GVZ-adjusted sizing (traded) | 3.4% / 0.24 / −20.8% | 23.5% / −13.5% |
| Buy & hold | 6.0% / 0.30 / −43.0% | 44.2% / −38.0% |

The strategy gives up much of buy & hold's return in exchange for roughly half the drawdown; it has not beaten
buy & hold's risk-adjusted return over the development period. Paper trading is the next test.

## Evaluation methodology

* **Walk-forward:** expanding window, retrained every 63 days, first prediction after 3 years. No random splits.
* **Purging:** labels span 5 days, so the 5 training rows before each test block are dropped. Training never
  contains data after the test block, so no embargo is needed.
* **Holdout:** everything from `2024-01-01` is reported separately. Parameters were fixed before running it.
* **Benchmarks** over identical dates and costs: cash, buy & hold, volatility-sized hold (isolates timing from
  sizing), 200-day trend, 12-1 momentum, technical rule alone, ML alone, ML without macro features (ablation), and
  GDX for the individual miners.
* **Metrics:** CAGR, volatility, Sharpe and Sortino (excess of T-bills; Sortino uses downside deviation over all
  days), max drawdown, Calmar, win rate, average win/loss, holding period, turnover, cost drag, exposure,
  information ratio and beta vs buy & hold.
* **Model diagnostics:** AUC, accuracy vs base rate, precision, recall, Brier score and log loss vs a constant
  forecast, calibration, confusion matrix, AUC per fold, grouped permutation importance.
* **Uncertainty:** stationary block bootstrap (mean block 21 days) for Sharpe and for the Sharpe difference vs
  benchmarks. These are descriptive intervals, not multiple-testing-corrected significance tests.
* **Robustness:** cost sensitivity (0–50 bps), threshold grid (development period only, not used for selection),
  regimes (asset trend, VIX level, real-yield direction), calendar years.

## Tests

`pytest` runs 72 tests offline in about 30 seconds. Highlights:

* **Look-ahead:** features are identical with the future removed; walk-forward predictions don't change when later
  data is added; the purge gap holds; FRED dates shift to publication; partial bars are dropped; model skill only
  uses revealed labels.
* **Accounting:** fills at the next open, exact cost deduction, cash interest, volatility sizing, stop behaviour.
* **Metrics:** Sortino, Sharpe, drawdown, Calmar against hand calculations; zero-volatility and short-sample cases.
* **Regression tests** for every bug fixed in v0.2 (below).

## Research knowledge base (v0.3)

[`research/`](research/README.md) records everything investigated: source-code notes on Freqtrade, LEAN,
Backtrader, VectorBT and Zipline-reloaded at pinned commits; evidence reviews on gold, regimes, ML vs simple
rules, sizing and risk; a 30-row [strategy-transfer matrix](research/transfer-matrix.md); a
[decision log](research/decisions.md); and [pre-registered experiments](research/experiments/README.md) with
acceptance rules written before any results. Changes adopted from the review:

| Finding | Change |
|---|---|
| All four engines that model stops fill them intrabar, with a gap rule; Aurum checked the close (and disagreed with its own paper trader) | Intrabar stop fills (D-012) |
| Freqtrade's look-ahead and recursive analyses | Strategy-level truncation test and warm-up test |
| Best-of-many selection inflates Sharpe | Deflated Sharpe, PSR and PBO in `aurum/stats.py`, reported for every experiment |
| Ideas worth testing (trend, regime gates, model families, risk overlays, triple-barrier exits) | 26 variants in `aurum/experiments.py`, run by `run_experiments.py` |

## Changes in v0.2 (audit fixes)

| Problem found in v0.1 | Fix |
|---|---|
| Backtest traded ML probabilities alone; live decisions used a different composite | One rule in `strategy.py`, used everywhere; consistency test |
| `run_bot.py` refreshed prices but reused the morning's features and prediction | Features rebuilt from fresh bars every loop; stale data blocks trading |
| Trades filled at the same close that generated the signal | Fills at the next open |
| Sortino used the std of negative days | Downside deviation over all days vs the risk-free rate |
| Paper BUY top-ups recomputed the stop, which could lower it | No averaging in; stop fixed at entry; regression test |
| Paper trading charged no costs | Per-ticker costs, fees and realised P&L tracked |
| Uninvested cash earned nothing; Sharpe ignored the risk-free rate | T-bill rate for both |
| ML skill weight would have used full-sample AUC (look-ahead) | Point-in-time AUC from revealed labels only |
| FRED lag was one observation | Two business days by date |
| Live signals used today's partial bar, unlike the backtest | Completed bars only by default |

## Known limitations

* **Survivorship bias:** the universe was chosen in 2026; failed or acquired miners are missing.
* **Macro vintages:** FRED revisions aren't point-in-time (market-based series are rarely revised).
* **Execution:** flat cost per ticker; real spreads widen in stress. Paper fills use the last seen price.
* **Small sample of regimes:** about 13 years out-of-sample, one asset class. Results may not generalise.
* **Multiple comparisons:** many strategies and tickers are compared; some will look good by chance.

## Possible extensions

Broker paper trading via API (e.g. Alpaca), ALFRED point-in-time macro vintages, point-in-time fundamentals, separate
risk budgets for ETFs vs single miners, an LLM-based headline classifier evaluated on a labelled history.
