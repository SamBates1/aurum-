# EXP-041: Candlestick patterns

| Field | |
|---|---|
| Status | Run 2026-10-29: no candlestick pattern has predictive value |
| Origin | Master brief §10 |

## Patterns (defined in `aurum/xlab.py::candle_patterns`, OHLC only)
Doji, hammer, hanging man, shooting star, bullish/bearish engulfing, inside bar, outside bar, bullish/bearish pin bar,
morning/evening star, gap up/down, wide-range up/down day (range > 2 ATR), 20-day breakout, failed breakout.

## Tests
Event study on every asset and horizon (1, 5, 10 days): forward return regressed on the pattern dummy plus 21-day
momentum, 21-day volatility and distance from the 200-day average, Newey–West standard errors. Discovery in the
development period at a 10% false-discovery rate (Benjamini–Hochberg) over **all** tests; a discovery counts only if
it also has the same sign and p < 5% before 2013 and after 2024. Trading test: hold the asset for 5 days after each
bullish pattern (vol-sized), vs the no-signal baseline, with three random-entry controls and a simple trend rule.

Cross-asset lab rules (README, 'Cross-asset lab'): universe SPY, QQQ, IWM, EFA, TLT, IEF, GLD, SLV, GDX, DBC (CPER excluded: data audit found paired ±30–50% bad prints in 2014–15); costs SPY/QQQ 2, IWM/EFA/TLT/IEF/GLD 3, SLV/GDX 5, DBC 8 bps one way; one account, next-open fills, T-bill on cash; periods pre (to 2013-10-17), dev (to 2023), holdout (2024+); figures in each result folder's `figures/`.

## Results (real data, 2026-10-29; `results/2026-10-29-2128-xlab-candles-real/` (summary.md, CSVs, figures/))
492 tests in the development period (18 patterns × 10 assets × 3 horizons, with momentum, volatility and trend controls
and Newey–West errors): 21 had raw p < 5%, fewer than the ~25 expected by pure chance; **0 discoveries** at a 10% false-
discovery rate; 0 confirmed. Trading every bullish pattern (hold 5 days) lost to simply holding in every case (ΔSharpe
in dev −0.03 to −0.84) and did no better than random entries. Rejected.
