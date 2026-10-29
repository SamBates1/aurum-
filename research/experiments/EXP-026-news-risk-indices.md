# EXP-026: News-based risk indices (stage 7, news analysis)

| Field | |
|---|---|
| Status | Run 2026-10-29: EPU small and consistent but below the bar; GPR rejected; not adopted |
| Origin | Stage 7; Baker, Bloom & Davis EPU [S27]; Caldara & Iacoviello GPR [S28]; Baur & Smales (2020) [S29] |

## Why not GDELT and AI headline scoring
Plan was GDELT news tone scored by AI. Checked 2026-10-29: GDELT's free DOC API covers only recent months; full
history needs Google BigQuery (paid account) or terabytes of raw files, and AI scoring of a decade of headlines
cannot be done point-in-time cheaply. Rejected for backtesting. **Instead**, two long-established, free, daily
indices built by counting newspaper articles: Economic Policy Uncertainty (FRED `USEPUINDXD`, from 1985) and the
Geopolitical Risk index (daily, from 1985). AI headline scoring stays a live-only feature to be judged in paper trading.

## Hypothesis
Gold and silver are safe havens: when news-based risk is elevated, they do better, so holding more of them helps.

## Variants (fixed before running)
Index smoothed over 21 days, z-score vs its last 252 days; GLD and SLV weight × (1 + 0.25 × clip(z/2, −1, 1)); miners
unchanged (they are equities, which suffer in risk-off). `epu_tilt` (EPU, lagged 2 business days), `gpr_tilt` (GPR,
lagged 1 business day; the index is occasionally revised, a known limitation).

## Acceptance criteria
Lab rules. EXP-021 criterion 2 cannot be applied (no GLD/SLV in the other set), so a pass is recorded as
"confirmed in time, not across assets".

Lab rules (README, 'Research lab'); run with `python run_lab.py --set core` (and `--fill close`, `--set other`).

## Results (real data, 2026-10-29; `results/2026-10-29-1337-lab-core-real/` and `…-closefill/`; first run's EPU and GPR failed on data handling, fixed and re-run)
| Variant | Core, open: pre / dev / holdout ΔSharpe (dev better) | Core, close | Verdict |
|---|---|---|---|
| epu_tilt | +0.05 (98%) / +0.02 (90%) / +0.00 | +0.06 / +0.02 / +0.01 | INCONCLUSIVE |
| gpr_tilt | −0.04 / −0.00 / −0.07 | −0.04 / −0.00 / −0.07 | REJECT |

Holding a little more gold and silver when news-based policy uncertainty is high helped slightly in every period and
both fill conventions, but the effect (+0.02 to +0.06) is far below the +0.10 bar. Recorded as a candidate to watch in
paper trading, not adopted. Geopolitical risk did not help.
