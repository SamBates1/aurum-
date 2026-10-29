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

## 2026-10-27 — First real-data research report (`reports/latest/`, commit 646da67)
Portfolio of six equal sleeves, after costs, out of sample from 2013-10-18:

| Period | Strategy Sharpe | Buy & hold Sharpe | Strategy max DD | Buy & hold max DD |
|---|---|---|---|---|
| Development 2013–2023 | 0.00 | 0.30 | −21.5% | −43.0% |
| Holdout 2024–2026 | 0.94 | 1.07 | −17.2% | −38.0% |

- The strategy roughly halves drawdowns but earned about nothing after costs in development; buy & hold had
  the better risk-adjusted return in both periods (bootstrap: strategy beat buy & hold in only 6% of
  development resamples).
- ML probabilities are not informative yet: holdout AUC 0.45–0.56 by ticker, and Brier score / log loss are
  worse than a constant forecast for every ticker. The point-in-time skill weighting mostly switches ML off.
- `ml_only` had a holdout Sharpe of 1.61 but −0.24 in development: treated as luck, not evidence.
- `run_experiments.py` produced no results folder: the run did not complete or was not saved. To redo.

## 2026-10-29 — Automated runs and first experiment results
- The Codespaces experiment run was most likely cut short by the 30-minute idle timeout; experiment runs were
  made resumable, then moved to GitHub Actions (`.github/workflows/experiments.yml`, D-016). The first automated
  run's experiment results were silently dropped by a `results/` rule in `.gitignore`; fixed and re-run.
- **Results** (`experiments/results/2026-10-29-real/summary.md`), portfolio level, net of costs:
  - Baseline: development Sharpe −0.01, holdout +0.92 (buy & hold: +0.30 / +1.08), with roughly half the drawdown.
  - No variant passed all rules. PBO 77%: picking the in-sample winner is worse than chance.
  - Intrabar stops beat closing-price stops (confirms D-012).
  - Trend rules, regime gates, mean reversion: no reliable improvement.
  - Model families: small, consistent development gains (+0.06 to +0.09) that did not hold on the holdout.
  - Chandelier trailing stop: best result (+0.12 development, +0.26 holdout, 94% of resamples) but deflated
    Sharpe 0.39 → candidate, not adopted (D-017).
- **Interpretation:** the system's value is risk control (smaller drawdowns), not return prediction; this
  matches the literature on weak out-of-sample predictability (topics/ml-vs-simple.md).

## 2026-10-29 — New ideas scan
Short literature scan ([topics/new-ideas-2026-10-29.md](topics/new-ideas-2026-10-29.md)). Most important: daily
"open" prices may not be tradable (Quantpedia), so every Aurum result assumes fills that may be optimistic;
EXP-010 (next-close fills) proposed as a validity check. Also proposed: HAR volatility forecasts for sizing
(EXP-011), a smoother continuous trend signal to cut costs (EXP-012), gold implied volatility (GVZ), and price
ranges for the trade-plan idea. Seasonality: low priority. GDX overnight drift: rejected.

## 2026-10-29 — Stages 1–2: fill check and invested-by-default
- **EXP-010** (whole registry with next-close fills): conclusions unchanged; open fills only mildly flattering
  (D-018). Miner-vs-GDX reversion looked much stronger with close fills: flagged for follow-up.
- **EXP-013** (invested by default): more return than the baseline, but fully invested variants had buy-and-hold
  sized drawdowns; no variant beat buy & hold risk-adjusted. Buy & hold had the best Sharpe of all (0.30).
- **Key lesson:** Aurum's protection comes from position sizing, not timing. Proposed new baseline:
  always invested with volatility-targeted size (D-019), pending the owner's decision.
- Engine: optional close fills and re-entry cooldown; result folders now time-stamped so runs never overwrite.

## Open questions
- Does the chandelier stop hold up on new data (EXP-009)?
- Is the miner-vs-GDX effect real, or an artefact of fill timing?
- Can any prediction signal beat volatility-sized holding (D-019)?
- Does the gold/real-yield regime break show up as poor holdout performance?
- Should ML be kept at all if trend rules match it (EXP-002 vs baseline)?
