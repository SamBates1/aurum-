# EXP-013: Invested by default, protect when needed

| Field | |
|---|---|
| Status | Pre-registered 2026-10-29, before running |
| Origin | First real-data results (D-017): the baseline sits in cash about half the time and missed most of gold's rise; owner's goal of profit, not only protection |
| Current Aurum equivalent | Flat unless the score reaches +0.20 (BUY); exits at −0.20 (SELL) |

## Hypothesis
Most of the profit available in gold and miners comes from being invested while they rise. A strategy that is
**invested unless the score says SELL** (score ≤ −0.20), and uses stops only as protection, earns clearly more than
the baseline while keeping drawdowns well below buy & hold.

## Variants (fixed before running)
| Variant | Rule |
|---|---|
| `default_long` | Invested whenever score > −0.20; volatility-targeted size (15%); 2-ATR intrabar stop; re-enter 10 trading days after a stop if still not SELL |
| `default_long_full` | Same, but fully invested when in (no volatility targeting) |
| `default_long_full_nostop` | Fully invested unless SELL; no stop-loss |
| `default_long_full_chandelier` | Fully invested unless SELL; 3-ATR trailing stop; 10-day re-entry |
| `buy_hold`, `vol_sized_hold` | **Reference rows** (exp `REF`): shown for comparison, not counted as trials |

The 10-day re-entry wait is new: the existing rule (wait for the signal to leave BUY) would keep a
default-long strategy out for months after a stop.

## Acceptance criteria (stated before running)
Two questions, both net of costs at portfolio level:
1. **Standard rules vs the baseline** (registry README), applied automatically.
2. **Profit with protection vs buy & hold**, read from the "Profit check" table. A variant achieves the goal if, in
   development, its Sharpe is at least buy & hold's (ΔSharpe vs B&H ≥ 0) **and** its maximum drawdown is at least 25%
   smaller than buy & hold's, **and** on the holdout its ΔSharpe vs B&H ≥ −0.10 with a smaller drawdown.

A variant that earns more than the baseline but fails (2) is a better *baseline*, not a better *investment* than
simply holding; that would be recorded as such.

## Main risks
More time invested means more market risk; full-exposure variants will have larger drawdowns than the baseline.
The SELL threshold (−0.20) is reused from the baseline, not tuned.

## Results
_Not yet run._
