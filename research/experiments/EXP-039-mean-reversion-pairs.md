# EXP-039: Mean reversion and pairs

| Field | |
|---|---|
| Status | Run 2026-10-29: mean reversion rejected; no pair is stably cointegrated |
| Origin | Master brief §6 |

## Rules
RSI(2) < 10 above the 200-day average, exit RSI(2) > 70; Bollinger z < −2, exit at 0; 60-day log-price z < −2, exit
at 0; buy after a 5-day fall worse than 2 standard deviations, hold 5 days. Same two questions and rules as EXP-038.

## Pairs (descriptive; long/short so not tradable in the current long-only, no-margin setup)
SLV/GLD, GDX/GLD, IWM/SPY, TLT/IEF: Engle–Granger cointegration on the full sample and on every 1-year window (share of
windows cointegrated at 5%), spread half-life, and a spread trade (rolling 1-year hedge ratio, 60-day z, enter at ±2,
exit at 0; 5 bps per leg; 0.5% a year short borrow). Correlated assets are **not** assumed to be a pair: the
cointegration stability statistic decides.

Cross-asset lab rules (README, 'Cross-asset lab'): universe SPY, QQQ, IWM, EFA, TLT, IEF, GLD, SLV, GDX, DBC (CPER excluded: data audit found paired ±30–50% bad prints in 2014–15); costs SPY/QQQ 2, IWM/EFA/TLT/IEF/GLD 3, SLV/GDX 5, DBC 8 bps one way; one account, next-open fills, T-bill on cash; periods pre (to 2013-10-17), dev (to 2023), holdout (2024+); figures in each result folder's `figures/`.

## Results (real data, 2026-10-29; `results/2026-10-29-2127-xlab-meanrev-real/` (summary.md, CSVs, figures/))
Portfolio verdicts (pre / dev / holdout ΔSharpe vs no-signal): RSI(2) −0.02 / −0.17 / −0.47 (INCONCLUSIVE); Bollinger
−0.46 / −0.12 / −0.49 (REJECT); 60-day z −0.66 / −0.18 / −0.35 (REJECT); 5-day extreme drop −0.24 / −0.19 / −0.24
(REJECT). Alone on each asset, the rules beat buy & hold in 20–30% of cells.

| Pair | Cointegrated (full sample, 5%) | Share of 1-year windows cointegrated | Half-life | Spread-trade Sharpe |
|---|---|---|---|---|
| SLV/GLD | no (ADF t −2.68) | 7% | 251 days | −0.05 |
| GDX/GLD | no (−2.21) | 14% | 369 days | −0.09 |
| IWM/SPY | no (−3.02) | 6% | 193 days | −0.28 |
| TLT/IEF | no (−1.42) | 9% | 611 days | −0.33 |

Highly correlated assets are not cointegrated here: their spreads wander for months or years, so the pairs trades lose
money. Rejected.
