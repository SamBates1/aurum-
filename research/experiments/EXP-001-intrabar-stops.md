# EXP-001: Intrabar stop fills

| Field | |
|---|---|
| Status | Pre-registered 2026-10-27, awaiting a real-data run |
| Origin | Framework review: LEAN `EquityFillModel.StopMarketFill`, Backtrader `bbroker._try_exec_stop`, VectorBT `get_stop_price_nb`, Freqtrade `_get_close_rate_for_stoploss` all fill a stop at the stop price when the bar trades through it and at the open after a gap. |
| Current Aurum equivalent | Aurum v0.2 checked stops on the close and exited the next open. That (a) is not how a resting stop order behaves, and (b) disagreed with Aurum's own paper trader, which exits when the live price touches the stop. |

## Hypothesis
Intrabar stop fills change measured returns and drawdowns materially for gap-prone miners. Because intrabar fills are what a live stop order does, the switch was adopted for parity before testing (D-012); this experiment measures the size of the change and checks the old convention wasn't hiding a better rule.

## Variants (fixed before running)
`baseline` (intrabar, new default) vs `stop_on_close` (v0.2 behaviour).

## Acceptance criteria
Not a keep/reject decision on realism grounds: the intrabar rule stays unless `stop_on_close` passes the KEEP rules, in which case investigate *why* before changing anything (it would suggest stops placed too tight). See [README](README.md#acceptance-criteria-applied-automatically-by-run_experimentspyverdict).

## Main risks and limitations
Intrabar fills are pessimistic when both the stop and a target are touched on the same day (stop assumed first), and assume a stop order rests at the exchange.

## Results
_Not yet run on real data._ After `python run_experiments.py`, copy the rows for this experiment from
`results/<date>-real/summary.md` here, with the verdict and any decision recorded in `../decisions.md`.
