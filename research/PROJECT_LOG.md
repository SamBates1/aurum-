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

## 2026-10-29 — Stages 3–4 and the strategy switch
- Built a target-weight engine (positions resized as volatility changes) after finding the stage-2
  `vol_sized_hold` reference never resized (D-019 correction).
- **Adopted:** always invested, sized by volatility (EXP-014, D-020), with sizing scaled by gold implied
  volatility (EXP-017, D-021). Both passed with open and close fills.
- **Rejected / not adopted:** ML tilts at 5/21/63-day horizons (no value), cross-sectional ranking (harmful),
  GVZ on/off gate, EWMA/HAR (no robust gain). Miner-vs-GDX tilt: consistent +0.09, just below the bar.
- **Lesson:** in this market, value came from *how much* to hold and from forward-looking risk (options), not
  from predicting direction.

## 2026-10-29 — Research lab: 20 years, new assets, Alpaca realism, stages 5–7
- Built `aurum/lab.py` and `run_lab.py`: the always-invested strategy needs no ML model, so it was tested from 2006
  (adding the 2008 crash and the 2011–15 gold bear market) and on eight precious-metal assets never used before.
  All rules written in EXP-020…028 before the runs.
- **2006–2026 headline (core set, net of costs):** strategy 5.7% a year, Sharpe 0.38, worst fall −39.7%; buy & hold
  9.5%, 0.39, −65.2%. Same return per unit of risk as holding, with a much smaller worst fall; less money in total.
  In 2011–15 it lost 39% where holding lost 63%. The new assets show the same pattern (EXP-020, EXP-021).
- **Adopted:** weekly orders after Friday's close (D-022); whole-share auction orders allowed for Alpaca (D-023).
- **Reviewed:** GVZ sizing did worse in 2008–2013 but better overall and on new assets: kept, weakness recorded (D-024).
- **Nothing else passed:** fair value, CFTC positioning, news-based risk indices, chandelier stop; miner tilt and
  EPU tilt small and consistent but below the bar (D-025). Stage 8 not run (nothing to combine).
- **Risk map:** Sharpe is the same at every risk level; the choice is how much of gold's ride to take (D-026).
- GDELT news history needs paid BigQuery access; replaced by free news-count indices (EPU, GPR).
- Intraday review written ([topics/intraday.md](topics/intraday.md)); the US pattern-day-trader rule was removed
  in 2026. Intraday tests (EXP-029…031) need Alpaca minute data.
- **Lesson:** after about 50 pre-registered variants, the edge in this market comes from risk sizing, not prediction. The
  bot is a smoother way to own gold and miners, not a way to beat owning them.

## 2026-10-29 — Owner's strategy brief: audit, portfolio lab, safety
- **Audit** ([audit-2026-10-29.md](audit-2026-10-29.md)): the backtest ran each asset in its own pot while the paper
  trader sized against the whole account; fixed with a one-account simulator (D-028, difference ≤ 0.04 Sharpe).
  Other findings: trading depended on the unused ML model succeeding each morning; no duplicate-order guard; no
  structured decision records.
- **Daily decisions** restored at the owner's request (D-027).
- **Portfolio lab** (EXP-032…036, 20 pre-registered variants, 2006–2026, two asset sets, two fill conventions):
  nothing adopted (D-029). Lump sum vs spreading in: coin-flip. Averaging down: deeper worst fall. Stops, trend exits,
  breakers: smaller falls, less return. Fixed weights beat volatility sizing on Sharpe before 2024, failed after.
  Settings sit in a flat region; strategy survives costs up to ~25 bps.
- **Diagnostics:** the strategy earns in gold bull markets (+22% a year) and loses about half as much as holding in
  bear markets (−18% vs −38%); longest time below a previous peak about 9 years (2011–2020), like holding.
- **Safety** (`aurum/safety.py`): off switch, stale-data and bad-price guards, one order per asset per day, order and
  position limits, cash check, and a structured record for every planned or blocked order; dashboard monitoring.
- **Documents:** paper-trading plan with pass/fail rules written in advance, deployment checklist, continuous
  improvement plan, and a strategy report ([strategy-report-2026-10-29.md](strategy-report-2026-10-29.md)).

## 2026-10-29 — Master brief: Quant Desk recovery, integrity audit, cross-asset lab
- **Stage 1:** the Quant Desk branch (PR #1) failed CI on formatting; fixed. The documented daily-report command could
  not run at all (`ModuleNotFoundError: aurum`), which would have broken the scheduled job; fixed and tested. Desk now
  shows provider/model, states that all "specialists" are one model with different prompts, labels fact / estimate /
  hypothesis, reads experiment records by ID only, and logs answers. No real model was available to test against.
- **Stage 2:** headline result reproduced from scratch (5.5% CAGR, Sharpe 0.36, worst fall −39.1%). Data audit of 35
  series ([audits/](audits/)): core data clean; CPER and the FRED credit spread unusable (D-031). Fixed: stale-cache
  history, checkpoints reusable after code changes, missing code/data fingerprints; ledger reconciliation verified.
- **Stages 3–5:** EXP-037…044 on ten assets, all pre-registered, with a standard figure pack per experiment. Nothing
  beat the S&P 500; leverage did not help; 70/30 SPY/GLD matched the S&P's return with less risk. No signal family
  (trend, mean reversion, pairs, candlesticks, ML, macro) passed. GVZ gave the best volatility forecasts (D-032). The
  strategy is robust to execution delay and doubled costs (D-030).
- **Lesson:** across about 100 pre-registered portfolio variants and over 500 statistical tests, the only reliable effects are risk effects
  (volatility sizing, diversification across assets), not return prediction.

- **Strategy platform (master build prompt, 2026-10-29 night):** strategy definitions shared by backtest, designer and
  paper trader; Strategy Designer with linked decision charts; Fair Test applying the lab rules; experiment registry
  with luck and holdout counters; independent risk engine; eligibility gates with owner approvals; paper trading of
  the owner's Option 3 pair (D-034, D-035). The designer engine reproduces EXP-045 exactly.

## Open questions
- Do the miner-vs-GDX and EPU tilts keep their small edge in paper trading (watched, not traded)?
- Which risk level does the owner choose (EXP-028)?
- Do intraday ideas (EXP-029…031) survive costs on minute data?
- Will paper trading confirm the GVZ-sized strategy's risk and return?
- Does the gold/real-yield regime break show up as poor holdout performance?
- Should ML be kept at all if trend rules match it (EXP-002 vs baseline)?
