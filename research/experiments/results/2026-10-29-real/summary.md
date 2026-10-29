# Experiment results: 2026-10-29 (real)

Tickers: GLD, SLV, GDX, NEM, AEM, WPM. Development 2013-10-18 → 2023-12-31; holdout from 2024-01-01. Config `2c9c656d1a4b`. 26 variants tried.

**Probability of backtest overfitting across all variants (development):** 77% (12870 CSCV splits). Around 50% means picking the best-looking variant is no better than chance.

Portfolio level, net of costs. ΔSharpe is vs the baseline over identical dates; 'better' is the share of block-bootstrap resamples in which the variant beat the baseline; DSR is the deflated Sharpe ratio (probability the Sharpe is real after allowing for all variants tried).

| Exp | Variant | Dev Sharpe | Dev ΔSharpe | better | Dev ΔSharpe 2× cost | Dev max DD | Holdout ΔSharpe | DSR | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| BASE | baseline | -0.01 | +0.00 | 0% | +0.00 | -21.4% | +0.00 | 0.25 | baseline |
| EXP-001 | stop_on_close | -0.13 | -0.12 | 0% | -0.12 | -23.8% | +0.03 | 0.14 | REJECT |
| EXP-002 | tsmom_12m | -0.14 | -0.13 | 32% | -0.09 | -15.5% | -0.11 | 0.13 | INCONCLUSIVE |
| EXP-002 | tsmom_1_3_12 | -0.15 | -0.14 | 21% | -0.13 | -22.3% | -0.01 | 0.13 | REJECT |
| EXP-002 | donchian_50_20 | +0.07 | +0.08 | 65% | +0.13 | -13.3% | -0.35 | 0.33 | INCONCLUSIVE |
| EXP-002 | baseline_trend_filter | -0.17 | -0.17 | 6% | -0.15 | -20.5% | +0.07 | 0.11 | REJECT |
| EXP-003 | gate_real_yields | +0.03 | +0.04 | 61% | +0.07 | -17.5% | -0.24 | 0.29 | INCONCLUSIVE |
| EXP-003 | gate_vix | -0.12 | -0.11 | 3% | -0.11 | -22.9% | +0.00 | 0.15 | REJECT |
| EXP-003 | gate_dollar | -0.05 | -0.04 | 42% | -0.01 | -13.8% | -0.22 | 0.21 | REJECT |
| EXP-003 | gate_gold_trend | -0.20 | -0.19 | 8% | -0.17 | -21.3% | -0.04 | 0.10 | REJECT |
| EXP-004 | model_logit | -0.01 | +0.00 | 53% | +0.02 | -22.1% | +0.05 | 0.25 | INCONCLUSIVE |
| EXP-004 | model_forest | +0.07 | +0.08 | 77% | +0.10 | -21.1% | -0.02 | 0.33 | INCONCLUSIVE |
| EXP-004 | model_hgb_calibrated | +0.08 | +0.09 | 78% | +0.10 | -19.0% | -0.07 | 0.35 | INCONCLUSIVE |
| EXP-004 | model_ensemble | +0.05 | +0.06 | 82% | +0.08 | -20.3% | +0.00 | 0.32 | INCONCLUSIVE |
| EXP-005 | no_stop | -0.01 | -0.00 | 46% | +0.01 | -23.5% | +0.00 | 0.25 | REJECT |
| EXP-005 | chandelier_3atr | +0.11 | +0.12 | 94% | +0.11 | -17.6% | +0.26 | 0.39 | INCONCLUSIVE |
| EXP-005 | dd_breaker | -0.03 | -0.02 | 20% | -0.02 | -21.3% | -0.06 | 0.23 | REJECT |
| EXP-005 | stop_guard | -0.04 | -0.03 | 22% | -0.03 | -22.1% | -0.03 | 0.22 | REJECT |
| EXP-005 | no_vol_target | +0.19 | +0.20 | 95% | +0.20 | -41.5% | -0.09 | 0.48 | INCONCLUSIVE |
| EXP-005 | target_vol_10 | -0.01 | -0.00 | 47% | +0.00 | -14.6% | -0.03 | 0.25 | REJECT |
| EXP-005 | target_vol_20 | +0.01 | +0.02 | 92% | +0.02 | -27.7% | +0.00 | 0.27 | INCONCLUSIVE |
| EXP-006 | bollinger_reversion | -0.05 | -0.04 | 48% | -0.01 | -3.9% | +0.43 | 0.21 | INCONCLUSIVE |
| EXP-006 | miner_vs_gdx_reversion | +0.06 | +0.07 | 68% | +0.09 | -13.3% | +0.17 | 0.33 | INCONCLUSIVE |
| EXP-007 | tb_model_tb_exits | +0.06 | +0.07 | 66% | -0.04 | -10.1% | +0.21 | 0.32 | INCONCLUSIVE |
| EXP-007 | tb_model_base_exits | +0.13 | +0.14 | 87% | +0.13 | -13.2% | -0.10 | 0.40 | INCONCLUSIVE |
| EXP-007 | base_model_tb_exits | -0.14 | -0.13 | 16% | -0.23 | -16.5% | +0.01 | 0.14 | REJECT |

Verdicts are proposals. A change is only adopted when recorded in research/decisions.md.
