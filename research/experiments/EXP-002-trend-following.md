# EXP-002: Trend following and time-series momentum

| Field | |
|---|---|
| Status | Run 2026-10-29 on real data: see Results |
| Origin | Moskowitz, Ooi & Pedersen (2012) [S1]; Hurst, Ooi & Pedersen (2017) [S2]; Donchian/turtle breakout rules. |
| Current Aurum equivalent | Aurum's technical score already includes a 50/200-day trend component, but no pure momentum strategy or trend filter has been tested as an alternative. |

## Hypothesis
Simple time-series momentum is a strong, interpretable baseline for gold and miners; the composite strategy should beat it after costs, or be replaced/augmented by it.

## Variants (fixed before running)
`tsmom_12m` (long when the 12-month return is positive); `tsmom_1_3_12` (average sign of 1, 3, 12-month returns); `donchian_50_20` (enter on a 50-day high, exit on a 20-day low); `baseline_trend_filter` (baseline, but new entries only when the 1/3/12-month trend is positive). All long-only, same sizing, stops and costs.

## Acceptance criteria
Standard rules in the registry README. See [README](README.md#acceptance-criteria-applied-automatically-by-run_experimentspyverdict).

## Main risks and limitations
Long-only, single-asset trend captures less diversification than the multi-asset studies; lookbacks fixed from the literature (no tuning).

## Results (real data, run 2026-10-29, `results/2026-10-29-real/`)
Portfolio of 6 sleeves, net of costs, vs the baseline over identical dates. Development 2013-10-18 → 2023-12-31;
holdout from 2024-01-01. 26 variants tried in total; PBO across them 77%.

| Variant | Dev Sharpe | Dev ΔSharpe | better | ΔSharpe 2× cost | Dev max DD | Holdout ΔSharpe | DSR | Verdict |
|---|---|---|---|---|---|---|---|---|
| tsmom_12m | -0.14 | -0.13 | 32% | -0.09 | -15.5% | -0.11 | 0.13 | INCONCLUSIVE |
| tsmom_1_3_12 | -0.15 | -0.14 | 21% | -0.13 | -22.3% | -0.01 | 0.13 | REJECT |
| donchian_50_20 | +0.07 | +0.08 | 65% | +0.13 | -13.3% | -0.35 | 0.33 | INCONCLUSIVE |
| baseline_trend_filter | -0.17 | -0.17 | 6% | -0.15 | -20.5% | +0.07 | 0.11 | REJECT |

No trend rule beat the baseline. 12-month and 1/3/12-month momentum and the trend filter were worse in development; the Donchian breakout was slightly better in development (+0.08) but much worse on the holdout (−0.35). **Conclusion: on these six assets, long-only, simple trend rules add nothing over the current technical score. Not adopted.**
