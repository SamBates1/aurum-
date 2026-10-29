# Intraday trading: evidence review and plan (2026-10-29)

Owner's request: keep the bot updated through the day and let it trade several times a day when the evidence
supports it. This note sets out what the evidence says, what would have to be true for it to pay, and how it would
be tested and built. **Nothing here is built yet**: intraday backtests need minute data, which comes free with the
Alpaca account (history from 2016), so they come after the Alpaca connection.

## What the evidence says
| Idea | Evidence | Verdict for Aurum |
|---|---|---|
| **Intraday momentum** (the first half-hour's return predicts the last half-hour's) | Gao, Han, Li & Zhou (2018, JFE) [S31]: SPY 1993–2013, R² ≈ 2% (4% in the 2008 crisis), timing strategy ≈ 6% a year, **before costs**. Follow-up work finds it weaker after publication and varying by market. | Worth testing on GLD/GDX with minute data. One round trip a day at most, so costs are manageable. |
| **Gold's around-the-clock pattern** (gold rises in Asian hours and drifts down in Western hours; dips around the London fix in the years of alleged manipulation) | Donati & Jung (CBS thesis, 2019) [S32]: Sharpe up to 1.6 before costs, below the market after costs. | For US-listed ETFs the Asian session is *overnight*, so this argues for holding overnight (what Aurum already does), not for intraday trading. Testable: overnight-only vs daytime-only holding with tradable prices. |
| **Overnight vs daytime returns** | Quantpedia [S20]: apparent overnight drift in GDX comes partly from unreliable daily "open" prices. | Needs real minute prices (e.g. 9:35 ET) to test fairly. Earlier rejection stands until then. |
| **Intraday risk checks** (act on crashes and volatility spikes during the day instead of waiting for the close) | Standard practice (LEAN risk models, Freqtrade protections); our own EXP-001 found intrabar stops better than close-checked ones. | Low risk, likely useful: the first thing to build. |
| **High-frequency prediction from news or order flow** | Dominated by professional firms with faster data and lower costs. | Rejected: no realistic edge for a retail bot. |

## What would have to be true for intraday trading to pay
1. **The edge must beat the costs.** A round trip in GLD costs about 0.06% (3 bps each way); in miners, 0.16–0.20%.
   Ten round trips a day in GDX ≈ 1% a day in costs. A strategy needs an edge per trade larger than that, after
   slippage, which almost no published intraday effect has.
2. **It must survive the same rules** as everything else: pre-registered, minute-level walk-forward, 2× cost test,
   DSR and confirmation on data not used to design it.
3. **Rules and accounts:** the US pattern-day-trader rule ($25,000 minimum) was removed: SEC approval 14 April 2026,
   effective 4 June 2026, with an intraday-margin standard instead; brokers may phase in until 20 October 2027 [S33].
   Alpaca's paper account starts at $100,000, so this does not block testing either way.

## How it would be tested (proposed experiments, run after Alpaca is connected)
- **EXP-029 Intraday momentum**: GLD, SLV, GDX 1-minute bars 2016 onwards (Alpaca, IEX feed). Signal: return from
  the previous close to 10:00 ET; trade in that direction from 15:30 to the close. Rules as in Gao et al., fixed in
  advance; compared with the daily strategy left alone.
- **EXP-030 Overnight vs daytime holding**: hold only from the close to 09:35 ET, only from 09:35 to the close, or
  both (current), using minute prices, not daily opens.
- **EXP-031 Intraday risk check**: during the day, every 5 minutes, if an asset has fallen more than k × its daily
  volatility since the open (k fixed at 3), cut that sleeve to half until the next close. Judged by the risk path.

## How it would run (if anything passes)
- GitHub Actions is fine for once-a-day jobs but not for all-day running (start times can slip by many minutes).
- An all-day bot needs an always-on machine: a small cloud server (≈ £4–6 a month) or a free-tier one, running a
  loop every 1–5 minutes during US market hours, with a heartbeat alert if it stops.
- Same safety design as the daily bot: paper-only keys, a kill switch, position and order limits, reconciliation
  with the broker after every order, and a log of every decision.

## Sources
S20, S31–S33 in [../sources.md](../sources.md).
