# EXP-003: Regime gates

| Field | |
|---|---|
| Status | Run 2026-10-29 on real data: see Results |
| Origin | Erb & Harvey (2013) [S3]; RBC on the 2022 break in the gold/real-yield link [S4]; HMM regime literature [S8][S9]. |
| Current Aurum equivalent | Macro variables are model features, but nothing stops new entries in hostile regimes. |

## Hypothesis
Blocking new entries in unfavourable macro or volatility regimes reduces drawdown per unit of risk without lowering Sharpe.

## Variants (fixed before running)
Entry blocked while: `gate_real_yields` 10y real yield rose over the last 63 trading days (FRED, lagged 2 business days); `gate_vix` VIX > 30; `gate_dollar` dollar index above its 200-day average; `gate_gold_trend` gold futures below their 200-day average. Exits unchanged.

## Acceptance criteria
Risk-control path is the relevant one: volatility-adjusted drawdown -20% with ΔSharpe ≥ -0.05, holding on the holdout. See [README](README.md#acceptance-criteria-applied-automatically-by-run_experimentspyverdict).

## Main risks and limitations
The 2022 regime break means a gate that worked in 2010–2021 may fail in the holdout; that is exactly what the holdout tests. HMMs deliberately excluded (see topics/regimes.md).

## Results (real data, run 2026-10-29, `results/2026-10-29-real/`)
Portfolio of 6 sleeves, net of costs, vs the baseline over identical dates. Development 2013-10-18 → 2023-12-31;
holdout from 2024-01-01. 26 variants tried in total; PBO across them 77%.

| Variant | Dev Sharpe | Dev ΔSharpe | better | ΔSharpe 2× cost | Dev max DD | Holdout ΔSharpe | DSR | Verdict |
|---|---|---|---|---|---|---|---|---|
| gate_real_yields | +0.03 | +0.04 | 61% | +0.07 | -17.5% | -0.24 | 0.29 | INCONCLUSIVE |
| gate_vix | -0.12 | -0.11 | 3% | -0.11 | -22.9% | +0.00 | 0.15 | REJECT |
| gate_dollar | -0.05 | -0.04 | 42% | -0.01 | -13.8% | -0.22 | 0.21 | REJECT |
| gate_gold_trend | -0.20 | -0.19 | 8% | -0.17 | -21.3% | -0.04 | 0.10 | REJECT |

Regime gates did not help. VIX, dollar and gold-trend gates were rejected; the real-yield gate was marginally better in development (+0.04) but worse on the holdout (−0.24), consistent with the post-2022 break in the gold/real-yield link. **Conclusion: no regime gate adopted.**
