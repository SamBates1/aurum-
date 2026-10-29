# Experiment results: 2026-10-29 (real)

Tickers: GLD, SLV, GDX, NEM, AEM, WPM. Development 2013-10-18 → 2023-12-31; holdout from 2024-01-01. Config `f04adb31f6e4`, orders filled at the next close. 16 variants tried (reference rows excluded).

**Probability of backtest overfitting across all variants (development):** 9% (12870 CSCV splits). Around 50% means picking the best-looking variant is no better than chance.

Portfolio level, net of costs. ΔSharpe is vs the baseline (`vol_hold`) over identical dates; 'better' is the share of block-bootstrap resamples in which the variant beat the baseline; DSR is the deflated Sharpe ratio (probability the Sharpe is real after allowing for all variants tried).

| Exp | Variant | Dev Sharpe | Dev ΔSharpe | better | Dev ΔSharpe 2× cost | Dev max DD | Holdout ΔSharpe | DSR | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| BASE | baseline | -0.09 | -0.19 | 17% | -0.25 | -20.5% | -0.36 | 0.24 | REJECT |
| EXP-014 | vol_hold | +0.10 | +0.00 | 0% | +0.00 | -28.2% | +0.00 | 0.45 | baseline |
| EXP-014 | vol_hold_band0 | +0.09 | -0.01 | 18% | -0.02 | -27.8% | -0.01 | 0.44 | REJECT |
| EXP-014 | vol_hold_band10 | +0.11 | +0.01 | 84% | +0.02 | -27.6% | +0.02 | 0.47 | INCONCLUSIVE |
| EXP-014 | vol_hold_monthly | +0.10 | -0.00 | 51% | +0.01 | -28.7% | +0.07 | 0.45 | REJECT |
| EXP-014 | vol_hold_tv20 | +0.11 | +0.01 | 83% | +0.01 | -34.0% | -0.03 | 0.47 | INCONCLUSIVE |
| EXP-015 | ml_tilt_h5 | +0.11 | +0.01 | 62% | -0.01 | -27.7% | -0.01 | 0.46 | INCONCLUSIVE |
| EXP-015 | ml_tilt_h21 | +0.07 | -0.03 | 26% | -0.05 | -27.4% | -0.10 | 0.42 | REJECT |
| EXP-015 | ml_tilt_h63 | +0.10 | -0.01 | 49% | -0.04 | -27.7% | -0.16 | 0.45 | REJECT |
| EXP-016 | xs_mom_126 | +0.01 | -0.09 | 1% | -0.11 | -28.8% | -0.04 | 0.35 | REJECT |
| EXP-016 | xs_mom_252_21 | +0.03 | -0.07 | 2% | -0.09 | -28.4% | -0.04 | 0.36 | REJECT |
| EXP-017 | vol_hold_ewma | +0.11 | +0.01 | 60% | +0.01 | -26.6% | -0.03 | 0.46 | INCONCLUSIVE |
| EXP-017 | vol_hold_har | +0.18 | +0.08 | 95% | +0.09 | -22.9% | -0.13 | 0.55 | INCONCLUSIVE |
| EXP-017 | vol_hold_gvz | +0.24 | +0.14 | 100% | +0.13 | -20.5% | +0.00 | 0.63 | KEEP (held on holdout) |
| EXP-018 | gvz_gate | +0.03 | -0.08 | 12% | -0.09 | -29.4% | +0.26 | 0.36 | REJECT |
| EXP-019 | miner_gdx_tilt | +0.19 | +0.09 | 100% | +0.08 | -28.0% | +0.03 | 0.56 | INCONCLUSIVE |
| REF | buy_hold | +0.30 | +0.20 | 99% | +0.21 | -43.0% | -0.24 | 0.70 | reference |
| REF | vol_sized_hold | +0.22 | +0.12 | 86% | +0.13 | -25.7% | -0.37 | 0.60 | reference |

## Profit check: every variant vs simply holding (buy & hold), net of costs

| Exp | Variant | Dev CAGR | Dev Sharpe | Dev max DD | Dev ΔSharpe vs B&H | Dev ΔCAGR vs B&H | Holdout CAGR | Holdout max DD | Holdout ΔSharpe vs B&H |
|---|---|---|---|---|---|---|---|---|---|
| BASE | baseline | +0.2% | -0.09 | -20.5% | -0.39 | -5.7% | +21.7% | -17.9% | -0.12 |
| EXP-014 | vol_hold | +1.7% | +0.10 | -28.2% | -0.20 | -4.2% | +25.4% | -13.5% | +0.24 |
| EXP-014 | vol_hold_band0 | +1.6% | +0.09 | -27.8% | -0.21 | -4.3% | +25.2% | -13.6% | +0.23 |
| EXP-014 | vol_hold_band10 | +1.9% | +0.11 | -27.6% | -0.19 | -4.1% | +25.9% | -13.2% | +0.25 |
| EXP-014 | vol_hold_monthly | +1.7% | +0.10 | -28.7% | -0.20 | -4.2% | +27.5% | -11.7% | +0.30 |
| EXP-014 | vol_hold_tv20 | +1.7% | +0.11 | -34.0% | -0.19 | -4.2% | +31.0% | -18.0% | +0.20 |
| EXP-015 | ml_tilt_h5 | +1.8% | +0.11 | -27.7% | -0.19 | -4.2% | +25.5% | -13.7% | +0.22 |
| EXP-015 | ml_tilt_h21 | +1.3% | +0.07 | -27.4% | -0.23 | -4.6% | +25.7% | -16.7% | +0.13 |
| EXP-015 | ml_tilt_h63 | +1.7% | +0.10 | -27.7% | -0.21 | -4.3% | +30.8% | -23.6% | +0.08 |
| EXP-016 | xs_mom_126 | +0.5% | +0.01 | -28.8% | -0.29 | -5.4% | +24.6% | -12.6% | +0.19 |
| EXP-016 | xs_mom_252_21 | +0.7% | +0.03 | -28.4% | -0.27 | -5.2% | +24.5% | -12.1% | +0.19 |
| EXP-017 | vol_hold_ewma | +1.8% | +0.11 | -26.6% | -0.19 | -4.1% | +24.0% | -13.1% | +0.21 |
| EXP-017 | vol_hold_har | +2.7% | +0.18 | -22.9% | -0.12 | -3.2% | +23.2% | -16.0% | +0.11 |
| EXP-017 | vol_hold_gvz | +3.4% | +0.24 | -20.5% | -0.06 | -2.5% | +23.6% | -13.6% | +0.24 |
| EXP-018 | gvz_gate | +0.8% | +0.03 | -29.4% | -0.28 | -5.2% | +25.3% | -11.3% | +0.50 |
| EXP-019 | miner_gdx_tilt | +3.0% | +0.19 | -28.0% | -0.11 | -3.0% | +28.1% | -14.9% | +0.27 |
| REF | buy_hold | +5.9% | +0.30 | -43.0% | +0.00 | +0.0% | +44.1% | -38.0% | +0.00 |
| REF | vol_sized_hold | +3.4% | +0.22 | -25.7% | -0.08 | -2.5% | +28.2% | -29.4% | -0.13 |

Verdicts are proposals. A change is only adopted when recorded in research/decisions.md.
