"""Decision Board (D-036): what the strategy says to do now, in pounds."""

from datetime import timezone

import pandas as pd
import pytest

from aurum import decision_board as DB
from aurum import spec as SP


@pytest.fixture(scope="module")
def daily():
    from aurum import data
    from aurum.config import load_config

    c = load_config()
    c["offline"] = True
    return {t: data.daily_prices(t, cfg=c) for t in ("SPY", "GLD")}


@pytest.fixture(scope="module")
def lib():
    return SP.library()


def ny(s):
    return pd.Timestamp(s, tz="America/New_York").tz_convert(timezone.utc).to_pydatetime()


def upto(d, day):
    return {t: p.loc[:day] for t, p in d.items()}


def test_fresh_money_is_invested_at_the_strategy_weights(daily, lib):
    b = DB.build(lib["spy-gld-70-30-monthly"], upto(daily, "2024-03-12"), {}, 1000, now=ny("2024-03-13 08:00"))
    acts = {r["asset"]: (r["action"], round(r["trade_amount"])) for r in b.rows}
    assert acts == {"SPY": ("BUY", 700), "GLD": ("BUY", 300)}
    assert b.headline.startswith("BUY £700 of SPY (e.g. VUSA)") and "SGLN" in b.headline
    assert b.cash_after == pytest.approx(0, abs=1)


def test_monthly_strategy_holds_between_rebalances_and_names_the_next_day(daily, lib):
    b = DB.build(
        lib["spy-gld-70-30-monthly"], upto(daily, "2024-03-15"), {"SPY": 800, "GLD": 250}, 0, now=ny("2024-03-18 08:00")
    )
    assert all(r["action"] == "HOLD" for r in b.rows)
    assert b.next_check == pd.Timestamp("2024-04-01") and "2024-04-01" in b.headline


def test_rebalance_day_trades_back_to_target_sells_first(daily, lib):
    b = DB.build(
        lib["spy-gld-70-30-monthly"], upto(daily, "2024-04-01"), {"SPY": 800, "GLD": 200}, 0, now=ny("2024-04-02 08:00")
    )
    acts = {r["asset"]: (r["action"], round(r["trade_amount"])) for r in b.rows}
    assert acts == {"SPY": ("SELL", -100), "GLD": ("BUY", 100)}
    assert b.headline.startswith("SELL £100 of SPY") and "sell first" in b.headline
    # three days late is still flagged (acting a few days late made no difference, EXP-044)
    late = DB.build(
        lib["spy-gld-70-30-monthly"], upto(daily, "2024-04-04"), {"SPY": 800, "GLD": 200}, 0, now=ny("2024-04-05 08:00")
    )
    assert {r["action"] for r in late.rows} == {"SELL", "BUY"} and "not yet done" in late.rows[0]["reason"]


def test_band_strategy_ignores_small_drift(daily, lib):
    b = DB.build(
        lib["spy-gld-70-30-risk-cap"],
        upto(daily, "2024-03-15"),
        {"SPY": 700, "GLD": 300},
        0,
        now=ny("2024-03-18 08:00"),
    )
    comp_targets = {r["asset"]: r["target_share"] for r in b.rows}
    for r in b.rows:
        if abs(comp_targets[r["asset"]] - r["current_amount"] / 1000) <= 0.05:
            assert r["action"] == "HOLD"
    assert all("volatility" in r["reason"] for r in b.rows)


def test_live_preview_only_while_the_market_is_open(daily, lib):
    s = lib["example-70-30-spy-trend-filter"]
    comp = upto(daily, "2024-03-12")
    sma = daily["SPY"]["Close"].loc[:"2024-03-12"].rolling(200).mean().iloc[-1]
    above = daily["SPY"]["Close"].loc["2024-03-12"] > sma
    crash = {"SPY": float(sma * (0.8 if above else 1.2)), "GLD": float(daily["GLD"]["Close"].loc["2024-03-12"])}
    closed = DB.build(s, comp, {}, 1000, live=crash, now=ny("2024-03-13 08:00"))
    assert closed.preview_changes == []
    open_ = DB.build(s, comp, {}, 1000, live=crash, now=ny("2024-03-13 12:00"))
    assert any("would flip" in x for x in open_.preview_changes)
    assert [r["action"] for r in open_.rows] == [r["action"] for r in closed.rows]  # the official decision is unchanged


def test_market_status_and_text():
    assert DB.market_status(ny("2024-03-13 10:00"))["open"] and not DB.market_status(ny("2024-03-16 10:00"))["open"]
    assert not DB.market_status(ny("2024-03-13 16:30"))["open"]
    assert "VUSA" in DB.uk_fund("SPY") and "UCITS" in DB.uk_fund("DBC")


def test_board_text_states_it_is_not_advice(daily, lib):
    b = DB.build(lib["spy-gld-70-30-monthly"], upto(daily, "2024-03-12"), {}, 500, now=ny("2024-03-13 08:00"))
    txt = DB.board_text(b)
    assert "BUY SPY" in txt and "£350.00" in txt and "not personal financial advice" in txt


def test_decision_board_page_renders(monkeypatch):
    from streamlit.testing.v1 import AppTest

    from aurum.config import ROOT

    at = AppTest.from_file(str(ROOT / "pages/0_Decision_Board.py"), default_timeout=300)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Decision:" in s.value for s in list(at.success) + list(at.info))
