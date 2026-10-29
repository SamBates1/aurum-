# Experiment results: 2026-10-29 (real)

Tickers: GLD, SLV, GDX, NEM, AEM, WPM. Development 2013-10-18 → 2023-12-31; holdout from 2024-01-01. Config `2c9c656d1a4b`, orders filled at the next open. 16 variants tried (reference rows excluded).

**Probability of backtest overfitting across all variants (development):** 18% (12870 CSCV splits). Around 50% means picking the best-looking variant is no better than chance.

Portfolio level, net of costs. ΔSharpe is vs the baseline (`vol_hold`) over identical dates; 'better' is the share of block-bootstrap resamples in which the variant beat the baseline; DSR is the deflated Sharpe ratio (probability the Sharpe is real after allowing for all variants tried).

| Exp | Variant | Dev Sharpe | Dev ΔSharpe | better | Dev ΔSharpe 2× cost | Dev max DD | Holdout ΔSharpe | DSR | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| BASE | baseline | -0.02 | -0.14 | 24% | -0.21 | -21.4% | -0.33 | 0.34 | REJECT |
| EXP-014 | vol_hold | +0.12 | +0.00 | 0% | +0.00 | -27.8% | +0.00 | 0.51 | baseline |
| EXP-014 | vol_hold_band0 | +0.12 | -0.00 | 39% | -0.01 | -27.6% | -0.02 | 0.51 | REJECT |
| EXP-014 | vol_hold_band10 | +0.12 | -0.01 | 31% | -0.00 | -27.7% | +0.04 | 0.50 | REJECT |
| EXP-014 | vol_hold_monthly | +0.10 | -0.02 | 36% | -0.01 | -28.9% | +0.11 | 0.49 | REJECT |
| EXP-014 | vol_hold_tv20 | +0.14 | +0.01 | 81% | +0.01 | -33.3% | -0.04 | 0.53 | INCONCLUSIVE |
| EXP-015 | ml_tilt_h5 | +0.11 | -0.01 | 32% | -0.02 | -28.6% | -0.02 | 0.50 | REJECT |
| EXP-015 | ml_tilt_h21 | +0.08 | -0.04 | 17% | -0.06 | -27.5% | -0.14 | 0.46 | REJECT |
| EXP-015 | ml_tilt_h63 | +0.10 | -0.03 | 41% | -0.06 | -28.5% | -0.17 | 0.48 | REJECT |
| EXP-016 | xs_mom_126 | +0.03 | -0.10 | 0% | -0.13 | -28.9% | -0.06 | 0.39 | REJECT |
| EXP-016 | xs_mom_252_21 | +0.06 | -0.06 | 5% | -0.08 | -27.6% | -0.05 | 0.44 | REJECT |
| EXP-017 | vol_hold_ewma | +0.11 | -0.01 | 31% | -0.01 | -27.0% | +0.03 | 0.50 | REJECT |
| EXP-017 | vol_hold_har | +0.18 | +0.06 | 90% | +0.07 | -23.3% | -0.03 | 0.59 | INCONCLUSIVE |
| EXP-017 | vol_hold_gvz | +0.24 | +0.12 | 99% | +0.11 | -20.8% | +0.06 | 0.66 | KEEP (held on holdout) |
| EXP-018 | gvz_gate | +0.09 | -0.03 | 30% | -0.05 | -30.3% | +0.26 | 0.47 | REJECT |
| EXP-019 | miner_gdx_tilt | +0.21 | +0.09 | 100% | +0.08 | -28.1% | +0.04 | 0.62 | INCONCLUSIVE |
| REF | buy_hold | +0.30 | +0.18 | 98% | +0.19 | -43.0% | -0.18 | 0.73 | reference |
| REF | vol_sized_hold | +0.22 | +0.10 | 82% | +0.11 | -25.8% | -0.32 | 0.63 | reference |

## Profit check: every variant vs simply holding (buy & hold), net of costs

| Exp | Variant | Dev CAGR | Dev Sharpe | Dev max DD | Dev ΔSharpe vs B&H | Dev ΔCAGR vs B&H | Holdout CAGR | Holdout max DD | Holdout ΔSharpe vs B&H |
|---|---|---|---|---|---|---|---|---|---|
| BASE | baseline | +0.8% | -0.02 | -21.4% | -0.32 | -5.2% | +20.8% | -17.2% | -0.15 |
| EXP-014 | vol_hold | +2.0% | +0.12 | -27.8% | -0.18 | -4.0% | +24.6% | -13.7% | +0.18 |
| EXP-014 | vol_hold_band0 | +2.0% | +0.12 | -27.6% | -0.18 | -4.0% | +24.1% | -14.1% | +0.16 |
| EXP-014 | vol_hold_band10 | +1.9% | +0.12 | -27.7% | -0.19 | -4.1% | +25.5% | -13.6% | +0.22 |
| EXP-014 | vol_hold_monthly | +1.7% | +0.10 | -28.9% | -0.20 | -4.3% | +27.3% | -12.1% | +0.29 |
| EXP-014 | vol_hold_tv20 | +2.1% | +0.14 | -33.3% | -0.17 | -3.9% | +29.9% | -18.4% | +0.14 |
| EXP-015 | ml_tilt_h5 | +1.9% | +0.11 | -28.6% | -0.19 | -4.1% | +24.5% | -14.1% | +0.16 |
| EXP-015 | ml_tilt_h21 | +1.5% | +0.08 | -27.5% | -0.22 | -4.6% | +24.1% | -17.8% | +0.04 |
| EXP-015 | ml_tilt_h63 | +1.7% | +0.10 | -28.5% | -0.20 | -4.3% | +29.0% | -24.8% | +0.01 |
| EXP-016 | xs_mom_126 | +0.7% | +0.03 | -28.9% | -0.28 | -5.3% | +23.6% | -13.2% | +0.12 |
| EXP-016 | xs_mom_252_21 | +1.2% | +0.06 | -27.6% | -0.24 | -4.8% | +23.5% | -12.1% | +0.13 |
| EXP-017 | vol_hold_ewma | +1.9% | +0.11 | -27.0% | -0.19 | -4.1% | +24.0% | -13.0% | +0.21 |
| EXP-017 | vol_hold_har | +2.8% | +0.18 | -23.3% | -0.12 | -3.2% | +23.9% | -15.0% | +0.15 |
| EXP-017 | vol_hold_gvz | +3.4% | +0.24 | -20.8% | -0.06 | -2.6% | +23.5% | -13.5% | +0.24 |
| EXP-018 | gvz_gate | +1.6% | +0.09 | -30.3% | -0.21 | -4.4% | +24.4% | -11.3% | +0.44 |
| EXP-019 | miner_gdx_tilt | +3.3% | +0.21 | -28.1% | -0.09 | -2.7% | +27.2% | -15.4% | +0.22 |
| REF | buy_hold | +6.0% | +0.30 | -43.0% | +0.00 | +0.0% | +44.2% | -38.0% | +0.00 |
| REF | vol_sized_hold | +3.4% | +0.22 | -25.8% | -0.08 | -2.6% | +28.3% | -29.5% | -0.13 |

Verdicts are proposals. A change is only adopted when recorded in research/decisions.md.
