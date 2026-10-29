# EXP-043: Macro and cross-asset lead-lag

| Field | |
|---|---|
| Status | Run 2026-10-29: nine development-period relationships, none confirmed in both other periods |
| Origin | Master brief §9 |

## Tests
For GLD, GDX, SLV and SPY: next-21-day return regressed on each driver today (dollar, real yield, breakeven, credit,
VIX, copper, yield curve, SPY's 21-day return), controlling for the asset's own past 21-day return, Newey–West (21
lags). Discoveries at 10% FDR in dev, confirmed only if the sign holds with p < 5% in pre and holdout. Contemporaneous
correlation is reported separately and is not treated as prediction. FRED series are latest revisions (not vintages):
market-based series are rarely revised, so this is noted rather than treated as look-ahead.

Cross-asset lab rules (README, 'Cross-asset lab'): universe SPY, QQQ, IWM, EFA, TLT, IEF, GLD, SLV, GDX, DBC (CPER excluded: data audit found paired ±30–50% bad prints in 2014–15); costs SPY/QQQ 2, IWM/EFA/TLT/IEF/GLD 3, SLV/GDX 5, DBC 8 bps one way; one account, next-open fills, T-bill on cash; periods pre (to 2013-10-17), dev (to 2023), holdout (2024+); figures in each result folder's `figures/`.

## Results (real data, 2026-10-29; `results/2026-10-29-2128-xlab-macro-real/` (summary.md, CSVs, figures/))
32 tests; 11 with raw p < 5% (1.6 expected by chance); 9 survive a 10% false-discovery rate in development; **none**
held (same sign, p < 5%) both before 2013 and after 2024. Closest: SPY after high VIX (t = 3.2 dev, 4.1 holdout, −0.1
before 2013), and silver after a rising dollar (negative in all three periods, t −0.9 / −2.4 / −0.9). Gold's
well-known contemporaneous links (dollar −0.49, real yields) are strong, but they describe the same day, not the future.
