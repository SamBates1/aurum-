# QuantConnect LEAN

| | |
|---|---|
| Repository | https://github.com/QuantConnect/Lean |
| Version inspected | commit `22404ea` (2026-10-26), sparse checkout of `Common/`, `Algorithm/`, `Algorithm.Framework/`, `Engine/` |
| Licence | Apache-2.0: ideas and (with attribution/notice) code may be reused |
| Type | Event-driven C# engine (Python API); same engine for backtest and live, with swappable data feeds, brokerages and transaction handlers |
| Inspected by | Claude, 2026-10-27, by reading source |

## How it works (traced in source)

**One engine, swappable handlers.** Backtest and live differ only in the handlers plugged into the engine
(data feed, transaction handler, results handler, brokerage). The algorithm code is identical, which is the
strongest form of backtest/live parity among the systems reviewed.

**Fill models.** `Common/Orders/Fills/` (`FillModel.cs`, `EquityFillModel.cs`, `ImmediateFillModel.cs`,
`LatestPriceFillModel.cs`, `FutureFillModel.cs`). In `EquityFillModel.StopMarketFill` a sell stop is
triggered when the bar's low reaches the stop. If the bar opened at or below the stop (an unfavourable gap),
the fill is at the open minus slippage, with a message saying so; otherwise at the stop price minus slippage.
Buy stops mirror this with the high. The fill model also refuses to fill when the exchange is closed.
**Adopted in Aurum** (D-012): stops now fill intrabar with the same gap rule.

**Slippage and fees** are separate pluggable models attached to each security (`SlippageModel`,
`FeeModel`, brokerage models that set realistic defaults per broker). Aurum keeps one per-ticker cost
assumption plus sensitivity analysis; a separate spread/slippage split is possible later.

**Algorithm Framework.** `Algorithm.Framework/` separates five stages:
1. Universe selection,
2. Alpha models emitting *Insights* (direction, period, optional magnitude and confidence),
3. Portfolio construction (`EqualWeighting…`, `InsightWeighting…`, `ConfidenceWeighted…`,
   `RiskParity…`, `MeanVarianceOptimization…`, `BlackLitterman…`),
4. Risk management,
5. Execution.
An Insight with a *period* is close to the user's "trade plan" idea: a view with an expiry.

**Risk management models.** `Algorithm.Framework/Risk/`:
- `MaximumDrawdownPercentPortfolio.cs`: liquidates when portfolio drawdown exceeds a threshold, measured
  from the start or (with `isTrailing`) from the peak.
- `MaximumDrawdownPercentPerSecurity.cs`, `MaximumUnrealizedProfitPercentPerSecurity.cs`: per-holding stop
  and take-profit.
- `MaximumSectorExposureRiskManagementModel.cs`: exposure caps.
Tested in Aurum as EXP-005 (`dd_breaker`, per sleeve) and EXP-007 (take-profit).

**Testing.** LEAN maintains "regression algorithms" whose expected statistics are asserted, so any engine
change that alters results is caught. Aurum's analogue: `test_baseline_variant_is_the_traded_strategy` and the
hand-built accounting tests.

## Lessons for Aurum
| Idea | Status |
|---|---|
| Intrabar stop fills with gap handling | Adopted (D-012) |
| Same engine for backtest and live | Already in Aurum's design (strategy.py, D-005) |
| Portfolio drawdown / per-security risk models | Experiment EXP-005 |
| Insight = direction + period + confidence | Informs the trade-plan idea; EXP-007 provides the barriers |
| Risk-parity / mean-variance construction | Deferred: only 6 highly correlated assets; equal risk sleeves already approximate it |
| Adopting LEAN itself | Rejected for now: C#/.NET stack, heavy data setup; benefits don't justify the complexity for 6 daily-bar assets (D-013) |
