# EXP-005: Position sizing and risk overlays

| Field | |
|---|---|
| Status | Pre-registered 2026-10-27, awaiting a real-data run |
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

## Results
_Not yet run on real data._ After `python run_experiments.py`, copy the rows for this experiment from
`results/<date>-real/summary.md` here, with the verdict and any decision recorded in `../decisions.md`.
