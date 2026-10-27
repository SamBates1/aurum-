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
