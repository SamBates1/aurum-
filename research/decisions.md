# Decision log

Every design decision, why it was made, and what would change it. Newest last.
Format: **ID — decision** (date) · context · reasons · revisit if.

**D-001 — Focus on gold, silver and gold miners** (2026-10-27)
Context: owner is a maths student applying for finance internships, with prior gold-investing experience.
Reasons: builds on existing knowledge; macro drivers (real yields, dollar, VIX) make a strong interview story;
mixes ETFs (ML + technicals) and miners (fundamentals too); free data from Yahoo and FRED.
Revisit if: the owner targets a different desk or sector (tickers live in `config.yaml`).

**D-002 — Python + Streamlit dashboard, paper trading before any real money** (2026-10-27)
Owner chose signals + paper trading, all four analysis types, web dashboard.

**D-003 — Run in GitHub Codespaces, personal GitHub account** (2026-10-27)
Claude's workspace has no market-data access; Codespaces needs no installs and has internet. Personal
(not university) account so the repository survives graduation and serves as a portfolio.

**D-004 — ML vote weighted by out-of-sample skill** (2026-10-27)
Context: first real-data run showed GLD with P(up) 79% while out-of-sample AUC was 0.50, and the ML vote
dominated the decision. Reason: a model with no proven skill must not drive trades. Weight 0 at AUC 0.50, full
at 0.56, measured point-in-time (D-009).

**D-005 — One strategy definition (`strategy.py`) for backtest, dashboard, bot and paper trading** (v0.2)
Context: audit found the backtest tested ML probabilities alone while live decisions used a composite.

**D-006 — Fills at the next open; per-ticker costs; T-bill on cash** (v0.2)
Same-close fills were optimistic; costs and cash interest were missing.

**D-007 — Signals from completed daily bars only** (v0.2)
Live decisions previously used today's partial bar, which the backtest never saw.

**D-008 — News sentiment and fundamentals: live context only, weight 0** (v0.2)
No free point-in-time history, so they cannot be backtested. Revisit if point-in-time data is obtained.

**D-009 — Point-in-time ML skill** (v0.2)
Using full-sample AUC to weight the model would be look-ahead. Only labels revealed by each date count.

**D-010 — FRED lagged two business days; untouched holdout from 2024-01-01** (v0.2)

**D-011 — Paper trading: no averaging in, stops never loosened, costs charged** (v0.2)
Audit found a top-up BUY could lower the stop.

**D-012 — Stops fill intrabar (stop price, or open after a gap)** (2026-10-27, v0.3)
Context: framework review: LEAN, Backtrader, VectorBT and Freqtrade all model stops this way; Aurum v0.2
checked the close and exited next morning, which also disagreed with its own paper trader (which reacts to
the live price). Reason: parity and realism, so adopted before testing; EXP-001 measures the effect.
Revisit if: EXP-001 shows the old convention passing the KEEP rules (would suggest stops are too tight).

**D-013 — Keep Aurum's own engine; don't adopt an external framework** (2026-10-27)
Reasons: the frameworks solve problems Aurum doesn't have (thousands of symbols, intraday data, many brokers);
heavy setup; Freqtrade and Backtrader are GPL, VectorBT has a Commons Clause; Aurum's engine is small, tested
and auditable. Revisit if: Aurum moves to live broker execution (LEAN is the strongest candidate).

**D-014 — Experiments are pre-registered; verdicts need DSR ≥ 0.5 and must hold on the holdout** (2026-10-27)
See `experiments/README.md`. Prevents the project drifting into data-mined complexity.

**D-015 — Trade-plan feature waits for EXP-007** (2026-10-27)
Owner's idea: tell me when to buy/sell, at what price, the stop, and how long to hold. Deferred at the
owner's request; EXP-007 (triple-barrier labels and exits) tests the stop/target/holding-period rules such a
plan would be built on.

**D-016 — Real-data runs happen on GitHub Actions** (2026-10-29)
Context: Claude's workspace cannot download market data, and Codespaces stops after 30 idle minutes, which most
likely cut short the first experiment run. Reasons: GitHub's runners have internet, cost nothing for a public repository,
and commit results back, so Claude can start a run (by pushing `research/experiments/RUN`) and read the
results without the owner typing commands. Revisit if: Yahoo Finance blocks GitHub's machines persistently.

**D-017 — After the first experiment run, no strategy change is adopted** (2026-10-29)
Context: 25 pre-registered variants vs the baseline on real data (`experiments/results/2026-10-29-real/`).
None met all acceptance rules; PBO across variants was 77%, i.e. the best-looking variant in one half of the
history is usually below median in the other half. Reasons: adopting the best-looking variant now would be
exactly the selection bias the rules exist to prevent. Kept: intrabar stops (D-012, confirmed by EXP-001).
Candidate: chandelier trailing stop (EXP-005) passed every rule except the deflated Sharpe (0.39 < 0.50).
Revisit if: the chandelier stop is confirmed on data not used here (EXP-009).

**D-018 — Keep next-open fills as default; check headline results with close fills** (2026-10-29)
EXP-010: rerunning the whole registry with next-close fills changed the baseline's development Sharpe by only
0.06 and changed no conclusion. Open fills were mildly flattering. Every future headline result is also run
with `--fill close` before being trusted.

**D-019 — Invested-by-default timing not adopted; volatility-sized holding becomes the candidate baseline** (2026-10-29)
EXP-013: being invested more raised returns but, when fully invested, drawdowns matched buy & hold, so the
signal's exits do not protect capital. Buy & hold had the best Sharpe of everything tested (0.30 development).
The protection comes from volatility-targeted sizing. Proposal: make "always invested, volatility-targeted"
(`vol_sized_hold`: development Sharpe 0.22, max DD −25.8%; holdout CAGR 28.3%) the baseline that every new
prediction idea must beat, so ideas are judged on whether they add anything to simply holding with sensible
sizing. To be confirmed by the owner before changing the traded strategy.

**D-019 correction** (2026-10-29, 12:45)
The `vol_sized_hold` reference used in D-019 sized each position once, at its first entry, and never resized it.
Its lower drawdowns therefore came mostly from holding part of each sleeve in cash, not from adjusting to
volatility over time. The baseline switch is **not** made on that evidence. Instead a properly rebalancing version
(`vol_hold`, EXP-014) is pre-registered with explicit adoption criteria and tested before any change.

**D-020 — Switch the traded strategy to "always invested, sized by volatility" (vol_hold)** (2026-10-29)
EXP-014 met every pre-registered adoption criterion in both periods with both fill conventions: versus the
v0.2 timing strategy, development CAGR 2.0% vs 0.8% and Sharpe 0.12 vs −0.02; holdout CAGR 24.6% vs 20.8% and
Sharpe above buy & hold's; max drawdowns 35% (development) and 64% (holdout) smaller than buy & hold.
`config.yaml: strategy.mode = vol_hold`. The ML score and reasons remain on the dashboard as context only.
The timing strategy is kept as `timing_v02` for comparison. The owner asked for the switch; it was made only
after the properly rebalancing version passed.

**D-021 — Size positions with gold implied volatility (GVZ)** (2026-10-29)
EXP-017's `vol_hold_gvz` passed all acceptance rules with both fills (DSR 0.66 / 0.63, PBO across the run 18% / 9%)
and reduced development drawdown from −27.8% to −20.8%. `strategy.vol_estimator = gvz`: 21-day volatility × (GVZ /
GLD 21-day volatility), clipped 0.5–2. If GVZ cannot be loaded or is stale, sizing falls back to plain 21-day
volatility with a visible warning. Revisit if: GVZ data becomes unreliable, or paper trading shows realised risk
far from target.

**D-022 — Place orders once a week, after Friday's close** (2026-10-29)
EXP-022: deciding orders every 5th trading day instead of daily kept the Sharpe ratio (pre-2013 +0.02, development
+0.02; other assets +0.04 / +0.01) with half the orders (20 instead of 39 per asset per year), meeting the rule fixed in
advance. Implemented as the last trading day of each week (`strategy.rebalance: weekly`); confirmed with that exact
rule as the baseline (Sharpe vs daily −0.03 / +0.01 / −0.02 open fills, +0.02 / +0.02 / +0.02 close fills). The dashboard
still shows the target every day; the bot and paper trader only act on rebalance days. Revisit if: paper trading shows
weekly drift from target causing materially larger losses than the backtest.

**D-023 — The Alpaca connection may trade whole shares at the opening auction** (2026-10-29)
EXP-022: whole-share positions changed Sharpe by at most ±0.03 for $10k and $100k accounts. Alpaca accepts fractional
quantities only as day orders [S25]; whole shares allow opening-auction (OPG) orders, the closest match to the
backtest's next-open fills.

**D-024 — Review of D-021 (GVZ sizing): kept, with a recorded weakness** (2026-10-29)
EXP-020's pre-registered check failed: in 2008-06 → 2013-10 (data no earlier test used) GVZ sizing did worse than plain
21-day sizing (ΔSharpe −0.09 open fills, −0.11 close fills). Against that: development +0.11, holdout +0.08, whole
2006–2026 period 0.38 vs 0.35, and on eight new assets 0.26 vs 0.19 over 2010–2026 (EXP-021). Kept because it was better
in 2 of 3 periods and on both asset sets over the full history; recorded as not robust across every period.
Revisit if: paper trading or a future period shows GVZ sizing behind plain sizing for a year or more.

**D-025 — Stages 5–7 add nothing; the traded strategy stays as is** (2026-10-29)
Gold fair value (EXP-024), CFTC positioning (EXP-025), and news-based risk indices (EXP-026) were all INCONCLUSIVE or
REJECTED; the chandelier stop was rejected and the miner tilt again fell short (EXP-023). Stage 8 (EXP-027) was therefore
not run, per its pre-registered rule. Candidates to watch in paper trading, not traded: miner-vs-GDX tilt (dev +0.08,
better in 100% of resamples, but not before 2013 or on other miners) and the EPU tilt (+0.02 to +0.06 in every period).
GDELT-based news scoring was rejected as infeasible to backtest point-in-time without paid data.

**D-026 — The risk level is the owner's choice; it does not change return per unit of risk** (2026-10-29)
EXP-028: over 2006–2026, volatility targets from 10% to 30% all have Sharpe 0.36–0.38 (buy & hold 0.39). Higher targets
earn more and fall further (15%: 5.7% a year, worst fall −39.7%; 25%: 7.2%, −54.2%). `target_vol` stays 0.15 until
the owner chooses.

**D-027 — Back to daily decisions, at the owner's request** (2026-10-29)
The owner prefers the bot to be able to act on any day. EXP-022 found daily and Friday-only decisions equivalent
(Sharpe differences within ±0.03 either way); daily reacts sooner after a sudden fall, at about twice the orders
(39 vs 21 per asset per year, roughly 0.1% a year more in costs). `strategy.rebalance: daily`. An order is still only
placed when an asset is more than 5 points (of its sleeve) away from target. Weekly stays available as a setting.

**D-028 — The one-account simulator is the standard backtest** (2026-10-29)
Audit finding: the backtest kept each asset in its own pot of money, while the paper trader sizes every asset against
the whole account. `aurum/portfolio.py` simulates one account exactly like the paper trader (and a broker). EXP-035:
the difference is small (≤ 0.04 Sharpe in every core period), so earlier conclusions stand; new work uses the
one-account engine.

**D-029 — Owner's strategy brief (EXP-032…036): no rule change adopted** (2026-10-29)
Twenty pre-registered variants on entries and scaling, stops and exits, circuit breakers and sizing, tested from 2006,
on eight other assets and with both fill conventions: none met the rules. Recorded findings: investing at once vs
spreading in is close to a coin-flip (lump sum ahead 54% of the time); averaging down deepens the worst fall; every stop
and exit gives up more return than it saves; fixed weights beat volatility sizing on Sharpe before 2024 but failed in
2024–2026, so volatility sizing is kept for what it does reliably, smaller falls, not for higher return per unit of
risk. The current settings sit in a flat region of the parameter grid. Near-misses to watch, not traded: 15% drawdown
breaker (fragile under close fills), fixed weights.

**D-030 — Master brief, cross-asset lab (EXP-037…044): the adopted strategy stays unchanged** (2026-10-29)
Eight pre-registered experiments on ten assets from 2006: no trend, momentum, mean-reversion, pairs, candlestick, ML
or macro signal met the rules; better volatility forecasts and covariance-based risk parity were inconclusive; the
adopted strategy is robust to one to five days' execution delay and to 2× costs. Nothing beat the S&P 500's return in
every period without a deeper worst fall, with or without leverage (EXP-037).

**D-031 — Data-audit actions** (2026-10-29)
CPER (copper ETF) excluded: paired ±30–50% bad prints in 2014–15 and 8.8% zero-volume days. FRED's high-yield spread
(BAMLH0A0HYM2) now returns only 3 years of history, so credit is measured with HYG / IEF. Futures OHLC from Yahoo
(GC=F, SI=F, HG=F) has many open/close values outside the day's range, so only futures closes are used (as before).
The price cache now refetches if the cached history starts later than requested; every result records code and data
fingerprints.

**D-032 — GVZ sizing (D-021, D-024) gains independent support** (2026-10-29)
EXP-040: GVZ-adjusted volatility was the most accurate forecast of the next 21 days' variance (QLIKE 0.209 vs 0.339
for plain 21-day) and the best-calibrated 99% VaR (0.89% breaches vs 2.32%) for gold assets. Kept.

**Owner decision pending — S&P 500 + gold** (2026-10-29)
EXP-037 found that 70% SPY + 30% GLD, rebalanced monthly, matched the S&P 500's return (11.3% a year) with a higher
Sharpe (0.69 vs 0.56) and a shallower worst fall (−38% vs −55%) over 2006–2026. It is a simple allocation, not a trading
signal, and lies outside Aurum's precious-metals mandate; adopting it is the owner's choice and is not implemented.

**D-033 — Owner's goal: profit close to the S&P 500 with protection in downturns; S&P + gold confirmed** (2026-10-29)
The owner chose both goals. EXP-045 confirmed that a 70/30 SPY/GLD mix (monthly) keeps the S&P 500's return (11.3% a
year, 2006–2026) with a Sharpe of 0.69 vs 0.56 and a worst fall of −38% vs −55%, robust to the mix (80/20–60/40),
rebalancing frequency and fill convention. Downturn overlays failed the strict pre-registered test; the 20%-volatility
risk cap was a near miss (Sharpe 0.81, worst fall −26%, but a larger loss in the fast 2020 crash). Not yet implemented
as the traded strategy: the owner is asked which allocation to paper-trade. (Resolved by D-034.)

**D-034 — Owner chose Option 3: paper-trade 70/30 SPY/GLD (main) with the risk-capped version as a shadow** (2026-10-29)
The owner's instruction ("Do option 3 for now") is implemented as two strategy definitions shared by the backtest, the
Strategy Designer and the paper trader: `strategies/spy-gld-70-30-monthly.yaml` (main: 70% SPY / 30% GLD, rebalanced on
the first trading day of each month) and `strategies/spy-gld-70-30-risk-cap.yaml` (shadow: each asset × min(1, 20% /
21-day volatility), checked daily, 5-point band). Both reproduce EXP-045's account values exactly (difference 0). They
run in separate paper ledgers (`paper.engine: spec`); the gold vol_hold bot remains available as `paper.engine:
legacy`. The owner's approvals are recorded per exact definition (spec hash) in `research/approvals.yaml`: main on the
evidence of EXP-045, shadow for evidence only (it narrowly failed EXP-045's downturn test). Editing either strategy
changes its hash and needs a new approval. Paper trading only; no real-money connection exists.

**D-035 — Strategy Designer, Fair Test, registry, risk engine and gates (master build prompt)** (2026-10-29)
New strategies are built from parts (assets, indicators, AND/OR/k-of-n rules, sizing, exits) and judged by the Fair
Test, which applies the same pre-registered rules as the labs (signal or risk path, 2× costs, DSR, holdout AND
pre-2013) plus look-ahead, accounting, execution-delay and ±20% sensitivity checks. The DSR counts every version tried
in the registry plus 100 earlier portfolio variants, so a new "winner" needs a large effect. The designer shows the
development period by default; each look at the 2024+ holdout is counted. An independent risk engine (config `risk:`)
can only cut risk. A Fair Test pass is evidence, not permission: paper trading needs every gate and the owner's
approval.
