# Experiment registry and protocol

Every idea follows: **Discover → Inspect source → Understand the maths → Evaluate evidence → Compare with
Aurum → Design experiment → Test out of sample → Keep or reject.** The first five steps live in
`research/frameworks/` and `research/topics/`; this folder holds the last three.

## Rules (written 2026-10-27, before any experiment was run on real data)
1. **Pre-register.** Hypothesis, variants and acceptance criteria are written in `EXP-xxx.md` before running.
   Parameters are fixed from the literature or round numbers, never tuned on results.
2. **Same everything.** Identical tickers, dates, costs, next-open fills, intrabar stops, cash interest and
   sleeve weights as the baseline (the traded strategy). Every variant runs through `strategy.simulate`.
3. **Development decides, holdout confirms.** Decisions use the development period
   (out-of-sample start → 2023-12-31). The holdout (2024-01-01 onwards) is looked at once, to confirm.
4. **Net, gross and 2× costs** are all reported. Improvements must survive doubled costs.
5. **Ablations** isolate components (e.g. EXP-007 separates the label from the exits).
6. **Failures are recorded**, with the reason, so they aren't retried by accident.
7. **Count every trial.** All variants in a run form the trial set for the Deflated Sharpe Ratio and PBO.

## Acceptance criteria (applied automatically by `run_experiments.py::verdict`)
At portfolio level, net of costs, versus the baseline over identical dates:

**Signal improvement path**: development ΔSharpe ≥ +0.10 **and** the variant beats the baseline in ≥ 80% of
stationary block-bootstrap resamples **and** ΔSharpe ≥ 0 at 2× costs.

**Risk-control path**: development max drawdown *per unit of volatility* at least 20% smaller **and**
ΔSharpe ≥ −0.05 (also at 2× costs). Volatility-adjusting stops "hold more cash" from passing as risk control.

**Then**: the variant's Deflated Sharpe Ratio (all variants as trials) ≥ 0.50, and on the holdout
ΔSharpe ≥ 0 (signal path) or the volatility-adjusted drawdown is no worse and ΔSharpe ≥ −0.10 (risk path).

| Outcome | Meaning |
|---|---|
| KEEP (held on holdout) | Candidate for adoption. Adopted only when recorded in `../decisions.md` |
| REJECT (failed on holdout) | Looked good in development, did not confirm |
| REJECT | Worse than the baseline in development |
| INCONCLUSIVE | Neither clearly better nor clearly worse; not adopted |

Also reported: **PBO** across all variants. If PBO ≥ 0.5, even "KEEP" results deserve scepticism.

## Research lab (rules written 2026-10-29, before any lab result existed)
The traded strategy does not need the ML model, so `run_lab.py` tests it, and every idea added on top of it, on more
history and on new assets (EXP-020 onwards):
- **Baseline:** `vol_hold_gvz`, exactly as traded (D-020, D-021). Every variant is a target weight per asset, run
  through `strategy.simulate_weights` with the same costs, fills, cash interest and 5-point band.
- **Periods:** `pre` = data start → 2013-10-17 (2006 for the core set; **never used by any earlier experiment**),
  `dev` = 2013-10-18 → 2023-12-31, `holdout` = 2024-01-01 onwards. The holdout has now been looked at several times,
  so it is no longer pristine; the pre-2013 period and the other assets are the fresh confirmation data.
- **Verdict:** the standard development rules (signal or risk path, 2× costs, DSR ≥ 0.5 over the lab's trial
  variants), then confirmation on **both** the holdout and the pre-2013 period. Adoption also needs the
  out-of-asset check (EXP-021, criterion 2) where it applies.
- **Tilts** are small by design: at most ±25% of the traded weight, never above full investment, parameters fixed
  in each EXP file before running.
- Descriptive rows (risk map, Alpaca checks) and references are not trials and get no verdict.
- Run: `lab:` lines in `RUN` (e.g. `lab: --set core`), or `python run_lab.py --set core|other [--fill close]`.

## Portfolio lab (rules written 2026-10-29, before any portfolio-lab result existed)
`run_plab.py` holds every asset and cash in **one account**, as the paper trader and a broker do (the sleeve engine
kept each asset in its own pot). Baseline `traded` = the traded rule with daily decisions (D-027). Same periods,
verdict rules and out-of-asset check as the research lab; the trial set is every non-descriptive variant in the run.
Experiments EXP-032 … EXP-036 (owner's brief of 2026-10-29). Run with `plab:` lines in `RUN`.

## Cross-asset lab (rules written 2026-10-29, before any cross-asset result existed)
`run_xlab.py` tests the master brief's strategy families on ten assets (SPY, QQQ, IWM, EFA, TLT, IEF, GLD, SLV, GDX,
DBC) in one account with the same periods and lab verdict rules; the baseline for signal families is the same
volatility-sized portfolio **with no signal**, so a pass means the signal adds something beyond sizing. Every run
writes a standard figure pack. Run with `xlab:` lines in `RUN`.

## Running

**Automated (no terminal needed):** `.github/workflows/experiments.yml` runs `run_research.py` and
`run_experiments.py` on GitHub's machines and commits the results and logs back. Start it by editing and
pushing `research/experiments/RUN` (first word `full` or `quick`), with **Actions → Experiments → Run workflow**,
or by enabling the weekly schedule in the workflow file.

**Manually (e.g. in Codespaces):**
```bash
python run_experiments.py            # real data (roughly 20–40 min); commit research/experiments/results/<date>-real/
python run_experiments.py --quick    # yearly retraining, fewer bootstrap draws
AURUM_OFFLINE=1 python run_experiments.py --quick   # synthetic: checks the code only (not committed)
```

## Registry
| ID | Idea | Origin | Status |
|---|---|---|---|
| [EXP-001](EXP-001-intrabar-stops.md) | Intrabar stop fills vs close-checked stops | LEAN / Backtrader / VectorBT / Freqtrade fill logic | Run: intrabar stops confirmed (D-012 kept) |
| [EXP-002](EXP-002-trend-following.md) | Time-series momentum, breakout, trend filter | Moskowitz–Ooi–Pedersen; Hurst–Ooi–Pedersen; turtle breakouts | Run: no improvement, not adopted |
| [EXP-003](EXP-003-regime-gates.md) | Macro/volatility regime gates | Erb–Harvey; regime literature | Run: no improvement, not adopted |
| [EXP-004](EXP-004-model-families.md) | Logistic, forest, calibrated, ensemble vs boosting | ML-vs-simple literature; FreqAI | Run: inconclusive, not adopted |
| [EXP-005](EXP-005-risk-overlays.md) | Stops, trailing, breakers, vol targets | Kaminski–Lo; Harvey et al.; Freqtrade Protections; LEAN risk models | Run: chandelier stop promising, fails DSR → EXP-009 |
| [EXP-006](EXP-006-mean-reversion.md) | Bollinger dips, miner vs GDX reversion | Mean-reversion literature; Tufano | Run: inconclusive, not adopted |
| [EXP-007](EXP-007-triple-barrier.md) | Triple-barrier labels and exits (trade plan) | López de Prado (AFML ch. 3) | Run: inconclusive, not adopted |
| [EXP-008](EXP-008-cot-positioning.md) | CFTC positioning signal | CFTC COT data | Superseded by EXP-025 |
| [EXP-010](EXP-010-close-fills.md) | Fill at the next close instead of the next open (robustness check) | Quantpedia [S20] | Run: results robust to fill assumption (D-018) |
| [EXP-013](EXP-013-invested-by-default.md) | Invested by default, protect when needed | First real results; profit goal | Run: goal not met; vol-sized holding proposed as new baseline (D-019) |
| [EXP-014](EXP-014-vol-hold.md) | Always invested, sized by volatility (candidate new baseline) | stage 2 follow-up | Run: **adopted** as traded strategy (D-020) |
| [EXP-015](EXP-015-ml-tilt-horizons.md) | Does prediction add value, and at which horizon? | stage 3 | Run: no horizon helps, not adopted |
| [EXP-016](EXP-016-cross-sectional-ranking.md) | Ranking the six assets against each other | stage 3 | Run: rejected |
| [EXP-017](EXP-017-volatility-forecasts.md) | Better volatility forecasts for sizing | stage 4 | Run: GVZ sizing **adopted** (D-021) |
| [EXP-018](EXP-018-gvz-gate.md) | Gold implied volatility as a risk gate | stage 4 | Run: rejected |
| [EXP-019](EXP-019-miner-gdx-tilt.md) | Miner vs GDX relative value, rechecked | stage 3 | Run: consistent +0.09, just below bar; re-test next |
| [EXP-020](EXP-020-long-history.md) | Longer history (2006–2013 stress test) | stage A | Run: protection confirmed 2006–2013; GVZ flagged (D-024) |
| [EXP-021](EXP-021-other-assets.md) | Eight precious-metal assets never tested | stage A | Run: protection and GVZ confirmed on new assets |
| [EXP-022](EXP-022-alpaca-realism.md) | Weekly orders, whole shares (Alpaca realism) | stage B | Run: weekly orders **adopted** (D-022) |
| [EXP-023](EXP-023-near-misses.md) | Miner-vs-GDX tilt and chandelier stop on the traded strategy | stage B | Run: miner tilt inconclusive; chandelier rejected |
| [EXP-024](EXP-024-fair-value.md) | Gold fair value (real yields, dollar) | stage 5 | Run: inconclusive, not adopted |
| [EXP-025](EXP-025-cot-positioning.md) | Speculative positioning (CFTC) | stage 6 | Run: not adopted |
| [EXP-026](EXP-026-news-risk-indices.md) | News-based risk indices (EPU, GPR) | stage 7 | Run: EPU small but below bar; GPR rejected |
| [EXP-027](EXP-027-combination.md) | Combine what passed | stage 8 | Not run: nothing to combine |
| [EXP-028](EXP-028-risk-map.md) | Risk map: 10–30% volatility targets | owner's choice | Run: risk map produced (owner chooses) |
| [EXP-032](EXP-032-entries-and-scaling.md) | Lump sum vs spreading in, adding to winners, averaging down, buying dips | brief | Run: nothing adopted |
| [EXP-033](EXP-033-stops-exits-breakers.md) | Stop-losses, trend exits, profit-taking, circuit breakers | brief | Run: all rejected |
| [EXP-034](EXP-034-sizing.md) | Sizing: fixed, inverse-vol, portfolio vol target, miners cap, cash reserve, fixed-fractional | brief | Run: nothing adopted |
| [EXP-035](EXP-035-risk-levels-and-robustness.md) | Risk levels, robustness grid, costs, one-account engine | brief | Run: flat region; one-account engine standard (D-028) |
| [EXP-036](EXP-036-regimes-and-diagnostics.md) | Regimes, consistency, tails, what normal looks like | brief | Run: diagnostics and normal ranges |
| [EXP-037](EXP-037-beat-sp500.md) | Can Aurum-style portfolios beat the S&P 500? | master brief | Run: nothing beat SPY; SPY+GLD 70/30 same return, less risk |
| [EXP-038](EXP-038-trend-momentum.md) | Trend following and momentum across ten assets | master brief | Run: none adopted |
| [EXP-039](EXP-039-mean-reversion-pairs.md) | Mean reversion and pairs | master brief | Run: rejected |
| [EXP-040](EXP-040-volatility-models.md) | Volatility models: forecast accuracy and sizing | master brief | Run: GVZ best forecast; portfolio inconclusive |
| [EXP-041](EXP-041-candlesticks.md) | Candlestick patterns | master brief | Run: no pattern works |
| [EXP-042](EXP-042-ml-models.md) | Machine learning vs simple baselines | master brief | Run: no ML skill |
| [EXP-043](EXP-043-macro-lead-lag.md) | Macro and cross-asset lead-lag | master brief | Run: nothing confirmed |
| [EXP-045](EXP-045-sp500-gold-mix.md) | S&P 500 + gold: robustness and downturn protection | owner | Run: mix robust; protections fail strict test (risk cap near miss) |
| [EXP-044](EXP-044-execution-delay.md) | Execution delay and cost sensitivity of the adopted strategy | master brief | Run: robust to delay and costs |
| EXP-009 | Chandelier trailing stop, confirmatory | EXP-005 result | Answered by EXP-023 (more history, new assets): rejected |

Results of each run go in `results/<date>-<time>-real[-…]/summary.md`; conclusions are copied into each EXP file's
"Results" section and into `../decisions.md`.
