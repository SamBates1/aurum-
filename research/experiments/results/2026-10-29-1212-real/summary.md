# Experiment results: 2026-10-29 (real)

Tickers: GLD, SLV, GDX, NEM, AEM, WPM. Development 2013-10-18 → 2023-12-31; holdout from 2024-01-01. Config `2c9c656d1a4b`, orders filled at the next open. 30 variants tried (reference rows excluded).

**Probability of backtest overfitting across all variants (development):** 63% (12870 CSCV splits). Around 50% means picking the best-looking variant is no better than chance.

Portfolio level, net of costs. ΔSharpe is vs the baseline over identical dates; 'better' is the share of block-bootstrap resamples in which the variant beat the baseline; DSR is the deflated Sharpe ratio (probability the Sharpe is real after allowing for all variants tried).

| Exp | Variant | Dev Sharpe | Dev ΔSharpe | better | Dev ΔSharpe 2× cost | Dev max DD | Holdout ΔSharpe | DSR | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| BASE | baseline | -0.02 | +0.00 | 0% | +0.00 | -21.4% | +0.00 | 0.19 | baseline |
| EXP-001 | stop_on_close | -0.12 | -0.10 | 1% | -0.10 | -22.9% | +0.02 | 0.11 | REJECT |
| EXP-002 | tsmom_12m | -0.14 | -0.12 | 33% | -0.08 | -15.5% | -0.13 | 0.10 | INCONCLUSIVE |
| EXP-002 | tsmom_1_3_12 | -0.15 | -0.13 | 23% | -0.12 | -22.3% | -0.03 | 0.10 | REJECT |
| EXP-002 | donchian_50_20 | +0.07 | +0.08 | 65% | +0.14 | -13.3% | -0.37 | 0.27 | INCONCLUSIVE |
| EXP-002 | baseline_trend_filter | -0.18 | -0.16 | 6% | -0.15 | -20.4% | +0.06 | 0.08 | REJECT |
| EXP-003 | gate_real_yields | +0.02 | +0.04 | 62% | +0.06 | -17.5% | -0.26 | 0.22 | INCONCLUSIVE |
| EXP-003 | gate_vix | -0.14 | -0.12 | 1% | -0.12 | -23.9% | +0.00 | 0.10 | REJECT |
| EXP-003 | gate_dollar | -0.08 | -0.06 | 38% | -0.03 | -13.8% | -0.25 | 0.14 | REJECT |
| EXP-003 | gate_gold_trend | -0.21 | -0.19 | 9% | -0.17 | -20.9% | -0.05 | 0.07 | REJECT |
| EXP-004 | model_logit | -0.01 | +0.01 | 56% | +0.03 | -22.1% | +0.03 | 0.20 | INCONCLUSIVE |
| EXP-004 | model_forest | +0.07 | +0.09 | 79% | +0.11 | -21.1% | -0.04 | 0.27 | INCONCLUSIVE |
| EXP-004 | model_hgb_calibrated | +0.08 | +0.09 | 80% | +0.11 | -19.1% | -0.09 | 0.28 | INCONCLUSIVE |
| EXP-004 | model_ensemble | +0.08 | +0.09 | 91% | +0.11 | -20.1% | -0.02 | 0.28 | INCONCLUSIVE |
| EXP-005 | no_stop | -0.01 | +0.01 | 48% | +0.01 | -23.4% | -0.01 | 0.19 | INCONCLUSIVE |
| EXP-005 | chandelier_3atr | +0.11 | +0.13 | 94% | +0.12 | -17.3% | +0.27 | 0.32 | INCONCLUSIVE |
| EXP-005 | dd_breaker | -0.01 | +0.01 | 67% | -0.02 | -20.8% | -0.06 | 0.20 | INCONCLUSIVE |
| EXP-005 | stop_guard | -0.02 | +0.00 | 54% | +0.00 | -21.3% | -0.04 | 0.19 | INCONCLUSIVE |
| EXP-005 | no_vol_target | +0.19 | +0.21 | 96% | +0.21 | -40.8% | -0.08 | 0.42 | INCONCLUSIVE |
| EXP-005 | target_vol_10 | -0.02 | -0.00 | 44% | -0.00 | -14.7% | -0.03 | 0.19 | REJECT |
| EXP-005 | target_vol_20 | +0.00 | +0.02 | 94% | +0.02 | -27.3% | +0.01 | 0.21 | INCONCLUSIVE |
| EXP-006 | bollinger_reversion | -0.05 | -0.03 | 48% | -0.00 | -3.9% | +0.41 | 0.16 | INCONCLUSIVE |
| EXP-006 | miner_vs_gdx_reversion | +0.07 | +0.08 | 70% | +0.10 | -13.3% | +0.14 | 0.27 | INCONCLUSIVE |
| EXP-007 | tb_model_tb_exits | +0.08 | +0.10 | 72% | -0.01 | -10.2% | +0.33 | 0.28 | INCONCLUSIVE |
| EXP-007 | tb_model_base_exits | +0.14 | +0.16 | 90% | +0.16 | -13.3% | -0.14 | 0.36 | INCONCLUSIVE |
| EXP-007 | base_model_tb_exits | -0.17 | -0.16 | 11% | -0.26 | -16.8% | +0.11 | 0.08 | REJECT |
| EXP-013 | default_long | +0.12 | +0.13 | 92% | +0.08 | -22.3% | -0.02 | 0.32 | INCONCLUSIVE |
| EXP-013 | default_long_full | +0.26 | +0.28 | 98% | +0.22 | -46.7% | -0.02 | 0.50 | INCONCLUSIVE |
| EXP-013 | default_long_full_nostop | +0.15 | +0.17 | 89% | +0.13 | -47.5% | +0.02 | 0.37 | INCONCLUSIVE |
| EXP-013 | default_long_full_chandelier | +0.24 | +0.26 | 95% | +0.21 | -42.9% | -0.27 | 0.48 | INCONCLUSIVE |
| REF | buy_hold | +0.30 | +0.32 | 94% | +0.40 | -43.0% | +0.14 | 0.56 | reference |
| REF | vol_sized_hold | +0.22 | +0.24 | 90% | +0.32 | -25.8% | +0.01 | 0.45 | reference |

## Profit check: every variant vs simply holding (buy & hold), net of costs

| Exp | Variant | Dev CAGR | Dev Sharpe | Dev max DD | Dev ΔSharpe vs B&H | Dev ΔCAGR vs B&H | Holdout CAGR | Holdout max DD | Holdout ΔSharpe vs B&H |
|---|---|---|---|---|---|---|---|---|---|
| BASE | baseline | +0.8% | -0.02 | -21.4% | -0.32 | -5.2% | +20.9% | -17.2% | -0.14 |
| EXP-001 | stop_on_close | -0.1% | -0.12 | -22.9% | -0.42 | -6.1% | +21.4% | -17.3% | -0.13 |
| EXP-002 | tsmom_12m | -0.1% | -0.14 | -15.5% | -0.44 | -6.1% | +20.9% | -28.2% | -0.27 |
| EXP-002 | tsmom_1_3_12 | -0.4% | -0.15 | -22.3% | -0.45 | -6.5% | +20.3% | -19.5% | -0.17 |
| EXP-002 | donchian_50_20 | +1.5% | +0.07 | -13.3% | -0.24 | -4.5% | +11.1% | -11.7% | -0.52 |
| EXP-002 | baseline_trend_filter | -0.4% | -0.18 | -20.4% | -0.48 | -6.4% | +22.3% | -16.4% | -0.08 |
| EXP-003 | gate_real_yields | +1.2% | +0.02 | -17.5% | -0.28 | -4.8% | +14.4% | -17.2% | -0.41 |
| EXP-003 | gate_vix | -0.2% | -0.14 | -23.9% | -0.44 | -6.2% | +21.1% | -17.4% | -0.14 |
| EXP-003 | gate_dollar | +0.5% | -0.08 | -13.8% | -0.38 | -5.5% | +15.5% | -17.9% | -0.39 |
| EXP-003 | gate_gold_trend | -0.5% | -0.21 | -20.9% | -0.51 | -6.5% | +19.8% | -17.1% | -0.19 |
| EXP-004 | model_logit | +0.9% | -0.01 | -22.1% | -0.31 | -5.2% | +20.7% | -18.4% | -0.12 |
| EXP-004 | model_forest | +1.5% | +0.07 | -21.1% | -0.24 | -4.5% | +21.8% | -20.9% | -0.19 |
| EXP-004 | model_hgb_calibrated | +1.5% | +0.08 | -19.1% | -0.23 | -4.5% | +17.1% | -14.6% | -0.24 |
| EXP-004 | model_ensemble | +1.6% | +0.08 | -20.1% | -0.23 | -4.5% | +20.5% | -18.3% | -0.17 |
| EXP-005 | no_stop | +0.8% | -0.01 | -23.4% | -0.31 | -5.2% | +20.4% | -17.3% | -0.16 |
| EXP-005 | chandelier_3atr | +1.8% | +0.11 | -17.3% | -0.19 | -4.2% | +16.5% | -7.5% | +0.12 |
| EXP-005 | dd_breaker | +0.9% | -0.01 | -20.8% | -0.31 | -5.2% | +18.2% | -18.8% | -0.20 |
| EXP-005 | stop_guard | +0.8% | -0.02 | -21.3% | -0.32 | -5.2% | +20.1% | -17.2% | -0.18 |
| EXP-005 | no_vol_target | +3.1% | +0.19 | -40.8% | -0.11 | -2.9% | +30.5% | -35.9% | -0.22 |
| EXP-005 | target_vol_10 | +1.0% | -0.02 | -14.7% | -0.32 | -5.0% | +16.1% | -13.1% | -0.18 |
| EXP-005 | target_vol_20 | +0.7% | +0.00 | -27.3% | -0.30 | -5.3% | +24.4% | -20.3% | -0.14 |
| EXP-006 | bollinger_reversion | +1.1% | -0.05 | -3.9% | -0.35 | -4.9% | +8.5% | -1.7% | +0.26 |
| EXP-006 | miner_vs_gdx_reversion | +1.5% | +0.07 | -13.3% | -0.24 | -4.5% | +16.9% | -11.8% | -0.00 |
| EXP-007 | tb_model_tb_exits | +1.5% | +0.08 | -10.2% | -0.22 | -4.5% | +14.4% | -6.1% | +0.18 |
| EXP-007 | tb_model_base_exits | +2.1% | +0.14 | -13.3% | -0.16 | -4.0% | +16.6% | -17.3% | -0.28 |
| EXP-007 | base_model_tb_exits | -0.0% | -0.17 | -16.8% | -0.48 | -6.0% | +13.2% | -7.0% | -0.04 |
| EXP-013 | default_long | +1.9% | +0.12 | -22.3% | -0.19 | -4.1% | +20.9% | -19.0% | -0.17 |
| EXP-013 | default_long_full | +4.6% | +0.26 | -46.7% | -0.04 | -1.5% | +34.2% | -35.3% | -0.16 |
| EXP-013 | default_long_full_nostop | +2.3% | +0.15 | -47.5% | -0.15 | -3.7% | +35.8% | -35.6% | -0.12 |
| EXP-013 | default_long_full_chandelier | +4.2% | +0.24 | -42.9% | -0.06 | -1.8% | +19.3% | -30.8% | -0.42 |
| REF | buy_hold | +6.0% | +0.30 | -43.0% | +0.00 | +0.0% | +44.2% | -38.0% | +0.00 |
| REF | vol_sized_hold | +3.4% | +0.22 | -25.8% | -0.08 | -2.6% | +28.3% | -29.5% | -0.13 |

Verdicts are proposals. A change is only adopted when recorded in research/decisions.md.
