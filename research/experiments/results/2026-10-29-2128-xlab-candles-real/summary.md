# EXP-041: candlestick patterns (real)

18 patterns × 10 assets × 3 horizons = **492 tests** in the development period. Forward returns regressed on the pattern dummy plus 21-day momentum, 21-day volatility and distance from the 200-day average, with Newey-West standard errors.

- Tests with raw p < 5%: **21** (about 25 expected by chance alone).
- Discoveries at a 10% false-discovery rate (Benjamini-Hochberg): **0**.
- Discoveries that also held (same sign, p < 5%) before 2013 and after 2024: **0**.


## Trading the bullish patterns (portfolio level, net of costs) vs the no-signal baseline

| Variant | pre ΔSharpe (better) | dev ΔSharpe (better) | holdout ΔSharpe (better) | dev 2× cost | DSR | Verdict |
|---|---|---|---|---|---|---|
| no-signal vol-sized (baseline) | +0.00 (0%) | +0.00 (0%) | +0.00 (0%) | +0.00 | – | baseline |
| after breakout_20 (hold 5d) | -0.20 (23%) | -0.13 (28%) | -1.01 (0%) | -0.28 | 0.35 | REJECT |
| after bullish_engulfing (hold 5d) | -1.22 (0%) | -0.84 (0%) | -0.58 (19%) | -1.01 | 0.00 | REJECT |
| after bullish_pin_bar (hold 5d) | -0.02 (46%) | -0.50 (2%) | -0.78 (0%) | -0.71 | 0.06 | REJECT |
| after gap_up (hold 5d) | -0.28 (4%) | -0.15 (10%) | -0.27 (8%) | -0.28 | 0.33 | REJECT |
| after hammer (hold 5d) | -0.31 (18%) | -0.42 (8%) | -0.24 (32%) | -0.58 | 0.10 | REJECT |
| after morning_star (hold 5d) | -0.77 (4%) | -0.34 (14%) | -0.90 (5%) | -0.48 | 0.15 | REJECT |
| after wide_range_up (hold 5d) | -0.39 (23%) | -0.03 (45%) | -0.75 (8%) | -0.07 | 0.48 | INCONCLUSIVE |
| simple trend sma_50_200 (comparison) | -0.00 (49%) | -0.04 (40%) | -0.10 (27%) | -0.04 | – | reference |
| random entries #1 (control) | -0.66 (3%) | -0.19 (19%) | -0.27 (27%) | -0.42 | – | reference |
| random entries #2 (control) | -0.22 (20%) | -0.31 (6%) | -0.70 (4%) | -0.54 | – | reference |
| random entries #3 (control) | -0.25 (16%) | -0.14 (25%) | -1.66 (0%) | -0.37 | – | reference |

## Figures

- [Candlestick chart with indicators: GLD](figures/candles_GLD.png)
- [Candlestick chart with indicators: SPY](figures/candles_SPY.png)
- [Newey-West t-statistics of 5-day forward return after each pattern, with controls (dev)](figures/pattern_t_stats_dev.png)
- [Average 5-day effect after each pattern, controlling for momentum, volatility and trend (dev)](figures/pattern_effects.png)
- [Equity curves and drawdowns](figures/pattern_portfolios.png)
