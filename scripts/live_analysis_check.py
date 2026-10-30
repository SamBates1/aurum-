"""End-to-end check of Live Analysis on real Alpaca data (run on GitHub by the alpaca-check workflow).

For every watchlist ticker: completed daily closes, the main strategy's view, trade plan, summary, a history record
(built in memory only, never appended) and its reproduction, the timeframe check and news. Writes
research/monitoring/live-analysis-check.md. No keys are written anywhere; nothing places an order.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from aurum import analysis as AN  # noqa: E402
from aurum import recommendations as RC  # noqa: E402
from aurum import spec as SP  # noqa: E402
from aurum import spec_paper as SPP  # noqa: E402
from aurum import summary as SM  # noqa: E402
from aurum import tradeplan as TP  # noqa: E402
from aurum.config import CFG  # noqa: E402
from aurum.providers import data_label, get_provider  # noqa: E402


def main():
    t0 = time.time()
    p = get_provider()
    lib = SP.library()
    mid = [i["spec"]["id"] for i in SPP.configured() if i["role"] == "main"]
    spec = lib[mid[0]] if mid else lib["spy-gld-70-30-monthly"]
    wl = CFG.get("watchlist", {})
    syms = list(wl.get("etfs", [])) + list(wl.get("stocks", []))
    cache = {}

    def daily(t):
        if t not in cache:
            cache[t] = AN.daily_frame(p.bars(t, "1d", start=pd.Timestamp("2016-01-01", tz="UTC")))
        return cache[t]

    hold = TP.holdings_returns({t: daily(t) for t in spec["base_weights"]}, spec["base_weights"])
    clock = p.clock()
    lines = [
        "# Live Analysis check on real data",
        "",
        f"Run {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M} UTC · provider {p.name} · US market "
        f"{'OPEN' if clock.get('is_open') else 'CLOSED'} · main strategy {spec['name']}",
        "",
        "| Ticker | Last completed close | Says | Stop | Size | Confidence | Timeframes | Record "
        "reproduces | News | Problems |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    fails = 0
    for s in syms:
        prob = []
        try:
            s_used, _ = AN.retarget(spec, s)
            d = {t: daily(t) for t in SP.assets_needed(s_used)}
            sv = AN.strategy_view(spec, s, d)
            plan = TP.build(s, d[s], sv.run, research_only=sv.research_only, holdings_returns=hold)
            frames = {k: AN.regular_hours(p.bars(s, k), k).iloc[:-1] for k in ("1h", "1d", "1w")}
            mt = AN.multi_timeframe(frames)
            sm = SM.build(plan, mt, [], None)
            rec = RC.make_record(s, spec, d, None, holdings=hold)
            ok, msg = RC.reproduce(rec, spec, d)
            news = p.news([s], limit=5)
            intr = p.bars(s, "5m")
            lab = data_label(intr, p.name)
            if not ok:
                prob.append(f"reproduce: {msg}")
            if not sm.wrong:
                prob.append("no devil's advocate points")
            if str(plan.as_of.date()) >= str(pd.Timestamp.now(tz="America/New_York").date()) and clock.get("is_open"):
                prob.append("used today's unfinished bar")
            lines.append(
                f"| {s} | {plan.as_of:%Y-%m-%d} | {rec['recommendation']['action']} | ${plan.stop:,.2f} | "
                f"£{rec['recommendation']['size_gbp']:,.0f} | {plan.confidence} | {mt['verdict']} | "
                f"{'yes' if ok else 'NO'} | {len(news)} | "
                f"{'; '.join(prob) or '-'} (5m sources {', '.join(lab.sources)}) |"
            )
        except Exception as exc:
            prob.append(str(exc)[:120])
            lines.append(f"| {s} | - | - | - | - | - | - | - | - | ERROR {'; '.join(prob)} |")
        fails += bool(prob)
    lines += ["", f"{len(syms) - fails} of {len(syms)} tickers without problems; {time.time() - t0:.0f}s."]
    out = ROOT / "research" / "monitoring" / "live-analysis-check.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
