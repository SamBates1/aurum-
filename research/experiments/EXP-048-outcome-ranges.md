# EXP-048: What range of outcomes should the owner expect?

| Field | |
|---|---|
| Status | Pre-registered 2026-10-30 10:55 UK, descriptive (no pass/fail) |
| Origin | Owner deciding whether, and how much, to invest (D-036) |

## Method (fixed before running)
- Monthly 70/30 and S&P-only returns in pounds, net of the EXP-046 fees, 1972-2026 (from EXP-047).
- 10,000 simulated futures by stationary block bootstrap (mean block 12 months, seed 42), which keeps runs of good and
  bad years together.
- Two plans: £1,000 once; £1,000 now plus £100 a month. Horizons 1, 3, 5 and 10 years.
- Reported: the 5th, 25th, 50th, 75th and 95th percentile of the final value; the chance of ending below the money paid
  in; the chance of a fall of 20% or more at some point; the median worst fall along the way. Nominal pounds (before
  inflation).
- Caveat: this assumes the future looks like a reshuffled 1972-2026. It cannot include events that never happened in
  that period.

## Amendment (2026-10-30 11:10 UK, before EXP-048 was run)
While checking EXP-047's data, the monthly-average prices turned out to understate volatility a lot (2006-2026: 12.9%
a year for the S&P from monthly averages vs 19.3% from daily data). Simulating the owner's outcomes from them would
make the range of outcomes look far too narrow. So the **main** simulation now uses true month-end returns in pounds
from EXP-046's daily data (2006-2026, net of the same fees); the 1972-2026 monthly series is shown as a second view,
with its monthly returns scaled to the volatility measured on daily data over 2006-2026 (stated as an approximation).
Everything else is unchanged.

## Results (real data; `results/2026-10-30-1134-uk-real/`)
**£1,000 now + £100 a month, 70/30, in pounds after fees** (paid in: £2,100 after 1 year, £6,900 after 5, £12,900 after 10):

| | 1 year | 5 years | 10 years |
|---|---|---|---|
| Optimistic view (2006-2026 repeated): bad 1-in-20 / typical | £2,085 / £2,286 | £8,221 / £9,896 | £20,131 / £26,232 |
| Cautious view (1972-2026): bad 1-in-20 / typical | £1,867 / £2,283 | £6,744 / £9,681 | £14,772 / £25,018 |
| Cautious view: chance of ending below what you paid in | 21% | 6% | 2% |

The two views agree on the typical outcome; they differ on the bad outcomes. The cautious view is the better guide:
2006-2026 was unusually good for a UK holder of gold. Neither view can include a crisis worse than 1972-2026's.
