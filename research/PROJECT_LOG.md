# Project log

Everything gathered and decided so far, in order, so future work starts from what is already known.
Decisions referenced as D-xxx are in [decisions.md](decisions.md); sources as Sx in [sources.md](sources.md).

## 2026-10-27 — Project start (v0.1)
- **Goal:** a bot that analyses markets and gives decisions, built as a CV project for finance internships.
- **Choices:** signals + paper trading; ML, fundamentals, technical and news sentiment; Python with a web
  dashboard (D-002). Sector: gold & macro with miners (D-001).
- **Built:** `aurum` package (data, features, walk-forward model, backtest, signals, paper portfolio),
  Streamlit dashboard, headless bot, tests; zipped and delivered.
- **Set-up journey:** GitHub account `SamBates1`, repository `aurum-`; a drag-and-drop upload flattened the
  folders, fixed with `git mv` in Codespaces; dashboard run with `python -m streamlit run app.py` (D-003).

## 2026-10-27 — First real-data run
- Dashboard showed GLD: **BUY**, ML P(up) 79%, technical score −0.75 (below 50/200-day averages),
  out-of-sample **AUC 0.50**, ML weight 67%. Lesson: an unskilled model was driving the decision → D-004.
- News sentiment was missing for GLD (no recent headlines) → aliases added (gold futures for GLD, etc.).

## 2026-10-27 — Paper-trading venues researched
- **Alpaca**: free paper accounts, open globally, email sign-up, built for API trading; covers all six
  US-listed tickers. Recommended.
- **Trading 212**: API with a demo environment; beta; Invest and Stocks ISA accounts only. UK alternative.
- **Interactive Brokers**: powerful; paper account with virtual capital; heavier to set up.
  (Sources in sources.md, "Tools and services".) Not yet connected to Aurum.

## 2026-10-27 — Full audit and v0.2
Confirmed bugs: backtest/live strategy mismatch; bot used stale features; same-close fills; wrong Sortino;
paper top-ups could lower stops; no paper costs; no cash interest; partial-bar signals; ML skill weighting would
have been look-ahead in a backtest. All fixed (D-005 … D-011). Added benchmarks, development/holdout split,
block bootstrap, cost sensitivity, regimes, model diagnostics, data validation and caching, 52 tests, CI.
CI initially failed (`pytest` without the project on the import path); fixed with `pythonpath` in pyproject.

## 2026-10-27 — Owner's idea, deferred
A trade plan per signal: when to buy/sell, at what price, stop-loss, how long to stay in (D-015).

## 2026-10-27 — Research module (v0.3): reverse-engineering trading systems
- **Source code read at pinned commits:** Freqtrade, LEAN, Backtrader, VectorBT, Zipline-reloaded
  ([frameworks/](frameworks/README.md)). Key findings: all stop-modelling engines fill stops intrabar with a gap
  rule (→ D-012); Freqtrade's truncation and warm-up analyses (→ two new tests); dangerous defaults in VectorBT
  (same-bar fills, 365-day year), Backtrader (annual Sharpe) and Freqtrade (non-standard Sortino);
  no engine adopted (D-013).
- **Evidence reviewed** ([topics/](topics/)): trend/momentum strong for diversified futures, weaker
  single-asset; the gold/real-yield link broke after 2021 (central-bank buying); miners ≈ 2× gold beta but
  unstable; vol targeting improves equity Sharpe, not commodities; stop-losses help only with momentum;
  equity-premium predictors fail out of sample; most published factors are likely false without a t ≈ 3 hurdle.
- **Built:** `aurum/experiments.py` (26 pre-registered variants across EXP-001…007), `run_experiments.py`
  (net/gross/2× cost, bootstrap, DSR, PBO, automatic verdicts), model zoo, triple-barrier labels, risk-rule
  options (trailing stop, take-profit, time exit, breakers), Deflated Sharpe / PSR / PBO, 72 tests.
- **Transfer matrix:** 30 ideas classified ([transfer-matrix.md](transfer-matrix.md)).
- **Next:** run `python run_experiments.py` on real data in Codespaces, commit the results, then record
  verdicts in each EXP file and decisions here.

## Open questions
- Does any variant beat the baseline after DSR on real data?
- Does the gold/real-yield regime break show up as poor holdout performance?
- Should ML be kept at all if trend rules match it (EXP-002 vs baseline)?
