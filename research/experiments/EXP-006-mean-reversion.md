# EXP-006: Mean reversion

| Field | |
|---|---|
| Status | Pre-registered 2026-10-27, awaiting a real-data run |
| Origin | Mean-reversion and relative-value literature; Tufano (1998) on varying miner exposure [S5]. See topics/mean-reversion.md. |
| Current Aurum equivalent | Aurum has no mean-reversion component except an RSI-extreme term in the technical score. |

## Hypothesis
Buying short-term dips inside uptrends, or miners that lag GDX, adds return that is diversifying to trend signals.

## Variants (fixed before running)
`bollinger_reversion` (buy when close < 20-day mean - 2σ and price above 200-day average; exit at the mean); `miner_vs_gdx_reversion` (miners only: buy when the 60-day z-score of log(miner/GDX) < -2; exit at 0; ETF sleeves run the baseline).

## Acceptance criteria
Standard rules; also inspect the worst trades (relative-value gaps can be information, not noise). See [README](README.md#acceptance-criteria-applied-automatically-by-run_experimentspyverdict).

## Main risks and limitations
Long-only; cointegration pairs rejected for now (needs shorting).

## Results
_Not yet run on real data._ After `python run_experiments.py`, copy the rows for this experiment from
`results/<date>-real/summary.md` here, with the verdict and any decision recorded in `../decisions.md`.
