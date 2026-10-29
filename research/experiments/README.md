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
| [EXP-008](EXP-008-cot-positioning.md) | CFTC positioning signal | CFTC COT data | Designed, not coded |
| EXP-009 (proposed) | Chandelier trailing stop, confirmatory | EXP-005 result | Not run: needs data not used in EXP-005 (new months via paper trading, or other assets) to be a fair test |

Results of each run go in `results/<date>-real/summary.md`; conclusions are copied into each EXP file's
"Results" section and into `../decisions.md`.
