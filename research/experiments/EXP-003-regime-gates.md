# EXP-003: Regime gates

| Field | |
|---|---|
| Status | Pre-registered 2026-10-27, awaiting a real-data run |
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

## Results
_Not yet run on real data._ After `python run_experiments.py`, copy the rows for this experiment from
`results/<date>-real/summary.md` here, with the verdict and any decision recorded in `../decisions.md`.
