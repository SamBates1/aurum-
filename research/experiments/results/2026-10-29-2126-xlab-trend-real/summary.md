# EXP-038: Trend following and momentum across 10 assets (real)

Historical simulation, net of costs, common dates 2006-06-01 → 2026-10-29 (first year warms up signals). Portfolio variants: equal sleeves across 10 assets, each sized by Aurum's volatility rule (15% / 21-day vol) and multiplied by the rule's 0/1 signal; baseline = the same sizing with no signal. 13 trial variants; PBO (dev) 80%.

## Portfolio verdicts vs the no-signal baseline

| Variant | pre ΔSharpe (better) | dev ΔSharpe (better) | holdout ΔSharpe (better) | dev 2× cost | DSR | Verdict |
|---|---|---|---|---|---|---|
| no-signal vol-sized (baseline) | +0.00 (0%) | +0.00 (0%) | +0.00 (0%) | +0.00 | – | baseline |
| equal weight, monthly (reference) | -0.23 (10%) | +0.08 (80%) | -0.05 (37%) | +0.08 | – | reference |
| sma_50_200 | +0.00 (48%) | -0.04 (40%) | -0.10 (27%) | -0.04 | 0.72 | REJECT |
| sma_20_100 | -0.01 (47%) | -0.14 (21%) | -0.07 (34%) | -0.16 | 0.60 | REJECT |
| ema_20_100 | -0.00 (50%) | -0.07 (33%) | -0.01 (44%) | -0.09 | 0.69 | INCONCLUSIVE |
| above_sma50 | -0.09 (36%) | -0.09 (32%) | -0.22 (19%) | -0.19 | 0.67 | REJECT |
| above_sma100 | -0.05 (42%) | -0.20 (15%) | -0.22 (13%) | -0.27 | 0.53 | REJECT |
| above_sma200 | -0.02 (46%) | -0.08 (30%) | -0.04 (36%) | -0.13 | 0.68 | INCONCLUSIVE |
| tsmom_63 | +0.05 (59%) | -0.24 (10%) | -0.32 (6%) | -0.31 | 0.48 | REJECT |
| tsmom_126 | +0.10 (64%) | +0.04 (55%) | -0.15 (19%) | -0.01 | 0.80 | REJECT (failed on holdout) |
| tsmom_252 | +0.11 (66%) | +0.04 (58%) | -0.10 (10%) | +0.01 | 0.80 | REJECT (failed on holdout) |
| donchian_50_20 | -0.06 (43%) | +0.05 (55%) | -0.29 (18%) | +0.01 | 0.81 | REJECT (failed on holdout) |
| multi_tf_1_3_12 | +0.00 (52%) | -0.22 (19%) | -0.61 (3%) | -0.34 | 0.51 | REJECT |
| xs_momentum_126_top3 | -0.03 (44%) | +0.02 (53%) | -0.01 (51%) | +0.01 | 0.78 | INCONCLUSIVE |
| xs_momentum_252_21_top3 | +0.15 (68%) | -0.10 (33%) | +0.14 (62%) | -0.11 | 0.65 | INCONCLUSIVE |

## Portfolio scorecard

| Strategy | pre: CAGR / Sharpe / max DD | dev: CAGR / Sharpe / max DD | holdout: CAGR / Sharpe / max DD | Exposure | Costs/yr | Beta vs SPY | Longest drawdown |
|---|---|---|---|---|---|---|---|
| no-signal vol-sized (baseline) | +6.2% / +0.66 / -13.7% | +4.2% / +0.40 / -16.0% | +14.6% / +1.09 / -7.3% | 80% | 0.09% | +0.27 | 735 days |
| equal weight, monthly (reference) | +6.7% / +0.43 / -37.5% | +6.5% / +0.47 / -23.5% | +20.5% / +1.04 / -11.9% | 100% | 0.02% | +0.51 | 952 days |
| sma_50_200 | +5.1% / +0.66 / -7.8% | +3.1% / +0.36 / -9.6% | +12.7% / +0.99 / -6.7% | 52% | 0.09% | +0.15 | 641 days |
| sma_20_100 | +4.9% / +0.66 / -7.8% | +2.5% / +0.25 / -9.9% | +12.0% / +1.02 / -5.1% | 52% | 0.14% | +0.13 | 796 days |
| ema_20_100 | +4.9% / +0.66 / -7.9% | +2.9% / +0.33 / -8.5% | +12.8% / +1.08 / -5.2% | 54% | 0.14% | +0.13 | 648 days |
| above_sma50 | +3.9% / +0.57 / -6.4% | +2.7% / +0.31 / -12.5% | +10.1% / +0.88 / -3.9% | 49% | 0.57% | +0.10 | 897 days |
| above_sma100 | +4.4% / +0.62 / -6.5% | +2.1% / +0.19 / -10.0% | +10.6% / +0.87 / -5.1% | 52% | 0.38% | +0.11 | 965 days |
| above_sma200 | +4.8% / +0.64 / -7.5% | +2.8% / +0.32 / -7.5% | +12.7% / +1.05 / -5.2% | 53% | 0.29% | +0.12 | 591 days |
| tsmom_63 | +5.1% / +0.71 / -7.4% | +2.0% / +0.16 / -9.7% | +9.9% / +0.77 / -4.7% | 52% | 0.43% | +0.12 | 925 days |
| tsmom_126 | +5.6% / +0.76 / -6.9% | +3.5% / +0.44 / -7.7% | +11.7% / +0.94 / -5.1% | 53% | 0.30% | +0.13 | 599 days |
| tsmom_252 | +5.7% / +0.77 / -7.1% | +3.5% / +0.44 / -7.9% | +12.9% / +0.99 / -7.0% | 52% | 0.21% | +0.14 | 579 days |
| donchian_50_20 | +3.7% / +0.61 / -4.1% | +3.0% / +0.44 / -6.0% | +8.9% / +0.81 / -3.8% | 35% | 0.18% | +0.07 | 1339 days |
| multi_tf_1_3_12 | +3.6% / +0.66 / -5.2% | +1.8% / +0.18 / -7.2% | +7.1% / +0.49 / -4.1% | 30% | 0.49% | +0.05 | 672 days |
| xs_momentum_126_top3 | +8.4% / +0.63 / -20.6% | +5.6% / +0.42 / -19.1% | +20.2% / +1.08 / -12.6% | 77% | 0.21% | +0.24 | 600 days |
| xs_momentum_252_21_top3 | +10.9% / +0.81 / -18.8% | +4.1% / +0.30 / -17.8% | +23.5% / +1.24 / -13.1% | 73% | 0.17% | +0.25 | 463 days |

## Each rule alone on each asset (long/flat, no vol sizing): share of asset-periods beating buy & hold

| Rule | Share of (asset, period) cells with higher Sharpe than buy & hold |
|---|---|
| above_sma200 | 43% |
| sma_50_200 | 43% |
| sma_20_100 | 43% |
| tsmom_126 | 43% |
| ema_20_100 | 40% |
| tsmom_252 | 37% |
| donchian_50_20 | 37% |
| tsmom_63 | 37% |
| above_sma100 | 33% |
| multi_tf_1_3_12 | 30% |
| above_sma50 | 27% |

## Figures

- [Equity curves and drawdowns](figures/equity_drawdown.png)
- [Sharpe minus buy & hold, each rule alone on each asset, long/flat (dev)](figures/heatmap_rule_asset_dev.png)
- [Sharpe minus buy & hold, each rule alone on each asset, long/flat (full)](figures/heatmap_rule_asset_full.png)
- [Portfolio Sharpe by period (pre / dev / holdout)](figures/sharpe_by_period.png)
- [Calendar-year returns](figures/annual_returns.png)
- [Sharpe by calendar year (stability across time)](figures/sharpe_by_year.png)
- [Candlestick chart with indicators: GLD](figures/candles_GLD.png)
