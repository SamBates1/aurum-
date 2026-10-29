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
| [EXP-020](EXP-020-long-history.md) | Longer history (2006–2013 stress test) | stage A | Pre-registered |
| [EXP-021](EXP-021-other-assets.md) | Eight precious-metal assets never tested | stage A | Pre-registered |
| [EXP-022](EXP-022-alpaca-realism.md) | Weekly orders, whole shares (Alpaca realism) | stage B | Pre-registered |
| [EXP-023](EXP-023-near-misses.md) | Miner-vs-GDX tilt and chandelier stop on the traded strategy | stage B | Pre-registered |
| [EXP-024](EXP-024-fair-value.md) | Gold fair value (real yields, dollar) | stage 5 | Pre-registered |
| [EXP-025](EXP-025-cot-positioning.md) | Speculative positioning (CFTC) | stage 6 | Pre-registered |
| [EXP-026](EXP-026-news-risk-indices.md) | News-based risk indices (EPU, GPR) | stage 7 | Pre-registered |
| [EXP-027](EXP-027-combination.md) | Combine what passed | stage 8 | Pre-registered |
| [EXP-028](EXP-028-risk-map.md) | Risk map: 10–30% volatility targets | owner's choice | Pre-registered |
| EXP-009 (proposed) | Chandelier trailing stop, confirmatory | EXP-005 result | Not run: needs data not used in EXP-005 (new months via paper trading, or other assets) to be a fair test |

Results of each run go in `results/<date>-<time>-real[-…]/summary.md`; conclusions are copied into each EXP file's
"Results" section and into `../decisions.md`.
