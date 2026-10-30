"""Live chart payload and Live Analysis logic (live-charts stage 2): times, no look-ahead, markers, live updates."""

import numpy as np
import pandas as pd
import pytest

from aurum import analysis as AN
from aurum import spec as SP
from aurum.livechart import build_payload, chart_time
from aurum.providers.synthetic import SyntheticProvider

NOW = pd.Timestamp("2026-10-30 18:00", tz="UTC")


@pytest.fixture(scope="module")
def prov():
    return SyntheticProvider(now=NOW)


@pytest.fixture(scope="module")
def daily(prov):
    return {s: AN.daily_frame(prov.bars(s, "1d")) for s in ("SPY", "GLD", "AAPL")}


def test_chart_times_are_new_york_wall_clock_and_dates():
    t = pd.Timestamp("2026-10-30 13:30", tz="UTC")  # 09:30 in New York (summer time)
    assert chart_time(t, True) == int((pd.Timestamp("2026-10-30 09:30") - pd.Timestamp("1970-01-01")).total_seconds())
    assert chart_time(pd.Timestamp("2026-10-30 04:00", tz="UTC"), False) == "2026-10-30"  # Alpaca daily stamp
    assert chart_time(pd.Timestamp("2026-10-30 00:00", tz="UTC"), False) == "2026-10-30"  # UTC-midnight stamp


def test_payload_drops_gaps_and_never_places_a_marker_before_its_time(prov):
    bars = prov.bars("SPY", "15m")
    s = pd.Series(np.nan, index=bars.index)
    s.iloc[-5:] = 1.0
    late = bars.index[-3] + pd.Timedelta(minutes=7)  # inside the third-last bar
    early = bars.index[0] - pd.Timedelta(days=30)  # before the chart starts: dropped
    p = build_payload(
        bars,
        title="t",
        timeframe="15m",
        overlays=[{"name": "x", "series": s, "color": "#000"}],
        markers=[{"time": late, "side": "BUY", "text": "BUY 5%"}, {"time": early, "side": "SELL"}],
        tips={late: "<b>why</b>"},
        price_lines=[
            {"price": 100, "title": "stop", "color": "#f00"},
            {"price": float("nan"), "title": "x", "color": "#f00"},
        ],
    )
    assert len(p["overlays"][0]["data"]) == 5
    assert [m["time"] for m in p["markers"]] == [p["bars"][-3]["time"]]
    assert list(p["tips"]) == [str(p["bars"][-3]["time"])] and len(p["price_lines"]) == 1
    times = [b["time"] for b in p["bars"]]
    assert times == sorted(times) and len(set(times)) == len(times)


def test_strategy_indicators_on_intraday_bars_use_the_previous_close(prov, daily):
    sma = daily["SPY"]["Close"].rolling(200).mean()
    bars = prov.bars("SPY", "15m")
    known = AN.as_known_on(sma, bars.index, "15m")
    for t in bars.index[::40]:
        d = pd.Timestamp(t.tz_convert(AN.NY).date())
        expect = sma[sma.index < d].dropna()
        assert known[t] == pytest.approx(expect.iloc[-1])
    dbars = prov.bars("SPY", "1d")
    on_day = AN.as_known_on(sma, dbars.index, "1d").dropna()
    d0 = on_day.index[-1]
    assert on_day.iloc[-1] == pytest.approx(sma.loc[pd.Timestamp(d0.tz_convert(AN.NY).date())])


def test_rules_applied_to_another_ticker_are_research_only(daily):
    lib = SP.library()
    s, research = AN.retarget(lib["example-70-30-spy-trend-filter"], "AAPL")
    assert research and s["universe"] == ["AAPL"] and "research only" in s["name"]
    assert s["signals"][0]["conditions"][0]["right"]["asset"] == "AAPL"
    same, r2 = AN.retarget(lib["spy-gld-70-30-monthly"], "GLD")
    assert not r2 and same["universe"] == ["SPY", "GLD"]
    sv = AN.strategy_view(lib["example-70-30-spy-trend-filter"], "AAPL", daily)
    assert sv.research_only and "not Fair-Tested" in sv.notes[0]


def test_markers_are_the_strategys_own_orders_at_the_next_open(prov, daily):
    lib = SP.library()
    sv = AN.strategy_view(lib["spy-gld-70-30-risk-cap"], "SPY", daily)
    bars = prov.bars("SPY", "1d")
    L = AN.strategy_layers(sv, bars, "1d")
    orders = sv.run.trades[sv.run.trades["ticker"] == "SPY"]
    assert len(L["markers"]) == len(orders) and set(L["strip"].dropna()) <= {"held", "cash"}
    first = L["markers"][0]
    assert pd.Timestamp(first["time"]).tz_convert(AN.NY).date() == pd.Timestamp(orders.iloc[0]["date"]).date()
    assert any("volatility" in p["title"] for p in L["panels"])
    tip = next(iter(L["tips"].values()))
    assert "Decided at the close of" in tip and "of the account" in tip


def test_live_trade_updates_the_last_bar_or_starts_a_new_one(prov):
    bars = prov.bars("SPY", "5m").iloc[-3:]
    last = bars.index[-1]
    same, ch = AN.apply_live(bars, {"price": 999.0, "time": last + pd.Timedelta(minutes=2)}, "5m")
    assert ch and same["High"].iloc[-1] == 999.0 and same["Close"].iloc[-1] == 999.0 and len(same) == 3
    new, ch2 = AN.apply_live(bars, {"price": 1.0, "time": last + pd.Timedelta(minutes=11)}, "5m")
    assert (
        ch2 and len(new) == 4 and new.index[-1] == last + pd.Timedelta(minutes=10) and new["source"].iloc[-1] == "IEX"
    )
    old, ch3 = AN.apply_live(bars, {"price": 1.0, "time": last - pd.Timedelta(hours=1)}, "5m")
    assert not ch3 and old.equals(bars)


def test_regular_hours_filter():
    idx = pd.date_range("2026-10-29 08:00", "2026-10-29 21:00", freq="5min", tz="America/New_York").tz_convert("UTC")
    df = pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0, "Volume": 1.0, "source": "SIP"}, index=idx)
    r = AN.regular_hours(df, "5m").index.tz_convert("America/New_York")
    assert r[0].strftime("%H:%M") == "09:30" and r[-1].strftime("%H:%M") == "15:55"


@pytest.mark.parametrize("label", list(AN.EXTRA))
def test_every_extra_indicator_builds(prov, label):
    parts = AN.extra_indicator(label, prov.bars("AAPL", "1h"))
    assert parts and all(len(x["series"].dropna()) > 10 for x in parts)


def test_live_analysis_page_renders_offline(monkeypatch):
    from streamlit.testing.v1 import AppTest

    from aurum.config import ROOT

    at = AppTest.from_file(str(ROOT / "pages/1_Live_Analysis.py"), default_timeout=300)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    at.sidebar.text_input[0].set_value("AAPL").run()
    assert not at.exception and any("research only" in w.value for w in at.warning)
