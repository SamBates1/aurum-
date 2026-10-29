# EXP-039: Mean reversion across 10 assets (real)

Historical simulation, net of costs, common dates 2006-06-01 → 2026-10-29 (first year warms up signals). Portfolio variants: equal sleeves across 10 assets, each sized by Aurum's volatility rule (15% / 21-day vol) and multiplied by the rule's 0/1 signal; baseline = the same sizing with no signal. 4 trial variants; PBO (dev) 96%.

## Portfolio verdicts vs the no-signal baseline

| Variant | pre ΔSharpe (better) | dev ΔSharpe (better) | holdout ΔSharpe (better) | dev 2× cost | DSR | Verdict |
|---|---|---|---|---|---|---|
| no-signal vol-sized (baseline) | +0.00 (0%) | +0.00 (0%) | +0.00 (0%) | +0.00 | – | baseline |
| equal weight, monthly (reference) | -0.23 (10%) | +0.08 (80%) | -0.05 (37%) | +0.08 | – | reference |
| rsi2_reversion | -0.02 (48%) | -0.17 (28%) | -0.47 (16%) | -0.30 | 0.73 | INCONCLUSIVE |
| bollinger_reversion | -0.46 (4%) | -0.12 (32%) | -0.49 (15%) | -0.18 | 0.78 | REJECT |
| zscore60_reversion | -0.66 (3%) | -0.18 (23%) | -0.35 (25%) | -0.21 | 0.72 | REJECT |
| extreme_drop_5d | -0.24 (30%) | -0.19 (32%) | -0.24 (37%) | -0.24 | 0.71 | REJECT |

## Portfolio scorecard

| Strategy | pre: CAGR / Sharpe / max DD | dev: CAGR / Sharpe / max DD | holdout: CAGR / Sharpe / max DD | Exposure | Costs/yr | Beta vs SPY | Longest drawdown |
|---|---|---|---|---|---|---|---|
| no-signal vol-sized (baseline) | +6.2% / +0.66 / -13.7% | +4.2% / +0.40 / -16.0% | +14.6% / +1.09 / -7.3% | 80% | 0.09% | +0.27 | 735 days |
| equal weight, monthly (reference) | +6.7% / +0.43 / -37.5% | +6.5% / +0.47 / -23.5% | +20.5% / +1.04 / -11.9% | 100% | 0.02% | +0.51 | 952 days |
| rsi2_reversion | +2.5% / +0.64 / -4.1% | +1.8% / +0.22 / -3.1% | +6.3% / +0.62 / -2.6% | 11% | 0.35% | +0.05 | 509 days |
| bollinger_reversion | +1.4% / +0.20 / -6.6% | +2.3% / +0.28 / -10.1% | +6.5% / +0.60 / -2.4% | 17% | 0.25% | +0.12 | 765 days |
| zscore60_reversion | +0.5% / -0.00 / -8.7% | +2.0% / +0.22 / -8.9% | +6.6% / +0.74 / -3.4% | 15% | 0.11% | +0.11 | 1666 days |
| extreme_drop_5d | +1.7% / +0.42 / -4.1% | +1.8% / +0.21 / -8.3% | +6.5% / +0.85 / -1.4% | 4% | 0.13% | +0.06 | 676 days |

## Each rule alone on each asset (long/flat, no vol sizing): share of asset-periods beating buy & hold

| Rule | Share of (asset, period) cells with higher Sharpe than buy & hold |
|---|---|
| extreme_drop_5d | 30% |
| rsi2_reversion | 30% |
| bollinger_reversion | 20% |
| zscore60_reversion | 20% |

## Figures

- [Equity curves and drawdowns](figures/equity_drawdown.png)
- [Sharpe minus buy & hold, each rule alone on each asset, long/flat (dev)](figures/heatmap_rule_asset_dev.png)
- [Sharpe minus buy & hold, each rule alone on each asset, long/flat (full)](figures/heatmap_rule_asset_full.png)
- [Portfolio Sharpe by period (pre / dev / holdout)](figures/sharpe_by_period.png)
- [Calendar-year returns](figures/annual_returns.png)
- [Sharpe by calendar year (stability across time)](figures/sharpe_by_year.png)
- [Candlestick chart with indicators: GLD](figures/candles_GLD.png)

## Pairs (market-neutral spread trades; descriptive, whole sample)

| Pair | Hedge ratio | ADF t (full) | Cointegrated (5%, full sample) | Share of 1-year windows cointegrated | Half-life (days) | Trade CAGR | Trade Sharpe | Max DD | Time in trade |
|---|---|---|---|---|---|---|---|---|---|
| SLV/GLD | 0.82 | -2.68 | no | 7% | 251 | -1.0% | -0.05 | -55.0% | 80% |
| GDX/GLD | 0.54 | -2.21 | no | 14% | 369 | -1.9% | -0.09 | -46.9% | 73% |
| IWM/SPY | 0.78 | -3.02 | no | 6% | 193 | -1.7% | -0.28 | -38.7% | 79% |
| TLT/IEF | 1.33 | -1.42 | no | 9% | 611 | -1.0% | -0.33 | -21.6% | 73% |

Pair-trade returns are close-to-close with no cash interest, so they are not directly comparable with the portfolio rows above.

## Figures

- [Equity curves and drawdowns](figures/pairs_equity.png)
