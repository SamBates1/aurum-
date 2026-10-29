# Experiment results: 2026-10-29 (real)

Tickers: GLD, SLV, GDX, NEM, AEM, WPM. Development 2013-10-18 → 2023-12-31; holdout from 2024-01-01. Config `0941fb0217c0`, orders filled at the next open. 1 variants tried (reference rows excluded).

**Probability of backtest overfitting across all variants (development):** nan% (0 CSCV splits). Around 50% means picking the best-looking variant is no better than chance.

Portfolio level, net of costs. ΔSharpe is vs the baseline (`baseline`) over identical dates; 'better' is the share of block-bootstrap resamples in which the variant beat the baseline; DSR is the deflated Sharpe ratio (probability the Sharpe is real after allowing for all variants tried).

| Exp | Variant | Dev Sharpe | Dev ΔSharpe | better | Dev ΔSharpe 2× cost | Dev max DD | Holdout ΔSharpe | DSR | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| BASE | baseline | -0.02 | +0.00 | 0% | +0.00 | -22.0% | +0.00 | 0.48 | baseline |
| REF | buy_hold | +0.30 | +0.32 | 94% | +0.40 | -43.0% | +0.14 | 0.83 | reference |
| REF | vol_sized_hold | +0.22 | +0.24 | 90% | +0.32 | -25.8% | +0.01 | 0.76 | reference |

## Profit check: every variant vs simply holding (buy & hold), net of costs

| Exp | Variant | Dev CAGR | Dev Sharpe | Dev max DD | Dev ΔSharpe vs B&H | Dev ΔCAGR vs B&H | Holdout CAGR | Holdout max DD | Holdout ΔSharpe vs B&H |
|---|---|---|---|---|---|---|---|---|---|
| BASE | baseline | +0.8% | -0.02 | -22.0% | -0.32 | -5.3% | +20.9% | -17.2% | -0.14 |
| REF | buy_hold | +6.0% | +0.30 | -43.0% | +0.00 | +0.0% | +44.2% | -38.0% | +0.00 |
| REF | vol_sized_hold | +3.4% | +0.22 | -25.8% | -0.08 | -2.6% | +28.3% | -29.5% | -0.13 |

Verdicts are proposals. A change is only adopted when recorded in research/decisions.md.
