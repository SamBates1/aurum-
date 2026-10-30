"""Market scanners (platform phase 3): long-term, swing and cross-asset, in five recorded stages.

1. Validate   - start from the eligible instruments in the universe snapshot (phase 1 rules).
2. Filter     - fast checks on every instrument (price, trading volume, history, volatility band).
3. Analyse    - compute the scanner's signals for the survivors; company accounts only for the shortlist.
4. Rank       - combine percentile ranks with weights from evidence (research/scanner/weights.json, written from
                EXP-051). Signals that failed their test get weight zero; if none passed, every signal counts
                equally and every result is labelled "not supported by evidence".
5. Risk check - drop names with an earnings date inside a swing trade's window and anything the portfolio rules
                block (phase 5 adds holdings-aware checks).
Each stage records how many instruments it kept and why the others went, so coverage is never overstated.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from . import factorlab as FL
from .config import ROOT

FOLDER = ROOT / "research" / "scanner"
WEIGHTS_FILE = FOLDER / "weights.json"
CASH_LIKE_VOL = 0.03  # yearly volatility below 3%: a cash-like fund (left out of long-term rankings)

SCANNERS = {
    "long-term": {
        "kinds": ("stock", "etf", "commodity etf"),
        "min_price": 10.0,
        "min_dollar_volume": 20e6,
        "min_history": 252,
        "atr_band": None,
        "signals": ("momentum", "low_volatility", "near_52w_high", "quality", "value"),
        "shortlist": 300,
        "horizon": "months to years",
    },
    "swing": {
        "kinds": ("stock", "etf"),
        "min_price": 10.0,
        "min_dollar_volume": 20e6,
        "min_history": 200,
        "atr_band": (0.01, 0.06),  # daily range 1% to 6%: enough movement to trade, not a lottery ticket
        "signals": ("short_term_reversal", "breakout", "pullback_in_uptrend", "trend_strength"),
        "shortlist": 300,
        "horizon": "1 to 8 weeks",
    },
    "cross-asset": {
        "kinds": ("etf", "commodity etf"),
        "min_price": 5.0,
        "min_dollar_volume": 5e6,
        "min_history": 252,
        "atr_band": None,
        "signals": ("trend", "momentum", "low_volatility"),
        "shortlist": 100,
        "horizon": "months",
    },
}
# what EXP-034/037/038 already found for the cross-asset signals (no new trials spent on them)
CROSS_ASSET_EVIDENCE = {
    "trend": "tested on 10 ETFs (EXP-038): cuts falls, no better return per unit of risk",
    "momentum": "tested on 10 ETFs (EXP-038): inconclusive",
    "low_volatility": "tested as inverse-volatility sizing (EXP-034, EXP-037): no improvement",
}


@dataclass
class ScanResult:
    scanner: str
    asof: str
    stages: list[tuple[str, int, str]] = field(default_factory=list)  # (stage, kept, note)
    ranking: pd.DataFrame | None = None
    weights: dict[str, float] = field(default_factory=dict)
    evidence: str = "untested"  # "evidence" when at least one signal passed its test

    def summary(self) -> str:
        lines = [f"## {self.scanner.title()} scanner ({SCANNERS[self.scanner]['horizon']})", ""]
        lines += ["| Stage | Kept | Note |", "|---|---|---|"]
        lines += [f"| {s} | {n:,} | {note} |" for s, n, note in self.stages]
        lines.append("")
        if self.evidence == "untested":
            lines.append(
                "**Not supported by evidence:** no signal has passed its test, so all count equally and the "
                "ranking is for information only."
            )
        else:
            lines.append(
                "Weights from test results: " + ", ".join(f"{k} {v:.0%}" for k, v in self.weights.items() if v)
            )
        return "\n".join(lines) + "\n"


def load_weights(path: Path | None = None) -> dict:
    path = path or (FOLDER / "weights.json")
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return {}


def weights_from_tests(
    stats: dict[str, dict], signals: tuple[str, ...], correlations: pd.DataFrame | None = None
) -> dict:
    """Weight = t-statistic of each PASSED signal, shared out among signals that move together (|corr| > 0.6), so
    one idea counted twice does not get double weight. No pass -> {} (the caller falls back to equal, untested)."""
    passed = {k: max(float(stats[k]["t"]), 0.0) for k in signals if stats.get(k, {}).get("verdict") == "PASS"}
    if not passed:
        return {}
    if correlations is not None:
        for a in list(passed):
            twins = [
                b
                for b in passed
                if b != a and a in correlations and b in correlations and abs(correlations.at[a, b]) > 0.6
            ]
            if twins:
                passed[a] /= 1 + len(twins)
    tot = sum(passed.values())
    return {k: v / tot for k, v in passed.items()}


def fast_filter(universe: pd.DataFrame, cfg: dict, atr_pct: pd.Series | None = None) -> tuple[pd.Index, list]:
    a = universe[universe["eligible"]]
    notes = []
    k = a[a["kind"].isin(cfg["kinds"])]
    notes.append(("kind", len(k), f"kinds: {', '.join(cfg['kinds'])}"))
    k = k[k["price"] >= cfg["min_price"]]
    notes.append(("price", len(k), f"price at least ${cfg['min_price']:.0f}"))
    k = k[k["dollar_volume_20d"] >= cfg["min_dollar_volume"]]
    notes.append(("volume", len(k), f"at least ${cfg['min_dollar_volume'] / 1e6:.0f}M traded a day"))
    k = k[k["bars"] >= min(cfg["min_history"], 90)]  # the snapshot holds 90 days; full history is checked in stage 3
    if cfg["atr_band"] and atr_pct is not None:
        lo, hi = cfg["atr_band"]
        ok = atr_pct.reindex(k.index)
        k = k[(ok >= lo) & (ok <= hi)]
        notes.append(("volatility band", len(k), f"daily range {lo:.0%} to {hi:.0%}"))
    return k.index, notes


def cross_asset_signals(p: FL.Panels) -> dict[str, pd.DataFrame]:
    c = p.close
    r = c.pct_change(fill_method=None)
    return {
        "trend": (c / c.rolling(200, min_periods=200).mean() - 1),
        "momentum": c.shift(21) / c.shift(252) - 1,
        "low_volatility": -r.rolling(63, min_periods=50).std(),
    }


def signals_for(scanner: str, p: FL.Panels) -> dict[str, pd.DataFrame]:
    if scanner == "long-term":
        return FL.long_term_signals(p)
    if scanner == "swing":
        return FL.swing_signals(p)
    return cross_asset_signals(p)


def rank(
    scanner: str,
    p: FL.Panels,
    candidates: pd.Index,
    weights: dict[str, float] | None,
    asof=None,
    min_history: int = 200,
) -> tuple[pd.DataFrame, dict, str]:
    """Composite score (0-100) from percentile ranks on `asof` (default: last row), with each signal's raw value and
    rank, so the reason for a position is visible. Returns (table, weights used, 'evidence' | 'untested')."""
    cfg = SCANNERS[scanner]
    sig = signals_for(scanner, p)
    d = p.close.index[-1] if asof is None else pd.Timestamp(asof)
    hist = p.close.loc[:d].notna().sum()
    names = [s for s in candidates if s in p.close.columns and hist.get(s, 0) >= min_history]
    if scanner == "long-term" and names:
        # cash-like funds (T-bill and ultra-short bond ETFs) barely move; they are cash, not investments to rank
        vol = p.close[names].loc[:d].pct_change(fill_method=None).tail(252).std() * np.sqrt(252)
        names = [s for s in names if not (vol.get(s, np.nan) < CASH_LIKE_VOL)]
    cols = [k for k in cfg["signals"] if k in sig]
    raw = pd.DataFrame({k: sig[k].loc[d, names] if names else pd.Series(dtype=float) for k in cols}, index=names)
    pct = raw.rank(pct=True)
    used = {k: v for k, v in (weights or {}).items() if k in cols and v > 0}
    status = "evidence" if used else "untested"
    if not used:
        harmful = {k for k, v in (load_weights().get("tested") or {}).items() if "harmful" in str(v)}
        avail = [k for k in cols if raw[k].notna().any() and k not in harmful]  # tested harmful: no weight at all
        used = {k: 1 / len(avail) for k in avail} if avail else {}
    num = sum(pct[k].fillna(0) * w for k, w in used.items()) if used else pd.Series(0.0, index=names)
    if scanner == "swing":
        # setup signals are events: a missing value means "no setup", which counts as zero, not as unknown
        den = pd.Series(float(sum(used.values())) if used else 1.0, index=names)
    else:
        den = sum(pct[k].notna() * w for k, w in used.items()) if used else pd.Series(1.0, index=names)
    score = (100 * num / den.replace(0, np.nan)).round(1)
    out = pd.concat([score.rename("score"), raw.add_prefix("value_"), pct.add_prefix("rank_").round(3)], axis=1)
    out["signals_known"] = raw.notna().sum(axis=1)
    out = out.sort_values("score", ascending=False)
    out.index.name = "symbol"
    return out, used, status


def risk_check(table: pd.DataFrame, scanner: str, events_by_symbol: dict[str, list] | None) -> tuple[pd.DataFrame, int]:
    """Swing: drop names with an earnings date in the next 8 weeks (overnight gap risk). Returns (kept, dropped)."""
    if scanner != "swing" or not events_by_symbol:
        return table, 0
    bad = {s for s, ev in events_by_symbol.items() if any(getattr(e, "kind", "") == "earnings" for e in ev)}
    kept = table[~table.index.isin(bad)]
    return kept, len(table) - len(kept)


def save(res: ScanResult, folder: Path | None = None) -> Path:
    folder = folder or FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{res.scanner}-latest.csv"
    if res.ranking is not None:
        res.ranking.to_csv(path)
    (folder / f"{res.scanner}-latest.json").write_text(
        json.dumps(
            {
                "scanner": res.scanner,
                "asof": res.asof,
                "stages": res.stages,
                "weights": res.weights,
                "evidence": res.evidence,
            },
            indent=1,
        )
    )
    return path
