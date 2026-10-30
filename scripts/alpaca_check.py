"""Check the Alpaca connection with the keys stored as GitHub Secrets (run by .github/workflows/alpaca-check.yml).

Writes research/monitoring/alpaca-check.md: what worked, bar counts per timeframe, the market clock, three headlines
and, if the US market is open, how many IEX trades arrived in 20 seconds. Never prints or saves the keys.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aurum.providers import alpaca_keys, data_label  # noqa: E402
from aurum.providers.alpaca import AlpacaProvider, IEXStream  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "research" / "monitoring" / "alpaca-check.md"


def main():
    lines = [f"# Alpaca connection check ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    ok = True
    if not alpaca_keys():
        lines.append("**FAIL:** keys not found (GitHub Secrets ALPACA_API_KEY and ALPACA_SECRET_KEY).")
        OUT.write_text("\n".join(lines) + "\n")
        print("\n".join(lines))
        sys.exit(1)
    lines.append("Keys found (values not shown).")
    p = AlpacaProvider()
    clock = p.clock()
    lines.append(
        f"Market clock: open={clock['is_open']}, next open {clock.get('next_open')}, next close "
        f"{clock.get('next_close')}."
    )
    lines += ["", "| Symbol | Timeframe | Bars | First | Last | Sources |", "|---|---|---|---|---|---|"]
    for sym, tf in (("SPY", "5m"), ("SPY", "15m"), ("AAPL", "1h"), ("NVDA", "4h"), ("GLD", "1d"), ("SPY", "1w")):
        try:
            b = p.bars(sym, tf)
            lab = data_label(b, p.name)
            lines.append(
                f"| {sym} | {tf} | {len(b)} | {b.index[0]:%Y-%m-%d %H:%M} | {b.index[-1]:%Y-%m-%d %H:%M} | "
                f"{', '.join(lab.sources)} |"
            )
        except Exception as exc:
            ok = False
            lines.append(f"| {sym} | {tf} | FAIL | | | {str(exc)[:120]} |")
    try:
        news = p.news(["AAPL", "NVDA"], limit=3)
        lines += ["", "Latest headlines:"] + [f"- {n['time'][:16]} {n['headline']} ({n['source']})" for n in news]
    except Exception as exc:
        ok = False
        lines.append(f"News FAIL: {str(exc)[:150]}")
    if clock["is_open"]:
        s = IEXStream(["SPY", "AAPL", "GLD"])
        time.sleep(20)
        snap = {k: s.snapshot(k) for k in ("SPY", "AAPL", "GLD")}
        s.stop()
        lines += ["", f"IEX stream: status {snap['SPY']['status']} {snap['SPY']['error']}".rstrip()]
        for k, v in snap.items():
            t = v["trade"]
            lines.append(
                f"- {k}: "
                + (
                    f"last trade {t['price']:.2f}, {v['age_s']:.0f}s old, {len(v['minute_bars'])} minute bars"
                    if t
                    else "no trade in 20 seconds"
                )
            )
        ok = ok and snap["SPY"]["status"] == "connected"
    else:
        lines += ["", "IEX stream: not tested (US market closed)."]
    lines += ["", f"**Result: {'PASS' if ok else 'FAIL'}**"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
