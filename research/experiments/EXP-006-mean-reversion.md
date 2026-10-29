# EXP-006: Mean reversion

| Field | |
|---|---|
| Status | Run 2026-10-29 on real data: see Results |
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

## Results (real data, run 2026-10-29, `results/2026-10-29-real/`)
Portfolio of 6 sleeves, net of costs, vs the baseline over identical dates. Development 2013-10-18 → 2023-12-31;
holdout from 2024-01-01. 26 variants tried in total; PBO across them 77%.

| Variant | Dev Sharpe | Dev ΔSharpe | better | ΔSharpe 2× cost | Dev max DD | Holdout ΔSharpe | DSR | Verdict |
|---|---|---|---|---|---|---|---|---|
| bollinger_reversion | -0.05 | -0.04 | 48% | -0.01 | -3.9% | +0.43 | 0.21 | INCONCLUSIVE |
| miner_vs_gdx_reversion | +0.06 | +0.07 | 68% | +0.09 | -13.3% | +0.17 | 0.33 | INCONCLUSIVE |

Neither mean-reversion rule passed. Bollinger dip-buying cut drawdown to −3.9% but by trading rarely, with lower development Sharpe; miner-vs-GDX reversion was slightly better in development (+0.07) and on the holdout (+0.17) but below the bars (DSR 0.33). **Conclusion: not adopted; miner-vs-GDX is worth watching.**
