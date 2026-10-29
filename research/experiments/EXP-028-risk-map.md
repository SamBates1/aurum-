# EXP-028: Risk map: return and worst fall at each risk level

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, before any lab result on real data |
| Origin | Owner's request: choose the risk level last, with full information |

## What it shows (descriptive, not a trial: no parameter is chosen by the code)
The traded strategy at volatility targets 10%, 15% (current), 20%, 25% and 30%, each asset capped at full investment
(no borrowing). For each: CAGR, Sharpe and max drawdown in every period, stress-window losses and calendar-year
returns, on the core set from 2006 and on the other set.

## How it is used
The owner chooses the risk level from this table, using the **worst** period (not the best) as the guide to what can
be lost. A higher target cannot exceed buy & hold's exposure, so above about 25% the strategy approaches buy & hold.

Lab rules (README, 'Research lab'); run with `python run_lab.py --set core` (and `--fill close`, `--set other`).

## Results
_Not yet run on real data._
