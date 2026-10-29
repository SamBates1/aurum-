# EXP-038: Trend following and momentum across ten assets

| Field | |
|---|---|
| Status | Run 2026-10-29: no trend or momentum rule adopted |
| Origin | Master brief §5; Moskowitz–Ooi–Pedersen (2012); Faber (2007) |

## Rules (all windows reported; none selected after seeing results)
SMA crosses 50/200 and 20/100; EMA cross 20/100; price above its 50-, 100- and 200-day average; time-series momentum
over 63, 126 and 252 days; Donchian breakout 50/20; multi-timeframe confirmation (1-, 3- and 12-month returns all
positive); cross-sectional momentum (hold the top 3 of 10 by 126-day return, or 252-day return skipping the last month,
monthly). Long/flat only.

## Two questions
1. **Each rule alone on each asset** (no sizing): share of (asset, period) cells in which it beats buy & hold's Sharpe.
2. **Portfolio**: equal sleeves sized by Aurum's volatility rule, multiplied by the 0/1 signal, vs the same portfolio
   with no signal (the brief's "no-predictive-signal volatility-managed" baseline). Lab rules decide (signal or risk path
   in dev, 2× costs, DSR, then holdout **and** pre). PBO across all variants reported.

Cross-asset lab rules (README, 'Cross-asset lab'): universe SPY, QQQ, IWM, EFA, TLT, IEF, GLD, SLV, GDX, DBC (CPER excluded: data audit found paired ±30–50% bad prints in 2014–15); costs SPY/QQQ 2, IWM/EFA/TLT/IEF/GLD 3, SLV/GDX 5, DBC 8 bps one way; one account, next-open fills, T-bill on cash; periods pre (to 2013-10-17), dev (to 2023), holdout (2024+); figures in each result folder's `figures/`.

## Results (real data, 2026-10-29; `results/2026-10-29-2126-xlab-trend-real/` (summary.md, CSVs, figures/))
Portfolio verdicts against the same volatility-sized portfolio with no signal (pre / dev / holdout ΔSharpe):
SMA 50/200 0.00 / −0.04 / −0.10 (REJECT); SMA 20/100 −0.01 / −0.14 / −0.07 (REJECT); EMA 20/100 −0.00 / −0.07 /
−0.01; above SMA50/100/200 all negative in dev; 63/126/252-day momentum +0.05/+0.10/+0.11 before 2013 but negative
after 2024 (126 and 252: REJECT, failed on holdout); Donchian 50/20 REJECT (failed on holdout); multi-timeframe REJECT;
cross-sectional momentum (126 days, top 3) −0.03 / +0.02 / −0.01 and (252−21) +0.15 / −0.10 / +0.14: INCONCLUSIVE.
PBO across the 13 variants is in the summary.

**Each rule alone on each asset** (long/flat, no sizing): no rule beat buy & hold's Sharpe in more than 43% of (asset,
period) cells. Trend rules roughly **halve drawdowns** (e.g. SMA 50/200 worst fall −7.8% vs −13.7% before 2013) by
being out of the market half the time, but give up as much return: risk reduction, not added return per unit of
risk. This matches EXP-002 (gold timing) on a much wider universe.
