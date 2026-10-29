# EXP-013: Invested by default, protect when needed

| Field | |
|---|---|
| Status | Run 2026-10-29: goal **not met**; nothing adopted |
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

## Results (real data, 2026-10-29 12:12 UTC; `results/2026-10-29-1212-real/`, open fills)

Portfolio of 6 sleeves, net of costs. Development 2013-10-18 → 2023-12-31; holdout from 2024-01-01.

| Variant | Dev CAGR | Dev Sharpe | Dev max DD | Holdout CAGR | Holdout max DD | Holdout ΔSharpe vs B&H | vs baseline |
|---|---|---|---|---|---|---|---|
| baseline | 0.8% | −0.02 | −21.4% | 20.9% | −17.2% | −0.14 | – |
| default_long | 1.9% | 0.12 | −22.3% | 20.9% | −19.0% | −0.17 | INCONCLUSIVE |
| default_long_full | 4.6% | 0.26 | −46.7% | 34.2% | −35.3% | −0.16 | INCONCLUSIVE (DSR 0.50) |
| default_long_full_nostop | 2.3% | 0.15 | −47.5% | 35.8% | −35.6% | −0.12 | INCONCLUSIVE |
| default_long_full_chandelier | 4.2% | 0.24 | −42.9% | 19.3% | −30.8% | −0.42 | INCONCLUSIVE |
| *buy_hold (reference)* | 6.0% | 0.30 | −43.0% | 44.2% | −38.0% | 0.00 | – |
| *vol_sized_hold (reference)* | 3.4% | 0.22 | −25.8% | 28.3% | −29.5% | −0.13 | – |

**Profit-with-protection test (criterion 2): failed by every variant.** Being invested more of the time does
raise returns well above the baseline (development CAGR 0.8% → 4.6%), but:
- fully invested variants had **the same or deeper drawdowns than buy & hold** (−43% to −48%): exiting on the
  SELL signal did not avoid the big falls, so the timing signal provides no protection;
- the variant that kept drawdowns low (`default_long`) did so through volatility-targeted sizing, and earned
  far less than holding.

Close fills (`2026-10-29-1212-real-closefill/`) give the same conclusion with slightly weaker numbers.

**What we learned:** over 2013–2026, buy & hold had the best risk-adjusted return of everything tested. The
protection Aurum provides comes from *how much* it holds, not *when* it holds (timing). *(Correction, 12:45: the
`vol_sized_hold` reference sizes once and never resizes, so its protection came mainly from partial cash holdings,
not from adjusting to volatility; see D-019 correction and EXP-014.)*
The simplest reference, always invested with volatility-targeted size (`vol_sized_hold`), beat the current
baseline on return and Sharpe in both periods, with drawdowns ~40% (development) and ~22% (holdout) smaller than
buy & hold. It is a reference row, not a pre-registered trial, so it is proposed as the candidate new baseline
for the next experiments (D-019), not adopted directly.
