# Gold and mining equities: what the evidence says

Priority 1. Status: literature reviewed 2026-10-27; Aurum's own tests are pre-registered as EXP-002, EXP-003, EXP-006.

## Trend following and time-series momentum
- **Moskowitz, Ooi & Pedersen (2012)** document time-series momentum in 58 liquid futures, commodities
  included: an asset's own past 1–12 month return tends to continue, with partial reversal at longer
  horizons. A diversified strategy earned substantial returns with little exposure to standard factors and did
  best in extreme markets. [S1]
- **Hurst, Ooi & Pedersen (2017)** extend this to 1880–2016 across 67 markets (29 commodities), using an equal
  mix of 1-, 3- and 12-month signals scaled to 10% volatility, net of estimated costs and fees. Positive in every
  decade; average per-market Sharpe about 0.4; positive in 8 of the 10 worst 60/40 drawdowns. [S2]
- **Caveat for Aurum:** the evidence is for *diversified* futures portfolios with long and short positions.
  A single long-only commodity (gold) or a handful of correlated miners captures far less of the
  diversification that drives those Sharpe ratios. Gold is not singled out in these papers' headline results.
- **Implication:** trend/momentum is the most credible *simple baseline* for Aurum and should be beaten
  before ML is trusted. Tested as EXP-002 (12-month, 1/3/12-month blend, Donchian breakout, trend filter).

## Real yields, the dollar and gold
- **Erb & Harvey (2013), "The Golden Dilemma"**: gold is an unreliable inflation hedge over practical horizons;
  its real price was historically high and high real prices preceded below-average real returns; but official
  (central bank) demand from emerging markets could keep pushing prices up. [S3]
- **The real-yield link broke after 2021.** RBC Wealth Management reports the inverse relation between gold
  and 10-year TIPS yields explained most of gold's variation in 2005–2021, but almost none in 2022–2023 and
  little since 2024, citing central-bank net purchases above 1,000 tonnes a year in 2022–2024 (about double
  the 2010–2021 average) and reserve diversification after Russia's reserves were frozen. [S4]
- **Implication:** a model trained mostly on 2010–2021 learned a relationship that later weakened. Aurum's
  development/holdout split (holdout from 2024) is exactly where this shows. Macro features must earn their
  place via ablation (`ml_no_macro` benchmark) and regime gates (EXP-003), not be assumed.

## Mining equities vs gold
- **Tufano (1998)**: the average North American gold miner moved about 2% per 1% move in gold; exposure varies
  over time and across firms, falls with hedging, diversification, higher gold prices and higher gold
  volatility, and rises with leverage. [S5]
- **Implications:** (1) miners need their own models and smaller position sizes (Aurum already trains per
  ticker and volatility-targets); (2) a gold-trend signal may transfer to miners because gold drives them, but
  company-specific risk and equity-market beta add noise, so it must be tested per sleeve; (3) relative value
  between a miner and GDX is a mean-reversion hypothesis (EXP-006), not an established effect.
- Evidence on miners' long-run underperformance vs bullion exists mainly in practitioner commentary; not
  relied on here.

## Volatility targeting for commodities
- **Harvey et al. (2018)**: volatility targeting raises Sharpe ratios for equities and credit (the leverage
  effect), but has **negligible Sharpe benefit for commodities, bonds and currencies**; it does reduce extreme
  returns in all classes. [S7] Moreira & Muir (2017) find large gains for equity factors. [S6]
- **Implication:** for GLD/SLV vol targeting is a risk control, not a return enhancer; for miners (equities)
  there may be a Sharpe benefit. Tested in EXP-005 (`no_vol_target`, `target_vol_10/20`).

## Summary
| Hypothesis | Evidence strength | Aurum test |
|---|---|---|
| Trend/momentum works in commodities (diversified) | Strong, long history | EXP-002 |
| Trend works on gold alone, long-only | Weaker, untested here | EXP-002 |
| Real yields drive gold | Strong 2005–2021, weak since 2022 | EXP-003, ablation |
| Miners ≈ 2× leveraged gold | Established (1998), unstable | per-ticker models; EXP-006 |
| Vol targeting improves commodity Sharpe | Not supported | EXP-005 |
