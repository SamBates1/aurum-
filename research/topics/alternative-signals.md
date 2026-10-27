# Alternative and event-driven signals

Status: reviewed 2026-10-27 for data availability and timestamp quality. None coded yet.

| Signal | Point-in-time history available free? | Timestamp issue | Status |
|---|---|---|---|
| CFTC Commitments of Traders (gold futures positioning) | Yes (CFTC historical files) | Data is as of **Tuesday close** but released **Friday 3:30 pm ET** [S15]; must be aligned to the release, not the as-of date | **Experiment (EXP-008, not yet coded)** |
| Gold ETF flows / holdings | Partly (issuer sites, WGC) | Holdings reported with lags; history often revised | Deferred |
| Central-bank gold purchases | Quarterly/monthly (WGC, IMF) | Long publication lags; slow-moving; mainly explains the 2022+ regime (gold-evidence.md) | Context only |
| Economic-release surprises (CPI, payrolls) | Consensus history is paid | Needs release time and consensus at the time | Rejected for now (data cost) |
| FOMC decisions | Dates are public | Event timing is known in advance; effect on gold is contested | Possible future event study |
| News sentiment | **No** free point-in-time archive | Headlines from Yahoo cover only recent days | Live display only, weight 0 (D-008) |
| Miner earnings / guidance | Dates yes, content point-in-time no | Needs as-reported fundamentals | Rejected for now |
| Volatility (VIX) | Yes | Same-day close | Already a feature; regime gate in EXP-003 |

Principle: a signal is only worth testing if it carries information not already in prices and macro features
**and** its historical values can be placed on the date they were actually known.
