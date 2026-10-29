# EXP-005: Position sizing and risk overlays

| Field | |
|---|---|
| Status | Run 2026-10-29 on real data: see Results |
| Origin | Kaminski & Lo [S14]; Harvey et al. (2018) [S7]; Moreira & Muir (2017) [S6]; Freqtrade Protections; LEAN risk models. |
| Current Aurum equivalent | Aurum uses a fixed 2-ATR stop, 15% vol target and sleeve caps; none of these were tested against alternatives. |

## Hypothesis
Some overlay (trailing stop, breaker, different vol target) reduces volatility-adjusted drawdown without lowering Sharpe; and the 2-ATR stop itself should beat no stop if gold trends (Kaminski–Lo).

## Variants (fixed before running)
`no_stop`; `chandelier_3atr` (trail: highest close since entry - 3 ATR, plus the initial 2-ATR stop); `dd_breaker` (exit and pause 21 days if the sleeve is 15% below its peak); `stop_guard` (pause 30 days after 2 stop-outs within 60 days); `no_vol_target` (full exposure); `target_vol_10`; `target_vol_20`.

## Acceptance criteria
Risk-control path for overlays; signal path for `no_stop` and the vol-target variants. See [README](README.md#acceptance-criteria-applied-automatically-by-run_experimentspyverdict).

## Main risks and limitations
Breakers are per sleeve, not portfolio-wide (a portfolio breaker needs joint simulation; see topics/sizing-and-risk.md).

## Results (real data, first run 2026-10-29 11:34 UTC; files at commit `c3d1f65`, `results/2026-10-29-real/`)
Portfolio of 6 sleeves, net of costs, vs the baseline over identical dates. Development 2013-10-18 → 2023-12-31;
holdout from 2024-01-01. 26 variants tried in total; PBO across them 77%. (The same folder name was
reused by the 12:12 run, which added EXP-013 and overwrote these files; they remain in git history.)

| Variant | Dev Sharpe | Dev ΔSharpe | better | ΔSharpe 2× cost | Dev max DD | Holdout ΔSharpe | DSR | Verdict |
|---|---|---|---|---|---|---|---|---|
| no_stop | -0.01 | -0.00 | 46% | +0.01 | -23.5% | +0.00 | 0.25 | REJECT |
| chandelier_3atr | +0.11 | +0.12 | 94% | +0.11 | -17.6% | +0.26 | 0.39 | INCONCLUSIVE |
| dd_breaker | -0.03 | -0.02 | 20% | -0.02 | -21.3% | -0.06 | 0.23 | REJECT |
| stop_guard | -0.04 | -0.03 | 22% | -0.03 | -22.1% | -0.03 | 0.22 | REJECT |
| no_vol_target | +0.19 | +0.20 | 95% | +0.20 | -41.5% | -0.09 | 0.48 | INCONCLUSIVE |
| target_vol_10 | -0.01 | -0.00 | 47% | +0.00 | -14.6% | -0.03 | 0.25 | REJECT |
| target_vol_20 | +0.01 | +0.02 | 92% | +0.02 | -27.7% | +0.00 | 0.27 | INCONCLUSIVE |

The **chandelier trailing stop** was the strongest result of the whole study: +0.12 Sharpe in development, better in 94% of resamples, still better at 2× costs, and +0.26 on the holdout. It fails only the deflated-Sharpe test (0.39 < 0.50): with 26 variants tried, an improvement this size could still be luck. Removing vol targeting raised Sharpe (+0.20) but nearly doubled the worst drawdown (−41.5% vs −21.4%) and was worse on the holdout. Breakers, stop guard and no-stop were rejected. **Conclusion: nothing adopted yet; the chandelier stop is the top candidate for a single confirmatory test (EXP-009).**
