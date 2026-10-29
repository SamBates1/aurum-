# Strategy platform: final status report (2026-10-29, overnight build)

Answer to the *MASTER BUILD PROMPT: Aurum quantitative research & strategy platform* and the owner's Option 3 choice.
Every performance number is a **historical backtest** on real Yahoo Finance data (completed daily bars to
2026-10-29), net of costs, one account, next-open fills, T-bill interest on cash, no borrowing. Nothing here is paper
or live trading performance yet, and nothing in Aurum can place a real-money order.

Status words: **implemented and verified** (built, tested, and checked on real data or by a test that would fail if it
were wrong) · **implemented** (built and unit-tested, not yet exercised on real data or by a person) · **blocked**
(needs something only the owner can provide).

## 1. What was built
| Part | Status | Where |
|---|---|---|
| One strategy definition shared by backtest, designer, Fair Test and paper trader | **Implemented and verified**: the designer engine reproduces EXP-045's account values **exactly** (difference 0.0) for the 70/30, the risk cap and the trend-filter example, on real data (workflow commit 2444b6c) and in tests | `aurum/spec.py`, `aurum/engine.py`, `strategies/*.yaml` |
| Both 70/30 strategies loaded as templates (plus SPY buy-and-hold and the rejected trend filter as a worked example) | **Implemented and verified** | `strategies/` |
| Strategy Designer rule builder: assets and weights, schedule and no-trade band, sizing (fixed, risk cap, risk balance), rules from 14 indicators combined with AND / OR / at-least-k, trailing stop, account brake, costs, fills, benchmark, plain-English summary, save versions, YAML/JSON download | **Implemented** (page tested headless: load, edit, add rule and condition, save) | `pages/2_Strategy_Designer.py` |
| Linked decision charts: candles + rule lines, buy/sell triangles with amount ($ or £) and % of the account, one indicator panel per rule shaded where its condition was met, rule strips, decision text on hover, holdings vs targets, growth and drawdown vs SPY and 70/30; one time axis so zoom and hover work across every panel | **Implemented and verified** on real data (charts committed in `research/designer/2026-10-29-2321-real/`, screenshots checked) | `aurum/designer_charts.py` |
| Results box, period table (development by default; each look at the 2024+ holdout counted), explain-a-day, order list, CSV and HTML export, comparison view with the 2008, 2020 and 2022 downturns | **Implemented** | designer tabs 2–3 |
| Send for Fair Test with statuses (draft → testing → passed / failed / inconclusive → owner-only approved / shadow → paper trading → retired) | **Implemented and verified** on real data (three reports in `research/fairtests/`) | `aurum/fairtest.py`, `aurum/registry.py` |
| Luck and overfitting tracking: every version tried is counted (plus 100 earlier variants) in the deflated Sharpe ratio; "best of N by luck" warning; holdout-look counter; warning after 10 edits | **Implemented** | `aurum/registry.py` |
| Research lab: vary one number over a grid, scored on the development period only, every try counted, PBO when there are enough versions | **Implemented** | designer tab 5 |
| Scanner: today's readings for ten ETFs and whether each rule would be met | **Implemented** | designer tab 6 |
| Independent risk engine (can only cut risk): allowed assets, gross and per-asset caps, daily turnover cap, account drawdown halt, volatility-spike block, stale-data block, minimum order size; limits in `config.yaml` `risk:` | **Implemented and verified** by tests | `aurum/risk.py` |
| Paper-trading eligibility gates and owner approvals (per exact definition; editing a strategy voids its approval) | **Implemented and verified**: both Option 3 strategies pass every gate with the real Fair Test reports | `aurum/gates.py`, `research/approvals.yaml` |
| Paper trading of Option 3: 70/30 main and risk-capped shadow in separate ledgers; decisions after the close on completed bars, fills after the next open; blocked orders retried once a day; every decision and order logged with the strategy fingerprint | **Implemented** (verified by tests with fixed clocks and offline data; it has not yet run against live prices) | `aurum/spec_paper.py`, `run_bot.py`, `pages/3_Paper_Strategies.py` |
| Live view: prices refresh every minute, clearly labelled as delayed about 15 minutes (Yahoo); data labelled EOD / STALE / SYNTHETIC everywhere | **Implemented** | paper and designer pages |
| Strategy registry page (versions, status history, runs, Fair Test reports, approvals) | **Implemented** | `pages/4_Strategy_Registry.py` |
| Quant Desk integration: the desk now reads the saved strategies, their Fair Test verdicts, approvals and paper ledgers (numbers copied from saved files, never computed by the model) | **Implemented** | `aurum/desk.py` |
| Real-data runs on GitHub (`designer:` line in `research/experiments/RUN`) | **Implemented and verified** (workflow run on commit 124ae7f, success) | `run_designer.py`, `.github/workflows/experiments.yml` |
| Alpaca paper connection | **Blocked**: needs your Alpaca paper account, the keys stored only as GitHub Secrets, and your confirmation that paper keys are acceptable under "no storage of real brokerage credentials" | — |

## 2. Results on real data (2006-06-01 to 2026-10-29)
| Strategy | CAGR | Sharpe | Worst fall | 2008-09 | 2020 crash | 2022 |
|---|---|---|---|---|---|---|
| SPY buy and hold | 11.2% | 0.56 | −55.2% | −35.1% | −9.9% | −18.2% |
| **A: 70/30 SPY/GLD monthly (main)** | 11.1% | 0.68 | −38.5% | −20.3% | −4.3% | −15.4% |
| **B: 70/30 + 20% risk cap (shadow)** | 11.0% | 0.81 | −25.8% | −13.8% | −6.2% | −14.2% |
| Example: 70/30 + SPY trend filter (rejected) | 9.2% | 0.74 | −15.8% | +0.7% | −8.7% | −9.0% |

Source: `research/designer/2026-10-29-2321-real/summary.md`. These agree with EXP-045 (11.3% / 0.69 / −38.5% for
A; 11.0% / 0.81 / −25.8% for B). The small difference for A is the start date: EXP-045's tables start on 2006-06-30,
these on 2006-06-01; on identical dates the two engines give identical account values (section 1).

## 3. Fair Test verdicts (stricter than EXP-045, by design)
| Strategy | Benchmark | Verdict | Why |
|---|---|---|---|
| A: 70/30 | SPY | **INCONCLUSIVE** | Better over 20 years (Sharpe +0.12, 93% of resamples better, worst fall −38% vs −55%) and on the holdout and pre-2013, but in the 2013–2023 development period SPY did very well, so the gain there (+0.05) is below the +0.10 bar; DSR 0.40 < 0.50 once ~100 earlier variants are counted |
| B: risk cap | A (70/30) | **INCONCLUSIVE** | Smaller falls (development worst fall −18% vs −25%) for nearly the same return, but neither the return-per-risk bar (+0.06 < +0.10) nor the 20% drawdown-per-volatility bar (+15.5%) is met; DSR 0.48 |
| Trend filter example | A (70/30) | **FAILED** | Lower Sharpe than 70/30 in development and drawdown per unit of volatility not 20% better |

What this means: the Fair Test confirms neither strategy is a *proven improvement* under the strict rules, and none
of the integrity checks found a problem (no look-ahead, correct accounting, robust to fills, delay and ±20% changes).
You approved A as main on the evidence of EXP-045, and the gate records that explicitly ("approved on the evidence of
EXP-045") rather than pretending the Fair Test passed. B runs as a shadow, for evidence only.

## 4. Tests and CI
179 tests (46 new for the platform, 1 regression test for a bug found tonight), passing locally on Python 3.11 and 3.12;
ruff lint and format clean; GitHub CI passed on PR #2 and on `main`.

## 5. Bugs found and fixed tonight
| Bug | Fix |
|---|---|
| The main dashboard's paper tab crashed (KeyError 'ticker') once the new paper trader wrote decision records | Shows only the legacy bot's records; regression test |
| Blocked paper orders (e.g. off switch on) would have dropped the decision until the next month | Decision kept and retried once a day until a newer one replaces it; test |
| Synthetic (offline) Fair Test reports could have been saved into `research/fairtests/` | Offline reports go to `logs/`; test |
| The PBO figure was printed for 2–3 near-identical versions (97%, meaningless) | Only computed with 5+ versions and labelled information-only |
| Number inputs crashed when adding a rule (mixed int/float limits) | Fixed; covered by the page test |

## 6. Limitations
- Backtests only; the 2024+ holdout has been looked at many times, so only data after 2026-10-29 is genuinely new.
- Paper fills use the first price seen after the open (Yahoo, ~15 minutes delayed), not the official opening auction.
- Live intraday decisions are not supported: decisions use completed daily bars, exactly as tested (intraday ideas
  EXP-029…031 need minute data from Alpaca).
- The £ view converts the dollar account at each day's GBP/USD rate, so it includes currency moves.
- Rules can compare an indicator with a number or with another indicator **of the same asset** in the builder (the
  definition format allows cross-asset rules; the form does not offer them yet).
- Survivorship: the asset list was chosen in 2026.

## 7. How to use it
1. `python -m streamlit run app.py`, then **Strategy Designer** in the page list.
2. Paper trading: `python run_bot.py --paper` (leave it running; it decides after each US close and trades after the
   next open). Watch it on **Paper Strategies**. A brand-new account invests at its first decision.
3. Re-run everything on real data: add a `designer:` line to `research/experiments/RUN` and push.

## 8. Recommended next actions
1. Start the paper bot so the 70/30 and the shadow begin building a real track record (judged by
   `research/paper-trading-plan.md`).
2. Decide on Alpaca: create a paper account and confirm whether paper keys may be stored as GitHub Secrets.
3. Use the designer for new ideas, but expect the Fair Test to reject most: with ~100 variants already tried, a new
   rule needs a large, confirmed effect.
