# Aurum strategy report (2026-10-29)

Answer to the owner's brief *Develop and Optimise a Profitable Investment Strategy*. Every number below is a
**historical backtest** (simulation on past data, net of costs), not live or paper-trading performance. Sources of
each figure are the result folders named in the experiment files; nothing here was tuned on the results it reports.

## 1. Summary
- About 70 pre-registered variants were tested across three rounds (timing, always-invested sizing, and this brief's
  entries / stops / sizing / risk rules), on 2006–2026 data, on eight assets never used in design, and with two fill
  conventions.
- **One rule survives:** stay invested and size each asset by its forecast risk. Over 20 years it earned **the same
  return per unit of risk as simply holding** (Sharpe 0.37 vs 0.39) with **much smaller falls** (worst −39% vs −65%;
  in 2008 −11% vs −36%; in 2011–15 −38% vs −63%), but **less money** (5.5% vs 9.5% a year).
- **No timing, prediction, stop-loss, scaling or circuit-breaker rule improved it reliably.** The current settings
  sit in a flat, robust region; they were not picked as the best of a grid.
- **Recommendation:** keep the current strategy (15% volatility target, daily decisions, 5-point band), connect it
  to Alpaca **paper** trading with the new safety layer, and judge it by the pass/fail rules written in advance.
  Do not expect it to beat holding gold and miners; expect it to fall about half as much.

## 2. Comparison of strategies (core set: GLD, SLV, GDX, NEM, AEM, WPM; one account; 2006-06 → 2026-10)
| Strategy | Entry / exit | Sizing | Stop | CAGR | Sharpe | Max DD | Costs/yr | Sharpe pre-2013 / 2013–23 / 2024– | Other 8 assets: Sharpe / max DD | Main weakness |
|---|---|---|---|---|---|---|---|---|---|---|
| **Traded (recommended)** | Always invested | 15% / forecast vol, GVZ-adjusted | None | 5.5% | 0.37 | −39.1% | 0.20% | 0.15 / 0.24 / 1.30 | 0.26 / −38.5% | Earns less than holding; loses in gold bear markets |
| Buy & hold | Buy once | Equal amounts | None | 9.5% | 0.39 | −65.2% | 0.00% | 0.28 / 0.30 / 1.01 | 0.34 / −62.0% | Very deep falls |
| Equal weights, rebalanced | Always invested | Fixed equal | None | 10.5% | 0.42 | −66.1% | 0.04% | 0.29 / 0.34 / 1.07 | 0.36 / −70.0% | Deepest falls |
| Fixed 60% weights | Always invested | 60% of sleeve | None | 8.3% | 0.41 | −45.8% | 0.03% | 0.27 / 0.34 / 1.06 | 0.36 / −48.0% | Failed 2024–26 confirmation |
| Conservative (10% target) | Always invested | 10% / vol | None | 4.4% | 0.37 | −28.0% | 0.11% | 0.15 / 0.25 / 1.31 | 0.26 / −27.9% | Lower return |
| Aggressive (20% target) | Always invested | 20% / vol | None | 6.4% | 0.37 | −47.6% | 0.28% | 0.15 / 0.25 / 1.27 | 0.26 / −48.3% | Deeper falls |
| 15% drawdown breaker | Halve all at −15% from peak | As traded | Portfolio | 5.4% | 0.40 | −29.4% | 0.17% | 0.23 / 0.20 / 1.30 | 0.25 / −29.0% | Fragile (close fills: −0.18 in 2013–23) |
| 200-day trend exit | Out below 200-day avg. | As traded | Trend | 3.8% | 0.28 | −22.5% | 0.37% | 0.19 / −0.09 / 1.32 | 0.24 / −18.9% | Much less return |
| 15% trailing stop | Out 21 days after −15% | As traded | Trailing | 3.3% | 0.20 | −38.7% | 0.29% | 0.01 / 0.04 / 1.16 | 0.08 / −36.8% | Whipsaw, no protection gain |
| Fixed-fractional (0.5% risk) | 2-ATR trailing stop | Risk / stop distance | ATR | 4.0% | 0.26 | −27.7% | 0.67% | 0.14 / 0.03 / 1.21 | 0.28 / −34.4% | High costs, whipsaw |
| Add to winners | +25% in uptrends | As traded | None | 5.8% | 0.37 | −41.9% | 0.30% | 0.17 / 0.20 / 1.31 | 0.27 / −40.8% | No gain |
| Average down | +25% when −15% from high | As traded | None | 5.9% | 0.37 | −43.3% | 0.29% | 0.14 / 0.27 / 1.28 | 0.24 / −43.8% | Deeper worst fall |
| Portfolio vol target 12% | Always invested | Inverse vol + covariance | None | 5.4% | 0.35 | −39.5% | 0.10% | 0.17 / 0.22 / 1.31 | 0.25 / −41.4% | No gain, more complex |
| v0.2 timing (ML + technical) | BUY ≥ +0.20, SELL ≤ −0.20 | 15% / vol at entry | 2 ATR | 0.6% (2013–23) | −0.03 (2013–23) | −21.4% (2013–23) | 0.7% | – / −0.03 / 0.94 | – | Prediction had no skill (sleeve engine; ML needs 3 years of training, so no pre-2013 result) |

**Duplication:** every row is long the same thing, gold-linked assets. They differ only in *how much* they hold and
*when*, so none is a diversifier for another. Simple beat complex: the ML-driven strategy was the worst performer
after costs and was retired.

## 3. What the evidence says, by question in the brief
- **Investing all at once or gradually?** From 207 start dates, spreading over 12 months ended ahead 46% of the time;
  average 3-year result 14.6% vs 15.5% for investing at once; worst case slightly softer (−27% vs −30%). No edge
  either way (EXP-032). Investing at once is recommended for the paper account.
- **Scale into winners or losers?** Neither. Adding to winners did nothing; averaging down deepened the worst fall
  (EXP-032). No martingale or repeated averaging is allowed (position limit check).
- **Stop-losses?** Fixed-percentage, ATR, trailing, trend and portfolio stops were tested in four separate rounds; all
  gave up more return than they saved (EXP-005, 013, 023, 033). The strategy controls risk by holding less when
  volatility rises, not by stops. Stop-order mechanics (trigger, stop-market, stop-limit) are explained in EXP-033.
- **How much to invest?** Formula below. Signal-strength (AI confidence) sizing was rejected because the model's
  probabilities were not calibrated out of sample (EXP-004, EXP-015).
- **Regimes:** the strategy makes its money in gold bull markets (+22% a year) and loses in bear (−18%) and sideways
  (−5%) markets, about half as much as holding. It does best when gold's implied volatility is medium (EXP-036).
- **Parameters:** Sharpe stays between 0.36 and 0.40 for targets of 10–20% and bands of 0–10 points with 21-day
  volatility, so the result does not depend on a lucky setting (EXP-035). Costs up to about 25 bps are survivable.

## 4. Recommended strategy (exact rules)
1. **Universe:** GLD, SLV, GDX, NEM, AEM, WPM. Sleeve per asset `s = min(20%, 1/N)` of account equity (1/6).
2. **Forecast volatility** (after each close, completed bars only):
   `σ = stdev(21 daily returns) × √252 × clip(GVZ/100 ÷ GLD 21-day vol, 0.5, 2)`; plain 21-day vol if GVZ is stale.
3. **Target:** `w = min(1, 0.15 / σ)` of the sleeve; account weight `s × w`. Never above 1 (no borrowing).
4. **Trade** at the next open only if `|w − current| > 0.05` (of the sleeve), or when moving to or from zero; decided
   every trading day (D-027).
5. **Initial entry:** all at once (no evidence for spreading in). **No additions** beyond the target, **no stops**,
   **no take-profit**: the position shrinks automatically as volatility rises and grows as it falls.
6. **Do not trade** when data are stale, prices fail the sanity check, the off switch is on, or any safety check fails.

## 5. Risk framework
| Limit | Value | Where |
|---|---|---|
| Maximum per asset | its sleeve (1/6 of equity) | `strategy.max_position_pct`, position-limit check |
| Maximum total exposure | 100% (no leverage, no margin) | simulator and paper trader never borrow |
| Correlated group (four miners) | not capped: volatility sizing already keeps them low; a 40% cap never bound (EXP-034) | – |
| Orders | one per asset per day; at most 12 per day | `live.max_orders_per_day`, safety checks |
| Bad data | stale bars, GVZ older than 4 days, price > 25% from last close → no trade | `pipeline.decide`, `safety.py` |
| Emergency | off switch (`live.trading_enabled`, `STOP_TRADING` file) | `safety.py` |
| Loss limits / breakers | none: tested and rejected (EXP-033). Drawdowns of 30–40% are possible and were part of history | – |
| Expected ranges | 3 months: 5th–95th percentile −8.7% to +11.7% | [paper-trading-plan.md](paper-trading-plan.md) |

## 6. Implementation status
| Item | Status | Files |
|---|---|---|
| One-account backtest | Done (D-028) | `aurum/portfolio.py`, `run_plab.py` |
| Daily decisions | Done (D-027) | `config.yaml: strategy.rebalance` |
| Pre-trade checks, off switch, duplicate guard, decision records | Done | `aurum/safety.py`, `aurum/paper.py`, `config.yaml: live` |
| Monitoring (equity, drawdown, exposure, P&L, costs, decision records) | Done (paper tab) | `app.py` |
| Tests | 99 automatic tests, including the new safety checks | `tests/` |
| Alpaca paper connection (whole-share opening-auction orders, reconciliation, alerts, sizing without the ML step) | Next | to be built |
| Intraday research (EXP-029…031) | After Alpaca (needs minute data) | [topics/intraday.md](topics/intraday.md) |

## 7. Limitations
Backtests only; one asset family; the asset list was chosen in 2026 (survivorship); free data with adjusted prices;
the 2024–2026 holdout has been looked at several times; costs are assumptions; the longest time below a previous
peak was about 9 years (2011–2020). Nothing here guarantees future profit.

## Related documents
[Audit](audit-2026-10-29.md) · [Paper-trading plan and deployment checklist](paper-trading-plan.md) ·
[Continuous improvement](continuous-improvement.md) · [Experiment registry](experiments/README.md) ·
[Decisions](decisions.md)
