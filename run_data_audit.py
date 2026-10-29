"""Data-quality audit of every price and macro series Aurum uses or may use (master brief Part B).

    python run_data_audit.py            # real data (needs internet; run on GitHub Actions with an "audit:" line)
    AURUM_OFFLINE=1 python run_data_audit.py   # synthetic: checks the code only

Checks per series: rows, first/last date, staleness, duplicate dates, non-positive prices, High < Low,
Open/Close outside the day's range, zero-volume days, missing trading days against SPY's calendar, and daily
moves beyond 25% (genuine crashes or split/adjustment errors: listed for inspection, not removed).
Writes research/audits/data-audit-<date>[-synthetic].md and a CSV.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from aurum import data
from aurum.config import CFG, ROOT

PRICE_SERIES = {
    "core": ["GLD", "SLV", "GDX", "NEM", "AEM", "WPM"],
    "other precious metals": ["GDXJ", "SIL", "RGLD", "FNV", "KGC", "AU", "PPLT", "PALL"],
    "equities": ["SPY", "QQQ", "IWM", "EFA"],
    "bonds": ["TLT", "IEF", "SHY"],
    "commodities / FX": ["DBC", "CPER", "UUP"],
    "macro (Yahoo)": ["^GVZ", "GC=F", "SI=F", "HG=F", "CL=F", "DX-Y.NYB", "^VIX", "^TNX", "^GSPC"],
}
FRED_SERIES = {
    "DFII10": "10y real yield",
    "T10YIE": "10y breakeven inflation",
    "DTB3": "3-month T-bill",
    "DGS10": "10y nominal yield",
    "DGS2": "2y nominal yield",
    "BAMLH0A0HYM2": "US high-yield credit spread",
    "USEPUINDXD": "economic policy uncertainty (daily)",
}
START = "2004-01-01"


def check_prices(name: str, df: pd.DataFrame, cal: pd.DatetimeIndex | None, now) -> dict:
    c = df["Close"]
    r = c.pct_change(fill_method=None)
    out = {
        "series": name,
        "rows": len(df),
        "first": str(df.index[0].date()),
        "last": str(df.index[-1].date()),
        "stale_days": data.staleness_days(df, now=now),
        "duplicate_dates": int(df.index.duplicated().sum()),
        "non_positive": int((df[["Open", "High", "Low", "Close"]] <= 0).sum().sum()),
        "high_below_low": int((df["High"] < df["Low"]).sum()),
        "open_or_close_outside_range": int(
            (
                (df["Open"] > df["High"] * 1.0001)
                | (df["Open"] < df["Low"] * 0.9999)
                | (df["Close"] > df["High"] * 1.0001)
                | (df["Close"] < df["Low"] * 0.9999)
            ).sum()
        ),
        "zero_volume_share": float((df["Volume"] <= 0).mean()) if "Volume" in df else np.nan,
        "big_moves_gt25pct": ", ".join(f"{d.date()} ({v:+.0%})" for d, v in r[r.abs() > 0.25].items()) or "none",
    }
    if cal is not None:
        span = cal[(cal >= df.index[0]) & (cal <= df.index[-1])]
        out["missing_vs_SPY_calendar"] = int(len(span.difference(df.index)))
        out["extra_vs_SPY_calendar"] = int(len(df.index.difference(span)))
    return out


def main():
    cfg = copy.deepcopy(CFG)
    now = datetime.now(timezone.utc)
    tag = "synthetic" if cfg.get("offline") else "real"
    rows, fred_rows = [], []
    frames = {}
    for group, tickers in PRICE_SERIES.items():
        for t in tickers:
            try:
                frames[t] = (group, data.daily_prices_from(t, START, cfg))
            except Exception as exc:
                rows.append({"group": group, "series": t, "error": f"{type(exc).__name__}: {exc}"})
    cal = frames["SPY"][1].index if "SPY" in frames else None
    for t, (group, df) in frames.items():
        is_macro = group.startswith("macro")
        rows.append({"group": group, **check_prices(t, df, None if is_macro else cal, now)})
    for sid, desc in FRED_SERIES.items():
        try:
            s = data.fred(sid, cfg) if not cfg.get("offline") else data.synthetic.macro([sid])[sid]
            gaps = s.index.to_series().diff().dt.days
            fred_rows.append(
                {
                    "series": sid,
                    "description": desc,
                    "rows": len(s),
                    "first": str(s.index[0].date()),
                    "last": str(s.index[-1].date()),
                    "longest_gap_days": int(gaps.max() or 0),
                    "note": "latest revision, not a point-in-time vintage; used with a 2-business-day lag",
                }
            )
        except Exception as exc:
            fred_rows.append({"series": sid, "description": desc, "error": f"{type(exc).__name__}: {exc}"})
    t = pd.DataFrame(rows)
    f = pd.DataFrame(fred_rows)
    out_dir = ROOT / "research" / "audits"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"data-audit-{now:%Y-%m-%d}" + ("-synthetic" if tag == "synthetic" else "")
    t.to_csv(out_dir / f"{stem}-prices.csv", index=False)
    f.to_csv(out_dir / f"{stem}-fred.csv", index=False)

    L = [f"# Data audit, {now:%Y-%m-%d %H:%M} UTC ({tag})", ""]
    if tag == "synthetic":
        L += ["> **SYNTHETIC DATA.** Checks the code path only.", ""]
    L += [
        "Source: Yahoo Finance via yfinance (split- and dividend-adjusted OHLCV, `auto_adjust=True`) and FRED. "
        f"Requested start {START}. Big moves are listed for inspection, not removed.",
        "",
        "| Group | Series | Rows | First | Last | Stale days | Dup. dates | ≤0 prices | High<Low | O/C outside range | "
        "Zero-volume share | Missing vs SPY days | Extra vs SPY days | Moves > 25% |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for _, r in t.iterrows():
        if isinstance(r.get("error"), str):
            L.append(f"| {r['group']} | {r['series']} | **error**: {r['error']} |" + " |" * 11)
            continue
        miss = "" if pd.isna(r.get("missing_vs_SPY_calendar")) else int(r["missing_vs_SPY_calendar"])
        extra = "" if pd.isna(r.get("extra_vs_SPY_calendar")) else int(r["extra_vs_SPY_calendar"])
        zv = "–" if pd.isna(r["zero_volume_share"]) else f"{r['zero_volume_share']:.1%}"
        L.append(
            f"| {r['group']} | {r['series']} | {r['rows']} | {r['first']} | {r['last']} | {r['stale_days']} | "
            f"{r['duplicate_dates']} | {r['non_positive']} | {r['high_below_low']} | "
            f"{r['open_or_close_outside_range']} | {zv} | {miss} | {extra} | {r['big_moves_gt25pct']} |"
        )
    L += [
        "",
        "## FRED series",
        "",
        "| Series | Description | Rows | First | Last | Longest gap (days) | Note |",
        "|---|---|---|---|---|---|---|",
    ]
    for _, r in f.iterrows():
        if isinstance(r.get("error"), str):
            L.append(f"| {r['series']} | {r['description']} | **error**: {r['error']} | | | | |")
        else:
            L.append(
                f"| {r['series']} | {r['description']} | {r['rows']} | {r['first']} | {r['last']} | "
                f"{r['longest_gap_days']} | {r['note']} |"
            )
    bad = [e for e in data.DATA_EVENTS if e.get("level") in ("error", "warning")]
    if bad:
        L += ["", "## Data events", ""] + [f"- {e['level']}: {e['source']}: {e['message']}" for e in bad]
    (out_dir / f"{stem}.md").write_text("\n".join(L) + "\n")
    print(f"Wrote {out_dir / (stem + '.md')}")


if __name__ == "__main__":
    main()
