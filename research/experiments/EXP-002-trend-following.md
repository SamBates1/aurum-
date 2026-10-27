# EXP-002: Trend following and time-series momentum

| Field | |
|---|---|
| Status | Pre-registered 2026-10-27, awaiting a real-data run |
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

## Results
_Not yet run on real data._ After `python run_experiments.py`, copy the rows for this experiment from
`results/<date>-real/summary.md` here, with the verdict and any decision recorded in `../decisions.md`.
