# Lab results: core set, 2026-10-29T13:31 UTC (real)

Assets: GLD, SLV, GDX, NEM, AEM, WPM; portfolio from 2006-06-30 (common start). Periods: pre 2006-06-30 → 2013-10-17; dev 2013-10-18 → 2023-12-31; holdout 2024-01-01 → now. Orders fill at the next open; net of costs; equal sleeves. Baseline = `vol_hold_gvz` (the traded strategy). 7 trial variants; PBO (development) 41%.

## Return, risk and Sharpe by period

| Exp | Variant | pre CAGR | pre Sharpe | pre max DD | dev CAGR | dev Sharpe | dev max DD | holdout CAGR | holdout Sharpe | holdout max DD | Rebal./yr |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE | vol_hold_gvz | +2.8% | +0.19 | -32.1% | +3.4% | +0.24 | -22.0% | +23.5% | +1.33 | -13.4% | 39 |
| REF | buy_hold | +4.7% | +0.28 | -63.9% | +6.0% | +0.30 | -41.1% | +39.0% | +1.00 | -36.7% | 0 |
| REF | vol_hold_21d | +4.2% | +0.28 | -31.4% | +2.1% | +0.13 | -27.9% | +24.2% | +1.25 | -14.2% | 29 |
| EXP-022 | weekly | +3.1% | +0.21 | -30.8% | +3.7% | +0.26 | -22.6% | +23.1% | +1.29 | -13.1% | 20 |
| EXP-022 | whole_shares_10k | +2.9% | +0.20 | -31.5% | +3.4% | +0.24 | -21.7% | +23.3% | +1.33 | -13.3% | 41 |
| EXP-022 | whole_shares_100k | +2.8% | +0.19 | -31.9% | +3.4% | +0.24 | -21.9% | +23.5% | +1.33 | -13.5% | 39 |
| EXP-023 | miner_gdx_tilt | +2.7% | +0.18 | -32.8% | +4.4% | +0.31 | -22.5% | +25.9% | +1.39 | -14.7% | 43 |
| EXP-023 | chandelier_3atr | +2.4% | +0.17 | -20.4% | +2.8% | +0.21 | -15.5% | +16.3% | +1.07 | -10.8% | 40 |
| EXP-024 | fv_rolling | +2.3% | +0.15 | -34.1% | +3.6% | +0.27 | -21.4% | +19.0% | +1.27 | -10.6% | 40 |
| EXP-024 | fv_expanding | +2.2% | +0.15 | -34.3% | +3.4% | +0.25 | -22.1% | +18.4% | +1.31 | -10.4% | 37 |
| EXP-025 | cot_contrarian | +2.4% | +0.16 | -34.3% | +3.7% | +0.26 | -22.2% | +20.6% | +1.24 | -13.7% | 40 |
| EXP-025 | cot_flow | +3.1% | +0.21 | -31.3% | +3.2% | +0.23 | -21.5% | +23.3% | +1.33 | -14.0% | 44 |
| EXP-028 | risk_10 | +2.2% | +0.16 | -22.6% | +3.0% | +0.26 | -15.4% | +17.0% | +1.32 | -8.8% | 25 |
| EXP-028 | risk_20 | +3.1% | +0.20 | -39.3% | +3.7% | +0.24 | -26.8% | +28.1% | +1.26 | -18.3% | 46 |
| EXP-028 | risk_25 | +3.2% | +0.20 | -45.4% | +4.0% | +0.24 | -30.6% | +32.3% | +1.23 | -22.1% | 49 |
| EXP-028 | risk_30 | +3.0% | +0.19 | -50.1% | +3.9% | +0.23 | -34.0% | +34.8% | +1.17 | -26.1% | 48 |

## Versus the traded strategy (ΔSharpe; 'better' = share of block-bootstrap resamples)

| Exp | Variant | pre ΔSharpe | pre better | dev ΔSharpe | dev better | holdout ΔSharpe | holdout better | dev ΔSharpe 2× cost | DSR | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| BASE | vol_hold_gvz | +0.00 | 0% | +0.00 | 0% | +0.00 | 0% | +0.00 | 0.73 | baseline |
| REF | buy_hold | +0.09 | 74% | +0.06 | 74% | -0.33 | 3% | +0.08 | – | reference |
| REF | vol_hold_21d | +0.09 | 89% | -0.11 | 1% | -0.08 | 22% | -0.10 | – | reference |
| EXP-022 | weekly | +0.02 | 74% | +0.02 | 86% | -0.03 | 21% | +0.03 | – | descriptive |
| EXP-022 | whole_shares_10k | +0.01 | 79% | +0.00 | 59% | -0.00 | 44% | -0.01 | – | descriptive |
| EXP-022 | whole_shares_100k | +0.00 | 62% | +0.00 | 83% | +0.00 | 74% | +0.00 | – | descriptive |
| EXP-023 | miner_gdx_tilt | -0.01 | 30% | +0.08 | 100% | +0.06 | 91% | +0.07 | 0.80 | INCONCLUSIVE |
| EXP-023 | chandelier_3atr | -0.02 | 42% | -0.03 | 39% | -0.26 | 9% | -0.07 | 0.70 | REJECT |
| EXP-024 | fv_rolling | -0.04 | 16% | +0.03 | 77% | -0.06 | 19% | +0.03 | 0.76 | INCONCLUSIVE |
| EXP-024 | fv_expanding | -0.04 | 11% | +0.02 | 69% | -0.02 | 24% | +0.02 | 0.75 | INCONCLUSIVE |
| EXP-025 | cot_contrarian | -0.03 | 18% | +0.02 | 73% | -0.09 | 8% | +0.02 | 0.75 | INCONCLUSIVE |
| EXP-025 | cot_flow | +0.02 | 80% | -0.01 | 35% | +0.01 | 54% | -0.02 | 0.72 | REJECT |
| EXP-028 | risk_10 | -0.03 | 10% | +0.02 | 86% | -0.00 | 41% | +0.02 | – | descriptive |
| EXP-028 | risk_20 | +0.01 | 63% | +0.00 | 54% | -0.06 | 2% | +0.00 | – | descriptive |
| EXP-028 | risk_25 | +0.01 | 63% | +0.01 | 58% | -0.10 | 3% | +0.01 | – | descriptive |
| EXP-028 | risk_30 | +0.00 | 50% | -0.01 | 38% | -0.15 | 1% | -0.01 | – | descriptive |

## Versus simply holding (buy & hold): ΔSharpe and share of resamples better

| Variant | pre ΔSharpe | pre better | dev ΔSharpe | dev better | holdout ΔSharpe | holdout better |
|---|---|---|---|---|---|---|
| vol_hold_gvz | -0.09 | 26% | -0.06 | 26% | +0.33 | 97% |
| buy_hold | +0.00 | 0% | +0.00 | 0% | +0.00 | 0% |
| vol_hold_21d | -0.00 | 49% | -0.17 | 2% | +0.25 | 89% |
| weekly | -0.07 | 31% | -0.04 | 34% | +0.29 | 95% |
| whole_shares_10k | -0.08 | 27% | -0.06 | 26% | +0.33 | 97% |
| whole_shares_100k | -0.09 | 26% | -0.06 | 27% | +0.33 | 97% |
| miner_gdx_tilt | -0.10 | 20% | +0.01 | 56% | +0.39 | 99% |
| chandelier_3atr | -0.11 | 27% | -0.09 | 24% | +0.07 | 56% |
| fv_rolling | -0.13 | 18% | -0.03 | 40% | +0.27 | 93% |
| fv_expanding | -0.13 | 18% | -0.05 | 33% | +0.31 | 96% |
| cot_contrarian | -0.12 | 22% | -0.04 | 36% | +0.24 | 93% |
| cot_flow | -0.07 | 32% | -0.08 | 22% | +0.33 | 97% |
| risk_10 | -0.11 | 20% | -0.05 | 34% | +0.32 | 96% |
| risk_20 | -0.08 | 26% | -0.06 | 25% | +0.26 | 94% |
| risk_25 | -0.08 | 26% | -0.06 | 25% | +0.23 | 92% |
| risk_30 | -0.09 | 22% | -0.07 | 16% | +0.17 | 88% |

## Stress windows (return / worst fall inside the window)

| Window | vol_hold_gvz | vol_hold_21d | buy_hold | risk_10 | risk_20 | risk_25 | risk_30 |
|---|---|---|---|---|---|---|---|
| 2008 financial crisis | -11.0% / -18.7% | -11.9% / -19.9% | -35.7% / -63.9% | -7.5% / -13.3% | -16.5% / -25.8% | -19.8% / -31.7% | -24.3% / -37.1% |
| 2011-15 gold bear market | -38.5% / -39.7% | -42.2% / -43.4% | -62.8% / -65.2% | -27.5% / -28.6% | -46.4% / -48.0% | -52.6% / -54.2% | -57.7% / -59.3% |
| 2013 gold crash | -15.4% / -17.0% | -16.6% / -18.5% | -30.5% / -34.9% | -10.5% / -11.7% | -19.5% / -21.5% | -22.4% / -24.9% | -24.9% / -27.5% |
| 2020 Covid crash | -5.1% / -8.1% | -5.8% / -10.1% | -14.2% / -24.6% | -3.0% / -5.2% | -7.1% / -10.8% | -9.3% / -13.6% | -10.8% / -15.9% |
| 2022 rate rises | -10.5% / -15.9% | -13.6% / -20.7% | -24.9% / -37.8% | -6.7% / -10.8% | -13.8% / -20.6% | -16.4% / -24.3% | -19.0% / -27.5% |

## Calendar-year returns

| Year | vol_hold_gvz | buy_hold | risk_20 | risk_25 |
|---|---|---|---|---|
| 2006 | +1.7% | +4.9% | +1.6% | +1.3% |
| 2007 | +16.3% | +28.3% | +18.7% | +21.5% |
| 2008 | -1.8% | -23.0% | -4.8% | -6.4% |
| 2009 | +12.0% | +35.7% | +15.7% | +18.8% |
| 2010 | +20.2% | +65.6% | +27.9% | +34.8% |
| 2011 | -4.2% | -18.3% | -5.9% | -9.3% |
| 2012 | +0.0% | +11.5% | +0.6% | +1.1% |
| 2013 | -21.6% | -40.8% | -26.5% | -30.2% |
| 2014 | -2.6% | -6.9% | -3.3% | -3.7% |
| 2015 | -8.5% | -18.1% | -11.1% | -13.0% |
| 2016 | +15.2% | +37.1% | +19.1% | +22.8% |
| 2017 | +6.8% | +12.0% | +8.4% | +9.9% |
| 2018 | -4.6% | -7.9% | -6.6% | -7.9% |
| 2019 | +22.8% | +36.2% | +29.4% | +34.1% |
| 2020 | +9.9% | +32.7% | +12.1% | +13.1% |
| 2021 | -1.5% | -5.0% | -2.2% | -2.8% |
| 2022 | -1.2% | -5.2% | -2.3% | -3.5% |
| 2023 | +6.0% | +13.5% | +6.3% | +7.1% |
| 2024 | +16.9% | +20.6% | +18.3% | +20.1% |
| 2025 | +50.5% | +111.9% | +65.0% | +76.4% |
| 2026 | +2.4% | -2.1% | +2.2% | +2.9% |

**Variants dropped because they raised errors:**

- `epu_tilt`: SLV: ValueError: cannot reindex on an axis with duplicate labels
- `gpr_tilt`: WPM: RuntimeError: gpr unavailable

**Data problems:**

- lab:gpr: unavailable (IndexError: index 0 is out of bounds for axis 0 with size 0)

Verdicts are proposals. A change is only adopted when recorded in research/decisions.md.
