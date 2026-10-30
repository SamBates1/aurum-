"""Recommendation history (live-charts stage 4): hash chain, change records, hysteresis, reproduction, outcomes."""

import json

import pandas as pd
import pytest

from aurum import analysis as AN
from aurum import recommendations as RC
from aurum import spec as SP
from aurum.providers.synthetic import SyntheticProvider

NOW = pd.Timestamp("2026-10-30 21:00", tz="UTC")


@pytest.fixture(scope="module")
def daily():
    p = SyntheticProvider(now=NOW)
    return {s: AN.daily_frame(p.bars(s, "1d"), now=NOW) for s in ("SPY", "GLD", "QQQ")}


def cut(daily, n):
    return {t: d.iloc[:-n] if n else d for t, d in daily.items()}


def test_chain_records_changes_and_detects_tampering(tmp_path, daily):
    spec = SP.library()["spy-gld-70-30-risk-cap"]
    recs = []
    for n in (30, 20, 10, 0):
        d = cut(daily, n)
        prev = RC.latest_for(recs, "SPY", spec["id"])
        recs += RC.append(recs, [RC.make_record("SPY", spec, d, prev, now=NOW)], tmp_path)
    assert len(recs) == 4 and RC.verify(recs)[0]
    assert RC.append(recs, [RC.make_record("SPY", spec, daily, recs[-1], now=NOW)], tmp_path) == []  # once per close
    loaded = RC.load(tmp_path)
    assert [r["hash"] for r in loaded] == [r["hash"] for r in recs]
    assert all(r["previous"] for r in recs[1:]) and recs[0]["previous"] is None
    # edit one stored value: the check must fail and say which record
    f = tmp_path / f"{recs[1]['as_of'][:7]}.jsonl"
    lines = f.read_text().splitlines()
    k = next(i for i, x in enumerate(lines) if json.loads(x)["seq"] == 2)
    r = json.loads(lines[k])
    r["recommendation"]["target_weight"] = 0.99
    lines[k] = json.dumps(r, sort_keys=True)
    f.write_text("\n".join(lines) + "\n")
    ok, msg = RC.verify(RC.load(tmp_path))
    assert not ok and "record 2" in msg


def test_hysteresis_ignores_small_moves_but_reports_entries_and_exits():
    prev = {"recommendation": {"action": "HOLD", "target_weight": 0.70}}
    assert RC.stable_action(prev, "BUY", 0.71) == "HOLD"
    assert RC.stable_action(prev, "SELL", 0.0) == "SELL"
    out = {"recommendation": {"action": "STAY OUT", "target_weight": 0.0}}
    assert RC.stable_action(out, "BUY", 0.5) == "BUY" and RC.stable_action(out, "STAY OUT", 0.0) == "STAY OUT"


def test_recorded_recommendation_reproduces(daily):
    spec = SP.library()["spy-gld-70-30-risk-cap"]
    rec = RC.make_record("SPY", spec, cut(daily, 15), None, now=NOW)
    ok, msg = RC.reproduce(rec, spec, daily)  # later data must not change a past recommendation
    assert ok, msg
    changed = {t: d.assign(Close=d["Close"] * 1.01) for t, d in daily.items()}
    assert not RC.reproduce(rec, spec, changed)[0]


def test_tickers_outside_the_strategy_are_not_covered(daily):
    spec = SP.library()["spy-gld-70-30-monthly"]
    rec = RC.make_record("QQQ", spec, daily, None, now=NOW)
    m = rec["recommendation"]
    assert rec["research_only"] and m["action"] == "NOT COVERED" and m["target_weight"] == 0 and m["size_gbp"] == 0
    assert RC.reproduce(rec, spec, daily)[0]


def test_outcomes_use_only_known_future_closes(daily):
    spec = SP.library()["spy-gld-70-30-monthly"]
    recs = [RC.make_record("SPY", spec, cut(daily, n), None, now=NOW) for n in (30, 3)]
    closes = {t: d["Close"] for t, d in daily.items()}
    out = RC.outcomes(recs, closes, horizons=(5,))
    assert len(out) == 1 and out.iloc[0]["as_of"] == recs[0]["as_of"]  # the 3-day-old one is too young
    i = closes["SPY"].index.get_loc(pd.Timestamp(recs[0]["as_of"]))
    exp = closes["SPY"].iloc[i + 5] / closes["SPY"].iloc[i] - 1 - 0.001
    assert out.iloc[0]["return_after_costs"] == pytest.approx(exp)
    assert out.iloc[0]["vs_benchmark"] == pytest.approx(-0.001)  # SPY against itself: just the costs


def test_multi_timeframe_agreement():
    idx = pd.date_range("2026-01-01", periods=100, freq="D", tz="UTC")
    up = pd.DataFrame({"Close": range(1, 101)}, index=idx, dtype=float)
    down = pd.DataFrame({"Close": range(100, 0, -1)}, index=idx, dtype=float)
    assert AN.multi_timeframe({"1h": up, "1d": up})["verdict"].startswith("All timeframes agree: up")
    assert "conflict" in AN.multi_timeframe({"1h": down, "1d": up})["verdict"]
