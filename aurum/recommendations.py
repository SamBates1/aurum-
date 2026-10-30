"""Recommendations over time (live-charts stage 4): an append-only, hash-chained record of what the strategy said
about each ticker after each completed close, why, and what changed since last time; plus outcome tracking.

Records live in research/recommendations/YYYY-MM.jsonl, one JSON object per line. Each record carries the hash of
the record before it, so any later edit or deletion breaks the chain and `verify` reports where. Each record also
carries the strategy fingerprint (spec hash), the code version and a fingerprint of the price data it used, so the
recommendation can be reproduced (`reproduce`).

A recommendation is "what the strategy says" plus the trade-plan arithmetic. It is not advice and places no order.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from . import analysis as AN
from . import spec as SP
from . import tradeplan as TP
from .config import ROOT
from .indicators import compute

FOLDER = ROOT / "research" / "recommendations"
GENESIS = "0" * 64
HYSTERESIS = 0.02  # a target-weight move smaller than this is not reported as a change


def code_version() -> str:
    sha = os.environ.get("GITHUB_SHA")
    if sha:
        return sha[:12]
    try:
        return subprocess.check_output(["git", "rev-parse", "--short=12", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        h = hashlib.sha256()
        for p in sorted((ROOT / "aurum").glob("*.py")):
            h.update(p.read_bytes())
        return "files-" + h.hexdigest()[:12]


def data_fingerprint(daily: dict[str, pd.DataFrame], as_of) -> str:
    """Hash of every close used, up to and including `as_of` (changes if any input price changes)."""
    h = hashlib.sha256()
    for t in sorted(daily):
        c = daily[t]["Close"]
        c = c[c.index <= pd.Timestamp(as_of)].round(4)
        h.update(t.encode())
        h.update(np.ascontiguousarray(c.to_numpy(float)).tobytes())
        h.update(str(c.index[-1].date() if len(c) else "").encode())
    return h.hexdigest()[:16]


def _hash(rec: dict) -> str:
    body = {k: v for k, v in rec.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def load(folder: Path = FOLDER) -> list[dict]:
    out = []
    for p in sorted(folder.glob("*.jsonl")):
        for line in p.read_text().splitlines():
            if line.strip():
                out.append(json.loads(line))
    return out


def verify(records: list[dict]) -> tuple[bool, str]:
    prev = GENESIS
    for i, r in enumerate(records):
        if r.get("prev_hash") != prev:
            return False, f"record {i + 1} ({r.get('symbol')} {r.get('as_of')}): link to the previous record is broken"
        if _hash(r) != r.get("hash"):
            return False, f"record {i + 1} ({r.get('symbol')} {r.get('as_of')}): contents were changed after recording"
        prev = r["hash"]
    return True, f"{len(records)} records, chain intact"


def latest_for(records: list[dict], symbol: str, strategy_id: str) -> dict | None:
    for r in reversed(records):
        if r["symbol"] == symbol and r["strategy_id"] == strategy_id:
            return r
    return None


def stable_action(prev: dict | None, action: str, weight: float, band: float = HYSTERESIS) -> str:
    """Hysteresis: BUY/HOLD wording flips and tiny weight moves are not new signals. A move from holding to not
    holding (or back) is always reported."""
    if prev is None:
        return action
    pw = float(prev["recommendation"]["target_weight"])
    held_before, held_now = pw > 0, weight > 0
    if held_before == held_now and abs(weight - pw) < band:
        return "HOLD" if held_now else "STAY OUT"
    if held_before and held_now and action == "BUY":
        return "HOLD"  # still held: a re-buy within a held position is a resize, not a new entry
    return action


def indicator_snapshot(d: pd.DataFrame) -> dict:
    c = d["Close"]
    vals = {
        "close": c.iloc[-1],
        "sma50": c.rolling(50).mean().iloc[-1],
        "sma200": c.rolling(200).mean().iloc[-1],
        "rsi14": compute("rsi", d, {"n": 14}).iloc[-1],
        "adx14": compute("adx", d, {"n": 14}).iloc[-1],
        "atr14_pct": compute("atr_pct", d, {"n": 14}).iloc[-1],
        "vol21": compute("volatility", d, {"n": 21}).iloc[-1],
    }
    return {k: (round(float(v), 4) if v is not None and np.isfinite(v) else None) for k, v in vals.items()}


def make_record(
    symbol: str,
    spec: dict,
    daily: dict[str, pd.DataFrame],
    previous: dict | None,
    *,
    rf=0.0,
    holdings: pd.Series | None = None,
    now: pd.Timestamp | None = None,
) -> dict:
    """Build (not yet chained) the record for `symbol` under `spec` from completed daily closes."""
    sv = AN.strategy_view(spec, symbol, daily, rf)
    plan = TP.build(symbol, daily[symbol], sv.run, research_only=sv.research_only, holdings_returns=holdings)
    as_of = plan.as_of
    weight = plan.target_weight
    if sv.research_only:
        # not in the strategy: the rules applied to this ticker are research, never a recommendation
        action, weight, size = "NOT COVERED", 0.0, 0.0
    else:
        action, size = stable_action(previous, plan.action, weight), plan.size_gbp
    rec = {
        "time": str(pd.Timestamp(now or pd.Timestamp.now(tz="UTC")).tz_convert("UTC").floor("s")),
        "as_of": str(pd.Timestamp(as_of).date()),
        "symbol": symbol,
        "strategy_id": spec["id"],
        "strategy_hash": SP.spec_hash(sv.spec),
        "research_only": sv.research_only,
        "code_version": code_version(),
        "data_fingerprint": data_fingerprint({t: daily[t] for t in SP.assets_needed(sv.spec)}, as_of),
        "recommendation": {
            "action": action,
            "raw_action": plan.action,
            "target_weight": round(weight, 4),
            "research_view": plan.action if sv.research_only else None,
            "entry": round(plan.entry, 4),
            "stop": round(plan.stop, 4),
            "targets": [[lab, round(px, 4)] for lab, px, _ in plan.targets],
            "size_gbp": round(size, 2),
            "confidence": plan.confidence,
            "uk_fund": plan.uk_fund,
        },
        "indicators": indicator_snapshot(daily[symbol]),
        "previous": None,
        "changed": [],
    }
    if previous:
        p = previous["recommendation"]
        rec["previous"] = {"as_of": previous["as_of"], "action": p["action"], "target_weight": p["target_weight"]}
        ch = []
        if p["action"] != action:
            ch.append(f"action {p['action']} -> {action}")
        if abs(float(p["target_weight"]) - weight) >= HYSTERESIS:
            ch.append(f"target weight {float(p['target_weight']):.0%} -> {weight:.0%}")
        if previous["strategy_hash"] != rec["strategy_hash"]:
            ch.append("strategy definition changed")
        rec["changed"] = ch
    return rec


def append(records: list[dict], new: list[dict], folder: Path = FOLDER) -> list[dict]:
    """Chain and write new records (skips a symbol/strategy already recorded for that close)."""
    folder.mkdir(parents=True, exist_ok=True)
    seen = {(r["symbol"], r["strategy_id"], r["as_of"]) for r in records}
    prev = records[-1]["hash"] if records else GENESIS
    written = []
    for r in new:
        if (r["symbol"], r["strategy_id"], r["as_of"]) in seen:
            continue
        r = dict(r, seq=len(records) + len(written) + 1, prev_hash=prev)
        r["hash"] = _hash(r)
        prev = r["hash"]
        with open(folder / f"{r['as_of'][:7]}.jsonl", "a") as f:
            f.write(json.dumps(r, sort_keys=True, default=str) + "\n")
        written.append(r)
    return written


def reproduce(rec: dict, spec: dict, daily: dict[str, pd.DataFrame], rf=0.0) -> tuple[bool, str]:
    """Re-run the strategy on the same closes and compare. Different data or strategy are reported, not hidden."""
    cut = {t: d[d.index <= pd.Timestamp(rec["as_of"])] for t, d in daily.items()}
    sv = AN.strategy_view(spec, rec["symbol"], cut, rf)
    if SP.spec_hash(sv.spec) != rec["strategy_hash"]:
        return False, "the strategy definition is different from the recorded one"
    fp = data_fingerprint({t: cut[t] for t in SP.assets_needed(sv.spec)}, rec["as_of"])
    if fp != rec["data_fingerprint"]:
        return False, "the price data differs from what was recorded (revised or different source)"
    w = float(sv.run.compiled.raw_target[rec["symbol"]].iloc[-1])
    ok = abs(w - float(rec["recommendation"]["target_weight"])) < 1e-4
    return ok, f"target weight {w:.4f} vs recorded {rec['recommendation']['target_weight']:.4f}"


def outcomes(
    records: list[dict],
    closes: dict[str, pd.Series],
    horizons=(5, 21),
    benchmark: str = "SPY",
    cost_bps: float = 5.0,
) -> pd.DataFrame:
    """For each record old enough: the ticker's return over the next h trading days after a round-trip cost, the
    benchmark's return, and the difference. Only known future closes are used; younger records are left out."""
    rows = []
    for r in records:
        if r.get("research_only"):
            continue  # not covered by the strategy: nothing to judge
        c = closes.get(r["symbol"])
        b = closes.get(benchmark)
        if c is None or b is None:
            continue
        d0 = pd.Timestamp(r["as_of"])
        if d0 not in c.index or d0 not in b.index:
            continue
        i, j = c.index.get_loc(d0), b.index.get_loc(d0)
        for h in horizons:
            if i + h >= len(c) or j + h >= len(b):
                continue
            ret = c.iloc[i + h] / c.iloc[i] - 1 - 2 * cost_bps / 1e4
            bret = b.iloc[j + h] / b.iloc[j] - 1
            rows.append(
                {
                    "as_of": r["as_of"],
                    "symbol": r["symbol"],
                    "strategy_id": r["strategy_id"],
                    "action": r["recommendation"]["action"],
                    "held": float(r["recommendation"]["target_weight"]) > 0,
                    "horizon_days": h,
                    "return_after_costs": ret,
                    "benchmark_return": bret,
                    "vs_benchmark": ret - bret,
                }
            )
    return pd.DataFrame(rows)


def outcome_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    g = df.groupby(["held", "horizon_days"])
    out = g.agg(
        recommendations=("symbol", "size"),
        avg_return=("return_after_costs", "mean"),
        avg_vs_benchmark=("vs_benchmark", "mean"),
        hit_rate=("return_after_costs", lambda x: float((x > 0).mean())),
    ).reset_index()
    out["held"] = out["held"].map({True: "strategy holds", False: "strategy out"})
    return out
