"""Platform phase 1: universe discovery and eligibility, ticker changes, SEC point-in-time accounts, FX, events."""

import numpy as np
import pandas as pd
import pytest

from aurum import events as EV
from aurum import fx, sec
from aurum import universe as U

ASOF = pd.Timestamp("2026-10-30", tz="UTC")


def _bars(price, vol, n=120, end="2026-10-30"):
    idx = pd.bdate_range(end=end, periods=n, tz="UTC")
    return pd.DataFrame({"Open": price, "High": price, "Low": price, "Close": price, "Volume": vol}, index=idx)


def _assets():
    return [
        {
            "symbol": "BIG",
            "name": "Big Company Inc. Common Stock",
            "exchange": "NASDAQ",
            "status": "active",
            "tradable": True,
        },
        {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "exchange": "ARCA", "status": "active", "tradable": True},
        {"symbol": "GLD", "name": "SPDR Gold Trust", "exchange": "ARCA", "status": "active", "tradable": True},
        {
            "symbol": "TQQQ",
            "name": "ProShares UltraPro QQQ 3x",
            "exchange": "NASDAQ",
            "status": "active",
            "tradable": True,
        },
        {"symbol": "PENNY", "name": "Penny Corp", "exchange": "NYSE", "status": "active", "tradable": True},
        {"symbol": "THIN", "name": "Thin Trading Co", "exchange": "NYSE", "status": "active", "tradable": True},
        {"symbol": "OTCX", "name": "Pink Sheet Co", "exchange": "OTC", "status": "active", "tradable": True},
        {"symbol": "STALE", "name": "Stale Corp", "exchange": "NYSE", "status": "active", "tradable": True},
        {"symbol": "NEWCO", "name": "New Listing Inc", "exchange": "NYSE", "status": "active", "tradable": True},
        {"symbol": "NODATA", "name": "No Data Inc", "exchange": "NYSE", "status": "active", "tradable": True},
    ]


def test_universe_eligibility_reasons_and_counts():
    t = U.from_alpaca_assets(_assets())
    assert t.at["SPY", "kind"] == "etf" and t.at["GLD", "kind"] == "commodity etf" and t.at["BIG", "kind"] == "stock"
    assert t.at["TQQQ", "kind"] == "levered etf"
    bars = {
        "BIG": _bars(150.0, 2e6),
        "SPY": _bars(700.0, 5e7),
        "GLD": _bars(350.0, 8e6),
        "TQQQ": _bars(90.0, 5e7),
        "PENNY": _bars(1.2, 9e7),
        "THIN": _bars(40.0, 1000.0),
        "STALE": _bars(50.0, 1e6, end="2026-10-01"),
        "NEWCO": _bars(30.0, 1e6, n=20),
    }
    a = U.assess(t, U.liquidity(bars, ASOF))
    ok = set(a.index[a["eligible"]])
    assert ok == {"BIG", "SPY", "GLD"}
    r = a["reason"]
    assert "leveraged" in r["TQQQ"] and "price" in r["PENNY"] and "a day" in r["THIN"] and "OTC" in r["OTCX"]
    assert "no trade" in r["STALE"] and "history" in r["NEWCO"] and r["NODATA"] == "no price data"
    snap = U.Snapshot(a, ASOF, "test")
    c = snap.counts()
    assert c == {"listed": 10, "eligible": 3, "stocks": 1, "etfs": 2, "commodity_etfs": 1}
    rep = U.coverage_report(snap, {"new": [], "removed": [], "renamed": []})
    assert "Eligible for analysis | 3" in rep and "Why instruments were excluded" in rep


def test_ticker_changes_are_detected(tmp_path):
    old = U.from_alpaca_assets(_assets())
    raw = [x for x in _assets() if x["symbol"] not in ("BIG", "STALE")]
    raw.append(
        {
            "symbol": "BIGG",
            "name": "Big Company Inc. Common Stock",
            "exchange": "NASDAQ",
            "status": "active",
            "tradable": True,
        }
    )
    raw.append({"symbol": "FRESH", "name": "Fresh IPO Inc", "exchange": "NYSE", "status": "active", "tradable": True})
    ch = U.changes(old, U.from_alpaca_assets(raw))
    assert ch["renamed"] == [("BIG", "BIGG")] and ch["new"] == ["FRESH"] and ch["removed"] == ["STALE"]
    snap = U.Snapshot(U.assess(old, None), ASOF, "test")
    U.save(snap, tmp_path)
    back = U.load(tmp_path)
    assert list(back.assets.index) == list(snap.assets.index) and not back.assets["eligible"].any()


def _fact(val, end, filed, start=None, form="10-K", fp="FY"):
    d = {"val": val, "end": end, "filed": filed, "form": form, "fp": fp}
    if start:
        d["start"] = start
    return d


FACTS = {
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        _fact(100e9, "2023-12-31", "2024-02-01", "2023-01-01"),
                        _fact(120e9, "2024-12-31", "2025-02-03", "2024-01-01"),
                        _fact(25e9, "2025-03-31", "2025-05-01", "2025-01-01", "10-Q", "Q1"),  # a quarter: not annual
                        _fact(150e9, "2025-12-31", "2026-02-02", "2025-01-01"),
                        _fact(140e9, "2025-12-31", "2026-08-01", "2025-01-01", "10-K/A"),  # restated later
                    ]
                }
            },
            "NetIncomeLoss": {
                "units": {
                    "USD": [
                        _fact(10e9, "2024-12-31", "2025-02-03", "2024-01-01"),
                        _fact(15e9, "2025-12-31", "2026-02-02", "2025-01-01"),
                    ]
                }
            },
            "OperatingIncomeLoss": {"units": {"USD": [_fact(20e9, "2025-12-31", "2026-02-02", "2025-01-01")]}},
            "NetCashProvidedByUsedInOperatingActivities": {
                "units": {"USD": [_fact(18e9, "2025-12-31", "2026-02-02", "2025-01-01")]}
            },
            "PaymentsToAcquirePropertyPlantAndEquipment": {
                "units": {"USD": [_fact(3e9, "2025-12-31", "2026-02-02", "2025-01-01")]}
            },
            "StockholdersEquity": {"units": {"USD": [_fact(60e9, "2025-12-31", "2026-02-02")]}},
            "LongTermDebt": {"units": {"USD": [_fact(30e9, "2025-12-31", "2026-02-02")]}},
            "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": [_fact(10e9, "2025-12-31", "2026-02-02")]}},
            "AssetsCurrent": {"units": {"USD": [_fact(40e9, "2025-12-31", "2026-02-02")]}},
            "LiabilitiesCurrent": {"units": {"USD": [_fact(20e9, "2025-12-31", "2026-02-02")]}},
        },
        "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [_fact(1e9, "2026-01-20", "2026-02-02")]}}},
    }
}


def test_sec_metrics_are_point_in_time():
    t = sec.facts_table(FACTS)
    before = sec.metrics(t, "2026-01-15")  # the FY2025 report was not filed yet
    assert before["period_end"] == "2024-12-31" and before["revenue"] == 120e9
    assert before["revenue_growth"] == pytest.approx(0.20)
    m = sec.metrics(t, "2026-03-01", price=225.0)
    assert m["period_end"] == "2025-12-31" and m["revenue"] == 150e9  # original figure, restatement not yet filed
    assert m["revenue_growth"] == pytest.approx(0.25) and m["earnings_growth"] == pytest.approx(0.5)
    assert m["net_margin"] == pytest.approx(0.10) and m["operating_margin"] == pytest.approx(20 / 150)
    assert m["roic"] == pytest.approx(20e9 * 0.79 / (60e9 + 30e9 - 10e9))
    assert m["free_cash_flow"] == 15e9 and m["fcf_margin"] == pytest.approx(0.10)
    assert m["debt_to_equity"] == pytest.approx(0.5) and m["current_ratio"] == pytest.approx(2.0)
    assert m["market_cap"] == 225e9 and m["pe"] == pytest.approx(15.0) and m["fcf_yield"] == pytest.approx(15 / 225)
    later = sec.metrics(t, "2026-09-01")
    assert later["revenue"] == 140e9  # the restatement counts only once it was filed
    assert sec.metrics(t, "2020-01-01")["missing"]  # nothing known yet: reported missing, never filled in


def test_fx_rate_known_on_a_date(monkeypatch):
    real_history = fx.history
    s = pd.Series([1.25, 1.27, 1.30], index=pd.to_datetime(["2026-10-27", "2026-10-28", "2026-10-29"]))
    monkeypatch.setattr(fx, "history", lambda cfg=None: (s, "test"))
    r = fx.rate("2026-10-28 12:00")
    assert r.usd_per_gbp == 1.27 and r.date == "2026-10-28" and r.to_gbp(127.0) == pytest.approx(100.0)
    assert fx.rate().usd_per_gbp == 1.30 and "test" in fx.rate().label
    off, src = real_history({"offline": True})
    assert src == "SYNTHETIC" and off.iloc[-1] == fx.SYNTHETIC_RATE


def test_fomc_calendar_and_gap_risk():
    ev = EV.upcoming(None, "2026-10-30", days=60, cfg={"offline": True})
    assert [e.date for e in ev] == ["2026-12-09"] and ev[0].confirmed and ev[0].gap_risk
    nxt = EV.fomc_events("2027-01-01", "2027-02-01")
    assert nxt[0].date == "2027-01-27" and not nxt[0].confirmed  # 2027 dates are tentative until confirmed
    assert all(np.diff([pd.Timestamp(d2).value for _, d2, _ in EV.FOMC]) > 0)
