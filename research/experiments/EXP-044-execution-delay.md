# EXP-044: Execution delay and cost sensitivity of the adopted strategy

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, before any real-data run |
| Origin | Master brief §13.9 |

## Grid
Fills at the next open (as traded), the next close, and the open 1, 2 and 5 extra days late; costs ×0, 1, 2, 3, 5.
The adopted strategy is considered robust to execution if Sharpe stays within 0.05 of the as-traded value with one
extra day of delay and at 2× costs.

Cross-asset lab rules (README, 'Cross-asset lab'): universe SPY, QQQ, IWM, EFA, TLT, IEF, GLD, SLV, GDX, DBC (CPER excluded: data audit found paired ±30–50% bad prints in 2014–15); costs SPY/QQQ 2, IWM/EFA/TLT/IEF/GLD 3, SLV/GDX 5, DBC 8 bps one way; one account, next-open fills, T-bill on cash; periods pre (to 2013-10-17), dev (to 2023), holdout (2024+); figures in each result folder's `figures/`.

## Results
_Not yet run on real data._
