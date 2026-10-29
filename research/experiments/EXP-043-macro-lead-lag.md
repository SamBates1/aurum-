# EXP-043: Macro and cross-asset lead-lag

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, before any real-data run |
| Origin | Master brief §9 |

## Tests
For GLD, GDX, SLV and SPY: next-21-day return regressed on each driver today (dollar, real yield, breakeven, credit,
VIX, copper, yield curve, SPY's 21-day return), controlling for the asset's own past 21-day return, Newey–West (21
lags). Discoveries at 10% FDR in dev, confirmed only if the sign holds with p < 5% in pre and holdout. Contemporaneous
correlation is reported separately and is not treated as prediction. FRED series are latest revisions (not vintages):
market-based series are rarely revised, so this is noted rather than treated as look-ahead.

Cross-asset lab rules (README, 'Cross-asset lab'): universe SPY, QQQ, IWM, EFA, TLT, IEF, GLD, SLV, GDX, DBC (CPER excluded: data audit found paired ±30–50% bad prints in 2014–15); costs SPY/QQQ 2, IWM/EFA/TLT/IEF/GLD 3, SLV/GDX 5, DBC 8 bps one way; one account, next-open fills, T-bill on cash; periods pre (to 2013-10-17), dev (to 2023), holdout (2024+); figures in each result folder's `figures/`.

## Results
_Not yet run on real data._
