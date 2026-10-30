"""Record what the main strategy says about every watchlist ticker after today's close (live-charts stage 4).

Run on GitHub after the US close (paper-trading workflow). Appends hash-chained records to
research/recommendations/, rewrites research/recommendations/latest.md (today's board, what changed) and
outcomes.md (how past recommendations did after costs vs SPY). Prices: Alpaca when keys are set, else Yahoo.
Nothing here places an order.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from aurum import analysis as AN  # noqa: E402
from aurum import recommendations as RC  # noqa: E402
from aurum import spec as SP  # noqa: E402
from aurum import spec_paper as SPP  # noqa: E402
from aurum import tradeplan as TP  # noqa: E402
from aurum.config import CFG  # noqa: E402
from aurum.providers import get_provider  # noqa: E402


def main(folder: Path = RC.FOLDER) -> list[dict]:
    p = get_provider()
    lib = SP.library()
    main_ids = [i["spec"]["id"] for i in SPP.configured() if i["role"] == "main"]
    spec = lib[main_ids[0]] if main_ids else lib["spy-gld-70-30-monthly"]
    wl = CFG.get("watchlist", {})
    symbols = list(wl.get("etfs", [])) + list(wl.get("stocks", []))
    cache: dict[str, pd.DataFrame] = {}

    def daily(t):
        if t not in cache:
            cache[t] = AN.daily_frame(p.bars(t, "1d", start=pd.Timestamp("2016-01-01", tz="UTC")))
        return cache[t]

    hold = TP.holdings_returns({t: daily(t) for t in spec["base_weights"]}, spec["base_weights"])
    records = RC.load(folder)
    ok, msg = RC.verify(records)
    if not ok:
        raise SystemExit(f"Recommendation history failed its integrity check: {msg}")
    new, errors = [], []
    for sym in symbols:
        try:
            s_used, _ = AN.retarget(spec, sym)
            d = {t: daily(t) for t in SP.assets_needed(s_used)}
            new.append(RC.make_record(sym, spec, d, RC.latest_for(records, sym, spec["id"]), holdings=hold))
        except Exception as exc:  # one bad ticker must not stop the others
            errors.append(f"{sym}: {exc}")
    written = RC.append(records, new, folder)
    allrec = records + written
    write_reports(allrec, written, errors, {t: daily(t)["Close"] for t in symbols}, folder, p.name)
    print(f"{len(written)} new records ({len(new) - len(written)} already recorded); {RC.verify(allrec)[1]}")
    for e in errors:
        print("error", e)
    return written


def write_reports(allrec, written, errors, closes, folder: Path, provider: str):
    lines = ["# Latest recommendations (what the main strategy says; not advice)", ""]
    if allrec:
        last = max(r["as_of"] for r in allrec)
        lines.append(f"Close of {last}. Prices: {provider}. Paper trading only.")
        lines += [
            "",
            "| Ticker | Says | Target | Stop | Size | Confidence | UK fund | Changed |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for r in [r for r in allrec if r["as_of"] == last]:
            m = r["recommendation"]
            ro = " (not in the main strategy)" if r["research_only"] else ""
            lines.append(
                f"| {r['symbol']} | {m['action']}{ro} | {m['target_weight']:.0%} | ${m['stop']:,.2f} | "
                f"£{m['size_gbp']:,.0f} | {m['confidence']} | {m['uk_fund']} | {'; '.join(r['changed']) or '-'} |"
            )
    if errors:
        lines += ["", "Errors: " + "; ".join(errors)]
    lines += ["", f"History: {RC.verify(allrec)[1]}."]
    (folder / "latest.md").write_text("\n".join(lines) + "\n")
    out = RC.outcomes(allrec, closes)
    summ = RC.outcome_summary(out)
    txt = ["# How past recommendations turned out", ""]
    if summ.empty:
        txt.append("Not enough history yet: outcomes appear once a recommendation is 5 trading days old.")
    else:
        txt.append(
            "Return of the ticker over the next 1 / 5 / 20 / 60 trading days after a round-trip cost of 10 bps, vs SPY."
        )
        txt.append("")
        txt.append("| | Days | Recommendations | Avg return | Avg vs SPY | Share positive |")
        txt.append("|---|---|---|---|---|---|")
        for _, r in summ.iterrows():
            txt.append(
                f"| {r['held']} | {r['horizon_days']} | {r['recommendations']} | {r['avg_return']:+.2%} | "
                f"{r['avg_vs_benchmark']:+.2%} | {r['hit_rate']:.0%} |"
            )
        txt += ["", "Small samples are noise: judge only after many months."]
    (folder / "outcomes.md").write_text("\n".join(txt) + "\n")


if __name__ == "__main__":
    main()
