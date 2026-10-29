# Experiment results: 2026-10-29 (real)

Tickers: GLD, SLV, GDX, NEM, AEM, WPM. Development 2013-10-18 → 2023-12-31; holdout from 2024-01-01. Config `f04adb31f6e4`, orders filled at the next close. 30 variants tried (reference rows excluded).

**Probability of backtest overfitting across all variants (development):** 73% (12870 CSCV splits). Around 50% means picking the best-looking variant is no better than chance.

Portfolio level, net of costs. ΔSharpe is vs the baseline over identical dates; 'better' is the share of block-bootstrap resamples in which the variant beat the baseline; DSR is the deflated Sharpe ratio (probability the Sharpe is real after allowing for all variants tried).

| Exp | Variant | Dev Sharpe | Dev ΔSharpe | better | Dev ΔSharpe 2× cost | Dev max DD | Holdout ΔSharpe | DSR | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| BASE | baseline | -0.08 | +0.00 | 0% | +0.00 | -20.5% | +0.00 | 0.16 | baseline |
| EXP-001 | stop_on_close | -0.16 | -0.08 | 3% | -0.08 | -22.5% | +0.01 | 0.10 | REJECT |
| EXP-002 | tsmom_12m | -0.11 | -0.03 | 47% | +0.01 | -16.0% | -0.15 | 0.13 | REJECT |
| EXP-002 | tsmom_1_3_12 | -0.15 | -0.07 | 32% | -0.06 | -20.5% | -0.10 | 0.11 | REJECT |
| EXP-002 | donchian_50_20 | +0.01 | +0.09 | 69% | +0.14 | -13.2% | -0.33 | 0.24 | INCONCLUSIVE |
| EXP-002 | baseline_trend_filter | -0.10 | -0.02 | 39% | -0.01 | -18.8% | +0.03 | 0.14 | REJECT |
| EXP-003 | gate_real_yields | -0.04 | +0.04 | 60% | +0.07 | -17.2% | -0.30 | 0.19 | INCONCLUSIVE |
| EXP-003 | gate_vix | -0.16 | -0.08 | 2% | -0.08 | -22.3% | +0.00 | 0.10 | REJECT |
| EXP-003 | gate_dollar | -0.20 | -0.12 | 28% | -0.09 | -14.9% | -0.30 | 0.08 | REJECT |
| EXP-003 | gate_gold_trend | -0.24 | -0.16 | 12% | -0.15 | -20.2% | -0.06 | 0.06 | REJECT |
| EXP-004 | model_logit | -0.05 | +0.03 | 65% | +0.05 | -20.3% | -0.01 | 0.18 | INCONCLUSIVE |
| EXP-004 | model_forest | +0.06 | +0.14 | 94% | +0.16 | -19.9% | -0.05 | 0.28 | INCONCLUSIVE |
| EXP-004 | model_hgb_calibrated | +0.05 | +0.13 | 91% | +0.14 | -19.3% | -0.06 | 0.28 | INCONCLUSIVE |
| EXP-004 | model_ensemble | +0.03 | +0.11 | 94% | +0.13 | -19.5% | -0.09 | 0.26 | INCONCLUSIVE |
| EXP-005 | no_stop | -0.09 | -0.01 | 43% | +0.00 | -23.2% | -0.01 | 0.15 | REJECT |
| EXP-005 | chandelier_3atr | +0.04 | +0.11 | 92% | +0.10 | -16.8% | +0.29 | 0.26 | INCONCLUSIVE |
| EXP-005 | dd_breaker | -0.10 | -0.02 | 15% | -0.06 | -21.3% | -0.02 | 0.14 | REJECT |
| EXP-005 | stop_guard | -0.13 | -0.05 | 15% | -0.05 | -21.6% | +0.00 | 0.12 | REJECT |
| EXP-005 | no_vol_target | +0.07 | +0.15 | 94% | +0.16 | -37.4% | -0.05 | 0.30 | INCONCLUSIVE |
| EXP-005 | target_vol_10 | -0.07 | +0.01 | 63% | +0.01 | -13.6% | -0.03 | 0.16 | INCONCLUSIVE |
| EXP-005 | target_vol_20 | -0.06 | +0.02 | 88% | +0.02 | -25.5% | +0.00 | 0.17 | INCONCLUSIVE |
| EXP-006 | bollinger_reversion | +0.04 | +0.12 | 61% | +0.15 | -3.6% | +0.38 | 0.26 | INCONCLUSIVE |
| EXP-006 | miner_vs_gdx_reversion | +0.17 | +0.25 | 96% | +0.27 | -11.7% | +0.15 | 0.42 | INCONCLUSIVE |
| EXP-007 | tb_model_tb_exits | +0.01 | +0.09 | 70% | -0.01 | -15.3% | +0.16 | 0.24 | INCONCLUSIVE |
| EXP-007 | tb_model_base_exits | +0.03 | +0.11 | 82% | +0.11 | -16.6% | -0.12 | 0.26 | INCONCLUSIVE |
| EXP-007 | base_model_tb_exits | -0.33 | -0.25 | 4% | -0.34 | -15.7% | +0.27 | 0.04 | REJECT |
| EXP-013 | default_long | -0.01 | +0.07 | 81% | +0.02 | -26.1% | +0.04 | 0.22 | INCONCLUSIVE |
| EXP-013 | default_long_full | +0.12 | +0.20 | 95% | +0.15 | -51.3% | +0.09 | 0.35 | INCONCLUSIVE |
| EXP-013 | default_long_full_nostop | +0.08 | +0.16 | 85% | +0.12 | -54.7% | +0.07 | 0.31 | INCONCLUSIVE |
| EXP-013 | default_long_full_chandelier | +0.10 | +0.18 | 88% | +0.13 | -44.7% | -0.12 | 0.34 | INCONCLUSIVE |
| REF | buy_hold | +0.30 | +0.38 | 96% | +0.46 | -43.0% | +0.13 | 0.58 | reference |
| REF | vol_sized_hold | +0.22 | +0.30 | 94% | +0.38 | -25.7% | -0.01 | 0.48 | reference |

## Profit check: every variant vs simply holding (buy & hold), net of costs

| Exp | Variant | Dev CAGR | Dev Sharpe | Dev max DD | Dev ΔSharpe vs B&H | Dev ΔCAGR vs B&H | Holdout CAGR | Holdout max DD | Holdout ΔSharpe vs B&H |
|---|---|---|---|---|---|---|---|---|---|
| BASE | baseline | +0.3% | -0.08 | -20.5% | -0.38 | -5.7% | +21.6% | -17.8% | -0.13 |
| EXP-001 | stop_on_close | -0.5% | -0.16 | -22.5% | -0.47 | -6.4% | +21.8% | -18.1% | -0.12 |
| EXP-002 | tsmom_12m | +0.1% | -0.11 | -16.0% | -0.41 | -5.8% | +20.8% | -28.0% | -0.27 |
| EXP-002 | tsmom_1_3_12 | -0.4% | -0.15 | -20.5% | -0.45 | -6.4% | +17.6% | -15.5% | -0.23 |
| EXP-002 | donchian_50_20 | +1.1% | +0.01 | -13.2% | -0.29 | -4.8% | +11.9% | -12.1% | -0.46 |
| EXP-002 | baseline_trend_filter | +0.2% | -0.10 | -18.8% | -0.40 | -5.7% | +22.2% | -17.1% | -0.10 |
| EXP-003 | gate_real_yields | +0.7% | -0.04 | -17.2% | -0.34 | -5.2% | +14.1% | -17.6% | -0.43 |
| EXP-003 | gate_vix | -0.3% | -0.16 | -22.3% | -0.46 | -6.3% | +21.7% | -17.9% | -0.12 |
| EXP-003 | gate_dollar | -0.2% | -0.20 | -14.9% | -0.50 | -6.1% | +14.8% | -18.6% | -0.43 |
| EXP-003 | gate_gold_trend | -0.7% | -0.24 | -20.2% | -0.54 | -6.7% | +20.2% | -18.0% | -0.19 |
| EXP-004 | model_logit | +0.5% | -0.05 | -20.3% | -0.35 | -5.4% | +20.4% | -18.4% | -0.14 |
| EXP-004 | model_forest | +1.4% | +0.06 | -19.9% | -0.24 | -4.6% | +21.9% | -21.4% | -0.18 |
| EXP-004 | model_hgb_calibrated | +1.3% | +0.05 | -19.3% | -0.25 | -4.6% | +17.7% | -14.4% | -0.19 |
| EXP-004 | model_ensemble | +1.2% | +0.03 | -19.5% | -0.27 | -4.7% | +19.6% | -19.2% | -0.22 |
| EXP-005 | no_stop | +0.1% | -0.09 | -23.2% | -0.39 | -5.8% | +20.8% | -17.4% | -0.13 |
| EXP-005 | chandelier_3atr | +1.3% | +0.04 | -16.8% | -0.27 | -4.7% | +16.6% | -8.1% | +0.16 |
| EXP-005 | dd_breaker | +0.1% | -0.10 | -21.3% | -0.40 | -5.8% | +19.7% | -19.8% | -0.15 |
| EXP-005 | stop_guard | -0.1% | -0.13 | -21.6% | -0.43 | -6.0% | +21.7% | -17.9% | -0.12 |
| EXP-005 | no_vol_target | +1.0% | +0.07 | -37.4% | -0.23 | -4.9% | +31.4% | -34.1% | -0.18 |
| EXP-005 | target_vol_10 | +0.7% | -0.07 | -13.6% | -0.37 | -5.3% | +16.6% | -13.7% | -0.16 |
| EXP-005 | target_vol_20 | +0.1% | -0.06 | -25.5% | -0.36 | -5.9% | +25.0% | -21.2% | -0.12 |
| EXP-006 | bollinger_reversion | +1.3% | +0.04 | -3.6% | -0.26 | -4.6% | +8.2% | -1.8% | +0.25 |
| EXP-006 | miner_vs_gdx_reversion | +2.1% | +0.17 | -11.7% | -0.13 | -3.9% | +17.1% | -11.3% | +0.02 |
| EXP-007 | tb_model_tb_exits | +1.2% | +0.01 | -15.3% | -0.29 | -4.8% | +13.1% | -5.8% | +0.04 |
| EXP-007 | tb_model_base_exits | +1.2% | +0.03 | -16.6% | -0.27 | -4.7% | +18.5% | -20.8% | -0.25 |
| EXP-007 | base_model_tb_exits | -0.8% | -0.33 | -15.7% | -0.63 | -6.8% | +14.2% | -7.2% | +0.14 |
| EXP-013 | default_long | +0.8% | -0.01 | -26.1% | -0.31 | -5.2% | +22.4% | -18.5% | -0.08 |
| EXP-013 | default_long_full | +1.6% | +0.12 | -51.3% | -0.18 | -4.3% | +38.9% | -35.4% | -0.04 |
| EXP-013 | default_long_full_nostop | +0.7% | +0.08 | -54.7% | -0.22 | -5.2% | +38.0% | -35.4% | -0.06 |
| EXP-013 | default_long_full_chandelier | +1.5% | +0.10 | -44.7% | -0.20 | -4.4% | +23.8% | -28.7% | -0.24 |
| REF | buy_hold | +5.9% | +0.30 | -43.0% | +0.00 | +0.0% | +44.1% | -38.0% | +0.00 |
| REF | vol_sized_hold | +3.4% | +0.22 | -25.7% | -0.08 | -2.5% | +28.2% | -29.4% | -0.13 |

Verdicts are proposals. A change is only adopted when recorded in research/decisions.md.
