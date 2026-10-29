# Lab results: other set, 2026-10-29T13:32 UTC (real)

Assets: GDXJ, SIL, RGLD, FNV, KGC, AU, PPLT, PALL; portfolio from 2010-05-19 (common start). Periods: pre 2010-05-19 → 2013-10-17; dev 2013-10-18 → 2023-12-31; holdout 2024-01-01 → now. Orders fill at the next open; net of costs; equal sleeves. Baseline = `vol_hold_gvz` (the traded strategy). 8 trial variants; PBO (development) 88%.

## Return, risk and Sharpe by period

| Exp | Variant | pre CAGR | pre Sharpe | pre max DD | dev CAGR | dev Sharpe | dev max DD | holdout CAGR | holdout Sharpe | holdout max DD | Rebal./yr |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE | vol_hold_gvz | -2.8% | -0.21 | -27.8% | +2.5% | +0.17 | -26.3% | +17.8% | +1.03 | -12.5% | 44 |
| REF | buy_hold | -3.7% | +0.02 | -51.3% | +5.6% | +0.29 | -49.4% | +30.4% | +0.84 | -34.3% | 0 |
| REF | vol_hold_21d | -2.4% | -0.13 | -28.3% | +1.4% | +0.08 | -32.7% | +18.0% | +0.97 | -12.0% | 32 |
| EXP-022 | weekly | -2.3% | -0.17 | -27.3% | +2.6% | +0.17 | -27.0% | +18.1% | +1.05 | -12.3% | 22 |
| EXP-022 | whole_shares_10k | -3.0% | -0.24 | -27.9% | +2.3% | +0.15 | -26.4% | +18.1% | +1.06 | -12.0% | 44 |
| EXP-022 | whole_shares_100k | -2.7% | -0.21 | -27.7% | +2.5% | +0.17 | -26.3% | +17.8% | +1.03 | -12.2% | 44 |
| EXP-023 | miner_gdx_tilt | -2.9% | -0.20 | -29.8% | +2.2% | +0.14 | -28.2% | +19.7% | +1.08 | -13.5% | 48 |
| EXP-023 | chandelier_3atr | -0.6% | -0.05 | -17.9% | +1.6% | +0.08 | -16.4% | +16.2% | +1.09 | -10.5% | 42 |
| EXP-024 | fv_rolling | -3.0% | -0.22 | -29.7% | +2.4% | +0.17 | -25.2% | +14.6% | +0.97 | -9.7% | 42 |
| EXP-024 | fv_expanding | -3.0% | -0.21 | -29.5% | +2.5% | +0.18 | -25.5% | +14.3% | +1.02 | -9.3% | 39 |
| EXP-025 | cot_contrarian | -3.3% | -0.22 | -29.7% | +2.5% | +0.17 | -27.2% | +16.1% | +0.99 | -12.3% | 45 |
| EXP-025 | cot_flow | -3.1% | -0.24 | -27.6% | +2.2% | +0.14 | -26.0% | +18.0% | +1.06 | -12.7% | 49 |
| EXP-026 | epu_tilt | -2.8% | -0.21 | -27.8% | +2.5% | +0.17 | -26.3% | +17.8% | +1.03 | -12.5% | 44 |
| EXP-028 | risk_10 | -2.0% | -0.25 | -19.4% | +2.1% | +0.16 | -19.2% | +13.7% | +1.07 | -7.7% | 27 |
| EXP-028 | risk_20 | -3.9% | -0.21 | -35.6% | +2.5% | +0.16 | -32.7% | +21.4% | +1.00 | -16.6% | 55 |
| EXP-028 | risk_25 | -5.0% | -0.20 | -41.4% | +2.8% | +0.17 | -38.4% | +24.8% | +0.98 | -20.7% | 60 |
| EXP-028 | risk_30 | -5.4% | -0.17 | -45.3% | +2.6% | +0.16 | -42.6% | +26.9% | +0.94 | -24.8% | 60 |

## Versus the traded strategy (ΔSharpe; 'better' = share of block-bootstrap resamples)

| Exp | Variant | pre ΔSharpe | pre better | dev ΔSharpe | dev better | holdout ΔSharpe | holdout better | dev ΔSharpe 2× cost | DSR | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| BASE | vol_hold_gvz | +0.00 | 0% | +0.00 | 0% | +0.00 | 0% | +0.00 | 0.65 | baseline |
| REF | buy_hold | +0.23 | 98% | +0.12 | 87% | -0.19 | 13% | +0.16 | – | reference |
| REF | vol_hold_21d | +0.09 | 73% | -0.09 | 4% | -0.06 | 27% | -0.08 | – | reference |
| EXP-022 | weekly | +0.04 | 80% | +0.01 | 59% | +0.02 | 59% | +0.02 | – | descriptive |
| EXP-022 | whole_shares_10k | -0.03 | 3% | -0.01 | 11% | +0.03 | 96% | +0.01 | – | descriptive |
| EXP-022 | whole_shares_100k | +0.01 | 82% | -0.00 | 44% | +0.00 | 67% | +0.00 | – | descriptive |
| EXP-023 | miner_gdx_tilt | +0.01 | 64% | -0.03 | 10% | +0.05 | 84% | -0.04 | 0.61 | REJECT |
| EXP-023 | chandelier_3atr | +0.16 | 74% | -0.09 | 24% | +0.06 | 59% | -0.14 | 0.54 | INCONCLUSIVE |
| EXP-024 | fv_rolling | -0.00 | 50% | +0.00 | 51% | -0.06 | 20% | +0.00 | 0.65 | INCONCLUSIVE |
| EXP-024 | fv_expanding | -0.00 | 50% | +0.01 | 58% | -0.01 | 22% | +0.02 | 0.66 | INCONCLUSIVE |
| EXP-025 | cot_contrarian | -0.01 | 46% | +0.00 | 56% | -0.04 | 24% | +0.01 | 0.65 | INCONCLUSIVE |
| EXP-025 | cot_flow | -0.03 | 31% | -0.02 | 26% | +0.03 | 72% | -0.03 | 0.62 | REJECT |
| EXP-026 | epu_tilt | +0.00 | 0% | +0.00 | 0% | +0.00 | 0% | +0.00 | 0.65 | INCONCLUSIVE |
| EXP-028 | risk_10 | -0.03 | 6% | -0.01 | 34% | +0.04 | 88% | +0.00 | – | descriptive |
| EXP-028 | risk_20 | +0.00 | 56% | -0.01 | 33% | -0.03 | 9% | -0.01 | – | descriptive |
| EXP-028 | risk_25 | +0.01 | 59% | +0.01 | 56% | -0.05 | 10% | +0.01 | – | descriptive |
| EXP-028 | risk_30 | +0.05 | 89% | -0.00 | 47% | -0.09 | 5% | +0.01 | – | descriptive |

## Versus simply holding (buy & hold): ΔSharpe and share of resamples better

| Variant | pre ΔSharpe | pre better | dev ΔSharpe | dev better | holdout ΔSharpe | holdout better |
|---|---|---|---|---|---|---|
| vol_hold_gvz | -0.23 | 2% | -0.12 | 13% | +0.19 | 87% |
| buy_hold | +0.00 | 0% | +0.00 | 0% | +0.00 | 0% |
| vol_hold_21d | -0.14 | 10% | -0.21 | 1% | +0.13 | 78% |
| weekly | -0.18 | 5% | -0.11 | 13% | +0.21 | 92% |
| whole_shares_10k | -0.26 | 1% | -0.13 | 10% | +0.22 | 90% |
| whole_shares_100k | -0.22 | 2% | -0.12 | 13% | +0.20 | 87% |
| miner_gdx_tilt | -0.22 | 2% | -0.15 | 5% | +0.24 | 93% |
| chandelier_3atr | -0.07 | 38% | -0.21 | 10% | +0.25 | 84% |
| fv_rolling | -0.23 | 1% | -0.12 | 16% | +0.14 | 79% |
| fv_expanding | -0.23 | 1% | -0.11 | 18% | +0.18 | 86% |
| cot_contrarian | -0.24 | 1% | -0.12 | 17% | +0.16 | 82% |
| cot_flow | -0.25 | 1% | -0.14 | 10% | +0.22 | 89% |
| epu_tilt | -0.23 | 2% | -0.12 | 13% | +0.19 | 87% |
| risk_10 | -0.26 | 1% | -0.13 | 11% | +0.24 | 91% |
| risk_20 | -0.23 | 1% | -0.13 | 10% | +0.16 | 84% |
| risk_25 | -0.22 | 1% | -0.12 | 12% | +0.14 | 82% |
| risk_30 | -0.18 | 2% | -0.12 | 7% | +0.10 | 77% |

## Stress windows (return / worst fall inside the window)

| Window | vol_hold_gvz | vol_hold_21d | buy_hold | risk_10 | risk_20 | risk_25 | risk_30 |
|---|---|---|---|---|---|---|---|
| 2008 financial crisis | – / – | – / – | – / – | – / – | – / – | – / – | – / – |
| 2011-15 gold bear market | -33.0% / -34.6% | -38.8% / -40.3% | -55.7% / -58.4% | -24.2% / -25.4% | -41.0% / -42.9% | -46.9% / -49.0% | -50.9% / -53.2% |
| 2013 gold crash | -11.9% / -13.7% | -13.8% / -15.8% | -28.4% / -33.5% | -8.2% / -9.5% | -15.4% / -17.7% | -18.5% / -21.3% | -21.2% / -24.3% |
| 2020 Covid crash | -6.3% / -10.3% | -7.8% / -12.7% | -16.6% / -33.6% | -3.6% / -6.7% | -9.0% / -13.7% | -10.8% / -16.3% | -12.6% / -18.8% |
| 2022 rate rises | -8.3% / -12.0% | -10.8% / -16.0% | -24.2% / -34.8% | -5.1% / -8.0% | -11.2% / -15.7% | -14.1% / -19.0% | -17.2% / -22.0% |

## Calendar-year returns

| Year | vol_hold_gvz | buy_hold | risk_20 | risk_25 |
|---|---|---|---|---|
| 2010 | +12.1% | +37.2% | +15.9% | +19.1% |
| 2011 | -5.4% | -15.6% | -7.6% | -10.0% |
| 2012 | -1.1% | +8.1% | -1.7% | -1.3% |
| 2013 | -15.7% | -35.3% | -20.0% | -23.6% |
| 2014 | +2.8% | +5.6% | +4.6% | +6.0% |
| 2015 | -13.7% | -25.2% | -17.6% | -21.3% |
| 2016 | +13.6% | +40.4% | +16.6% | +19.1% |
| 2017 | +12.0% | +29.5% | +16.6% | +19.6% |
| 2018 | -2.8% | -1.7% | -4.0% | -5.1% |
| 2019 | +23.7% | +47.6% | +30.5% | +39.8% |
| 2020 | +3.4% | +17.0% | +3.7% | +5.2% |
| 2021 | -2.6% | -7.4% | -4.0% | -5.2% |
| 2022 | -0.6% | -2.9% | -2.2% | -3.5% |
| 2023 | -3.0% | -14.2% | -6.7% | -9.4% |
| 2024 | +7.7% | +6.0% | +7.5% | +7.2% |
| 2025 | +46.6% | +104.1% | +60.7% | +75.7% |
| 2026 | -0.0% | -3.0% | -0.6% | -1.5% |

**Variants dropped because they raised errors:**

- `gpr_tilt`: PALL: RuntimeError: gpr unavailable

**Data problems:**

- lab:gpr: unavailable (IndexError: index 0 is out of bounds for axis 0 with size 0)

Verdicts are proposals. A change is only adopted when recorded in research/decisions.md.
