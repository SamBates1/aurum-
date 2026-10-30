"""Draw Live Analysis charts from real Alpaca data and save pictures (run on GitHub by the alpaca-check workflow).

Writes research/monitoring/live-chart-<ticker>-<timeframe>.png using the same payload builder and front end as the
dashboard page (self-contained HTML, rendered by a headless browser). No keys are written anywhere.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from aurum import analysis as AN  # noqa: E402
from aurum import spec as SP  # noqa: E402
from aurum.livechart import build_payload  # noqa: E402
from aurum.providers import data_label, get_provider  # noqa: E402

FRONT = ROOT / "aurum" / "livechart" / "frontend"
OUT = ROOT / "research" / "monitoring"
CASES = [
    ("SPY", "1d", "spy-gld-70-30-risk-cap", ["Bollinger 20, 2"]),
    ("SPY", "15m", "spy-gld-70-30-monthly", ["VWAP (session)", "RSI 14"]),
    ("AAPL", "1h", "example-70-30-spy-trend-filter", ["SMA 50", "MACD 12/26/9"]),
]


def html_for(payload: dict) -> str:
    lib = (FRONT / "lightweight-charts.standalone.production.js").read_text()
    main = (FRONT / "main.js").read_text()
    page = (FRONT / "index.html").read_text()
    page = page.replace(
        '<script src="lightweight-charts.standalone.production.js"></script>', f"<script>{lib}</script>"
    )
    boot = (
        "<script>window.parent = {postMessage: function(){}};</script>"
        f"<script>{main}</script>"
        "<script>window.dispatchEvent(new MessageEvent('message', {data: {type: 'streamlit:render', "
        f"args: {{payload: {json.dumps(payload)}}}, theme: {{base: 'light'}}}}}}));</script>"
    )
    return page.replace('<script src="main.js"></script>', boot)


def main():
    from playwright.sync_api import sync_playwright

    p = get_provider()
    lib = SP.library()
    shots = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for sym, tf, sid, extras in CASES:
            s_used, _ = AN.retarget(lib[sid], sym)
            daily = {
                a: AN.daily_frame(p.bars(a, "1d", start=pd.Timestamp("2016-01-01", tz="UTC")))
                for a in SP.assets_needed(s_used)
            }
            sv = AN.strategy_view(lib[sid], sym, daily, 0.0)
            bars = AN.regular_hours(p.bars(sym, tf), tf)
            L = AN.strategy_layers(sv, bars, tf)
            ov, pn = list(L["overlays"]), list(L["panels"])
            for lab in extras:
                parts = AN.extra_indicator(lab, bars)
                ov += [
                    {"name": x["name"], "series": x["series"], "color": "#c98500", "dashed": x.get("dashed")}
                    for x in parts
                    if x["where"] == "price"
                ]
                pp = [x for x in parts if x["where"] == "panel"]
                if pp:
                    pn.append(
                        {
                            "title": lab,
                            "series": [
                                {
                                    "name": x["name"],
                                    "series": x["series"],
                                    "color": AN.OVERLAY_COLOURS[i],
                                    "kind": x.get("kind", "line"),
                                }
                                for i, x in enumerate(pp)
                            ],
                            "levels": AN.PANEL_LEVELS.get(AN.EXTRA[lab][0], []),
                        }
                    )
            lab = data_label(bars, p.name)
            payload = build_payload(
                bars,
                title=f"{sym} · {tf} · {lib[sid]['name']}",
                timeframe=tf,
                overlays=ov,
                panels=pn,
                markers=L["markers"],
                tips=L["tips"],
                strip=L["strip"],
                status=lab.text,
                height=560 + 110 * len(pn),
                visible_bars=160,
            )
            page = browser.new_page(viewport={"width": 1400, "height": payload["height"] + 20})
            errors: list[str] = []
            page.on("pageerror", lambda e, errs=errors: errs.append(str(e)))
            page.set_content(html_for(payload))
            page.wait_for_timeout(1500)
            path = OUT / f"live-chart-{sym.lower()}-{tf}.png"
            page.screenshot(path=str(path))
            shots.append(
                f"- {path.name}: {len(payload['bars'])} bars, {len(payload['markers'])} orders, "
                f"sources {', '.join(lab.sources)}" + (f", ERRORS {errors[:2]}" if errors else "")
            )
            page.close()
        browser.close()
    (OUT / "live-chart-check.md").write_text(
        "# Live chart snapshots from real Alpaca data\n\n" + "\n".join(shots) + "\n"
    )
    print("\n".join(shots))


if __name__ == "__main__":
    main()
