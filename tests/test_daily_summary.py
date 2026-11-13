import pandas as pd

from aurum import daily_summary as DS

DAYS = pd.bdate_range("2026-11-02", periods=4)


def _spy():
    return pd.DataFrame({"Open": [100.0, 101, 102, 103], "Close": [101.0, 102, 99, 104.0]}, index=DAYS)


def _equity():
    return pd.DataFrame(
        {
            "account": [100_000.0, 99_000, 98_500, 98_000],
            "long-term": [50_000.0, 49_500, 49_300, 49_100],
            "swing": [50_000.0, 49_500, 49_200, 48_900],
        },
        index=DAYS,
    )


def test_spy_benchmark_buys_at_the_first_open():
    b = DS.spy_benchmark(_spy(), money=100_000)
    assert b.iloc[0] == 101_000 and b.iloc[-1] == 104_000  # 100,000 / 100 open x the close


def test_summary_compares_each_pot_with_spy_and_reports_the_day():
    s = DS.build(_equity(), _spy(), [], [], [])
    acct, lt, sw = s["rows"]
    assert acct["value"] == 98_000 and acct["day"] == -500 and abs(acct["since_start"] - (-0.02)) < 1e-12
    assert acct["spy_value"] == 104_000 and abs(acct["vs_spy"] - (-0.06)) < 1e-12
    assert lt["spy_value"] == 52_000 and abs(sw["vs_spy"] - (48_900 / 50_000 - 1.04)) < 1e-12
    assert abs(s["spy_day"] - (104 / 99 - 1)) < 1e-12 and s["days"] == 4


def test_fills_since_the_last_close_include_stop_and_target_legs():
    orders = [
        {"client_order_id": "AUR-SW-1", "symbol": "GILD", "side": "buy", "type": "limit", "filled_qty": "29",
         "filled_avg_price": "171.02", "filled_at": "2026-11-02T14:31:00Z",
         "legs": [{"symbol": "GILD", "side": "sell", "type": "stop", "filled_qty": "29", "filled_avg_price": "161.0",
                   "filled_at": "2026-11-05T15:00:00Z"}]},
        {"client_order_id": "AUR-SW-2", "symbol": "EPAM", "side": "sell", "type": "limit", "filled_qty": "31",
         "filled_avg_price": "164.73", "filled_at": "2026-11-05T19:42:00Z"},
    ]  # fmt: skip
    s = DS.build(_equity(), _spy(), orders, [], [])
    assert [(f["symbol"], f["what"]) for f in s["fills"]] == [("GILD", "stop hit"), ("EPAM", "target hit")]


def test_near_stops_and_what_needs_the_owner():
    positions = [
        {"symbol": "SLDE", "current_price": "26.30"},
        {"symbol": "GILD", "current_price": "170.66"},
        {"symbol": "AXTI", "current_price": "42.0"},  # long-term: no stop working
    ]
    open_orders = [
        {"symbol": "SLDE", "side": "sell", "type": "limit", "limit_price": "31.49",
         "legs": [{"type": "stop", "stop_price": "25.85"}]},
        {"symbol": "GILD", "side": "sell", "type": "limit", "limit_price": "189.95",
         "legs": [{"type": "stop", "stop_price": "161.05"}]},
    ]  # fmt: skip
    notes = ["swing: value $48,841", "ACTION NEEDED: H has no working stop"]
    s = DS.build(_equity(), _spy(), [], positions, open_orders, waiting=2, notes=notes)
    (n,) = s["near_stops"]  # GILD is 6% above its stop: not listed
    assert n["symbol"] == "SLDE" and abs(n["gap"] - (26.30 / 25.85 - 1)) < 1e-12
    md = DS.to_markdown(s)
    assert "2 order(s) to approve" in md and "ACTION NEEDED: H" in md and "SLDE $26.30" in md
    assert "Same money in SPY" in md and "$104,000 (+4.0%)" in md


def test_quiet_day_and_missing_spy():
    s = DS.build(_equity(), None, [], [], [])
    assert s["rows"][0]["spy_value"] is None
    md = DS.to_markdown(s)
    assert "Bought and sold since the last close:** nothing." in md and "Needs you:** nothing." in md
