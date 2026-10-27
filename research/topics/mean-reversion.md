# Mean reversion

Status: reviewed 2026-10-27; experiments EXP-006.

## Ideas
- **Bollinger / z-score dips in an uptrend**: buy closes more than 2 standard deviations below the 20-day
  mean while price is above its 200-day average; exit back at the mean.
- **Relative value: miner vs GDX**: buy a miner when the log price ratio to GDX is 2 standard deviations below
  its 60-day mean; exit when it returns to the mean.
- **Cointegration pairs (e.g. GDX vs GLD, long one / short the other)**.

## Why mean reversion can fail
- Time-series momentum (1–12 months) is the dominant documented effect in commodities [S1][S2]; buying dips
  fights it during strong downtrends, which is why the dip rule is restricted to uptrends.
- Relative-value gaps between a miner and its index can be *information* (a guidance cut, a mine accident)
  rather than noise, so the spread may never close. The test must look at the loss tail, not just the average.
- Cointegration relationships between gold and miners drift as hedging, costs and leverage change
  (Tufano 1998 shows exposures vary over time) [S5].

## Decisions
- Bollinger and miner-vs-GDX reversion: **Experiment** (EXP-006), long-only, same costs and accounting.
- Cointegration pairs trading: **Rejected for now**: needs short selling (Aurum is long-only by design), and
  the relationship is unstable; revisit only if the long-only relative-value test shows value.
