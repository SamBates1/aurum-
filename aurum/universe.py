"""Investment universe manager (platform phase 1): which US instruments exist, which are usable, and why not.

Source: Alpaca's asset list (paper trading endpoint, read-only) for every US-listed stock and ETF Alpaca supports,
plus daily bars for liquidity. Nothing outside that list is claimed as covered.

Each snapshot records, per symbol: name, exchange, asset kind (stock / ETF / commodity ETF), tradability flags,
last price, 20-day average dollar volume, the last bar date and an eligibility verdict with the reason. Comparing a
snapshot with the previous one finds new listings, removed symbols and likely ticker changes (same name, new symbol).
Snapshots are kept under research/universe/ so changes over time are auditable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .config import ROOT

FOLDER = ROOT / "research" / "universe"
RULES = {
    "min_price": 5.0,  # below this: penny-stock behaviour, wide spreads
    "min_dollar_volume": 5_000_000.0,  # 20-day average dollar volume; below this a $50k pot moves the price
    "max_stale_days": 5,  # no bar for this many business days -> inactive
    "min_history_days": 60,  # need this many daily bars for any analysis
}
EXCHANGES = {"NYSE", "NASDAQ", "ARCA", "AMEX", "BATS", "NYSEARCA"}
# words in an ETF's name that mark the kind of exposure (kept separate from the companies that produce them)
COMMODITY_WORDS = (
    "gold",
    "silver",
    "oil",
    "crude",
    "copper",
    "commodity",
    "platinum",
    "palladium",
    "natural gas",
    "agricultur",
    "metals",
    "uranium",
)
LEVERED_WORDS = ("2x", "3x", "-2x", "-3x", "ultra", "leveraged", "inverse", "short ", "bear ", "bull ")


@dataclass
class Snapshot:
    assets: pd.DataFrame  # one row per symbol, columns as in `columns()`
    taken: pd.Timestamp
    source: str

    def counts(self) -> dict:
        a = self.assets
        return {
            "listed": int(len(a)),
            "eligible": int(a["eligible"].sum()),
            "stocks": int(((a["kind"] == "stock") & a["eligible"]).sum()),
            "etfs": int((a["kind"].str.contains("etf") & a["eligible"]).sum()),
            "commodity_etfs": int(((a["kind"] == "commodity etf") & a["eligible"]).sum()),
        }


def classify(name: str, symbol: str, attributes: list | None = None) -> str:
    """'stock', 'etf', 'commodity etf' or 'levered etf' from the asset's name (Alpaca does not label ETFs)."""
    n = f" {str(name).lower()} "
    is_fund = any(
        w in n
        for w in (
            " etf",
            " fund",
            " trust",
            " ishares",
            " spdr",
            " invesco",
            " vanguard",
            " proshares",
            " direxion",
            " wisdomtree",
            " vaneck",
            " etc ",
        )
    )
    if not is_fund:
        return "stock"
    if any(w in n for w in LEVERED_WORDS):
        return "levered etf"
    if any(w in n for w in COMMODITY_WORDS) and " miners" not in n:
        return "commodity etf"
    return "etf"


def from_alpaca_assets(raw: list[dict]) -> pd.DataFrame:
    """Alpaca /v2/assets rows -> the universe table (before liquidity)."""
    rows = []
    for a in raw:
        if a.get("class", "us_equity") != "us_equity":
            continue
        rows.append(
            {
                "symbol": a["symbol"],
                "name": a.get("name") or "",
                "exchange": a.get("exchange") or "",
                "status": a.get("status") or "",
                "tradable": bool(a.get("tradable")),
                "fractionable": bool(a.get("fractionable")),
                "shortable": bool(a.get("shortable")),
                "kind": classify(a.get("name") or "", a["symbol"]),
            }
        )
    return pd.DataFrame(rows).drop_duplicates("symbol").set_index("symbol").sort_index()


def liquidity(bars: dict[str, pd.DataFrame], asof: pd.Timestamp) -> pd.DataFrame:
    """Per symbol: last price, 20-day average dollar volume, bars available, business days since the last bar."""
    out = {}
    for s, b in bars.items():
        if b is None or not len(b):
            out[s] = {"price": np.nan, "dollar_volume_20d": np.nan, "bars": 0, "stale_days": np.inf, "last_bar": None}
            continue
        b = b.sort_index()
        dv = (b["Close"] * b["Volume"]).tail(20).mean()
        last = pd.Timestamp(b.index[-1])
        last_d = (last.tz_convert("America/New_York") if last.tzinfo else last).date()
        stale = max(0, len(pd.bdate_range(last_d, pd.Timestamp(asof).date())) - 1)
        out[s] = {
            "price": float(b["Close"].iloc[-1]),
            "dollar_volume_20d": float(dv),
            "bars": int(len(b)),
            "stale_days": stale,
            "last_bar": str(last_d),
        }
    return pd.DataFrame.from_dict(out, orient="index")


def assess(table: pd.DataFrame, liq: pd.DataFrame | None, rules: dict = RULES) -> pd.DataFrame:
    """Add `eligible` and `reason` (first failing check, in plain words). Symbols without liquidity data are not
    eligible: coverage is never assumed."""
    t = table.copy()
    if liq is not None and len(liq):
        t = t.join(liq, how="left")
    for c in ("price", "dollar_volume_20d", "bars", "stale_days", "last_bar"):
        if c not in t:
            t[c] = np.nan
    reasons = []
    for _, r in t.iterrows():
        if r["status"] != "active":
            reasons.append("inactive at Alpaca")
        elif not r["tradable"]:
            reasons.append("not tradable at Alpaca")
        elif r["exchange"] not in EXCHANGES:
            reasons.append(f"exchange {r['exchange'] or 'unknown'} (OTC or other)")
        elif r["kind"] == "levered etf":
            reasons.append("leveraged or inverse ETF (decays over time)")
        elif not np.isfinite(r["bars"]) or r["bars"] == 0:
            reasons.append("no price data")
        elif r["stale_days"] > rules["max_stale_days"]:
            reasons.append(f"no trade for {int(r['stale_days'])} business days")
        elif r["bars"] < rules["min_history_days"]:
            reasons.append(f"only {int(r['bars'])} days of history")
        elif r["price"] < rules["min_price"]:
            reasons.append(f"price ${r['price']:.2f} below ${rules['min_price']:.0f}")
        elif r["dollar_volume_20d"] < rules["min_dollar_volume"]:
            reasons.append(
                f"trades ${r['dollar_volume_20d'] / 1e6:.1f}M a day (needs ${rules['min_dollar_volume'] / 1e6:.0f}M)"
            )
        else:
            reasons.append("")
    t["reason"] = reasons
    t["eligible"] = t["reason"] == ""
    return t


def changes(old: pd.DataFrame | None, new: pd.DataFrame) -> dict[str, list]:
    """New listings, removed symbols and likely ticker changes (a removed and a new symbol with the same name)."""
    if old is None or not len(old):
        return {"new": [], "removed": [], "renamed": []}
    added = sorted(set(new.index) - set(old.index))
    gone = sorted(set(old.index) - set(new.index))
    by_name = {str(new.at[s, "name"]).strip().lower(): s for s in added if str(new.at[s, "name"]).strip()}
    renamed = []
    for s in gone:
        n = str(old.at[s, "name"]).strip().lower()
        if n and n in by_name:
            renamed.append((s, by_name[n]))
    moved = {a for a, _ in renamed} | {b for _, b in renamed}
    return {
        "new": [s for s in added if s not in moved],
        "removed": [s for s in gone if s not in moved],
        "renamed": renamed,
    }


def save(snap: Snapshot, folder: Path = FOLDER) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "assets.csv"
    snap.assets.to_csv(path)
    (folder / "snapshot.json").write_text(
        json.dumps({"taken": str(snap.taken), "source": snap.source, "counts": snap.counts(), "rules": RULES}, indent=2)
    )
    return path


def load(folder: Path = FOLDER) -> Snapshot | None:
    p = folder / "assets.csv"
    if not p.is_file():
        return None
    meta = json.loads((folder / "snapshot.json").read_text()) if (folder / "snapshot.json").is_file() else {}
    df = pd.read_csv(p, index_col="symbol", keep_default_na=False, na_values=[""])
    df["eligible"] = df["eligible"].astype(str).str.lower() == "true"
    return Snapshot(df, pd.Timestamp(meta.get("taken", "1970-01-01")), meta.get("source", "unknown"))


def coverage_report(snap: Snapshot, ch: dict) -> str:
    a, c = snap.assets, snap.counts()
    lines = [
        "# Universe coverage",
        "",
        f"Snapshot {snap.taken:%Y-%m-%d %H:%M} UTC from {snap.source}. Only instruments in this list are covered.",
        "",
        "| | Count |",
        "|---|---|",
        f"| Listed by Alpaca (US equities and ETFs) | {c['listed']:,} |",
        f"| Eligible for analysis | {c['eligible']:,} |",
        f"| of which stocks | {c['stocks']:,} |",
        f"| of which ETFs | {c['etfs']:,} |",
        f"| of which commodity ETFs | {c['commodity_etfs']:,} |",
        "",
        "## Why instruments were excluded",
        "",
        "| Reason | Count |",
        "|---|---|",
    ]
    why = a.loc[~a["eligible"], "reason"].str.replace(r"\$[0-9.]+M|\d+", "N", regex=True).value_counts()
    lines += [f"| {r} | {n:,} |" for r, n in why.items()]
    lines += ["", "## Changes since the last snapshot", ""]
    lines.append(f"New: {len(ch['new'])} · removed: {len(ch['removed'])} · likely ticker changes: {len(ch['renamed'])}")
    if ch["renamed"]:
        lines.append("")
        lines += [f"- {o} -> {n}" for o, n in ch["renamed"][:50]]
    lines += [
        "",
        f"Rules: price at least ${RULES['min_price']:.0f}; average daily trading at least "
        f"${RULES['min_dollar_volume'] / 1e6:.0f}M over 20 days; a trade within "
        f"{RULES['max_stale_days']} business days; "
        f"at least {RULES['min_history_days']} days of history; no leveraged or inverse ETFs; "
        "listed on a main exchange.",
    ]
    return "\n".join(lines) + "\n"
