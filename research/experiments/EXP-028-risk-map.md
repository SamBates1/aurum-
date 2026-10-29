# EXP-028: Risk map: return and worst fall at each risk level

| Field | |
|---|---|
| Status | Run 2026-10-29: risk map produced; owner to choose |
| Origin | Owner's request: choose the risk level last, with full information |

## What it shows (descriptive, not a trial: no parameter is chosen by the code)
The traded strategy at volatility targets 10%, 15% (current), 20%, 25% and 30%, each asset capped at full investment
(no borrowing). For each: CAGR, Sharpe and max drawdown in every period, stress-window losses and calendar-year
returns, on the core set from 2006 and on the other set.

## How it is used
The owner chooses the risk level from this table, using the **worst** period (not the best) as the guide to what can
be lost. A higher target cannot exceed buy & hold's exposure, so above about 25% the strategy approaches buy & hold.

Lab rules (README, 'Research lab'); run with `python run_lab.py --set core` (and `--fill close`, `--set other`).

## Results (real data, core set 2006–2026, open fills; `results/2026-10-29-1337-lab-core-real/`, `…-1337-lab-core-real-closefill/`, `…-1332-lab-other-real/`)
| Volatility target | CAGR 2006–2026 | Sharpe | Worst fall (whole period) | 2008 crisis | 2011–15 bear market | 2024–2026 CAGR |
|---|---|---|---|---|---|---|
| 10% | 4.5% | 0.38 | −28.6% | −7.5% | −27.5% | 17.0% |
| **15% (current)** | **5.7%** | **0.38** | **−39.7%** | **−11.0%** | **−38.5%** | **23.5%** |
| 20% | 6.5% | 0.38 | −48.0% | −16.5% | −46.4% | 28.1% |
| 25% | 7.2% | 0.38 | −54.2% | −19.8% | −52.6% | 32.3% |
| 30% | 7.3% | 0.36 | −59.3% | −24.3% | −57.7% | 34.8% |
| buy & hold | 9.5% | 0.39 | −65.2% | −35.7% | −62.8% | 39.0% |

**Key finding:** return per unit of risk is the same at every level (Sharpe 0.36–0.38, and buy & hold 0.39). The
risk level does not make the strategy better or worse; it chooses how much of gold's ride to take: roughly, each
extra 1% a year of long-run return costs about 8–10 points of extra worst-case fall. Above 25% little extra return is
gained because positions hit the full-investment cap. The other assets show the same pattern.
