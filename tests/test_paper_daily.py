"""Daily paper trading on GitHub (run_paper_daily.py): catch-up, official-open fills, agreement with the backtest."""

import pandas as pd
import pytest

import run_paper_daily as RPD
from aurum import engine as E
from aurum import safety
from aurum import spec as SP
from aurum import spec_paper as SPP


@pytest.fixture
def setup(tmp_path, monkeypatch, cfg):
    from aurum import data

    monkeypatch.setattr(safety, "ROOT", tmp_path)
    monkeypatch.setattr(safety, "KILL_FILE", tmp_path / "STOP_TRADING")
    daily = {t: data.daily_prices(t, cfg=cfg) for t in ("SPY", "GLD")}
    lib = SP.library()
    return daily, lib, tmp_path, cfg


def test_catch_up_fills_at_the_official_open_and_matches_the_backtest(setup):
    daily, lib, tmp, cfg = setup
    spec = lib["spy-gld-70-30-monthly"]
    start, end = pd.Timestamp("2024-02-27"), pd.Timestamp("2024-06-28")
    tr = SPP.SpecPaperTrader(spec, "main", tmp / "ledger.json", cfg)
    log = RPD.process(tr, {t: p.loc[:start] for t, p in daily.items()})  # first run: only the latest day
    assert tr.book.state["started"] == str(start.date()) and tr.book.state["pending"]
    assert any("decided at the close" in x for x in log)
    tr = SPP.SpecPaperTrader(spec, "main", tmp / "ledger.json", cfg)  # next runs reload the ledger
    for cut in ("2024-03-15", "2024-04-30", str(end.date())):
        RPD.process(tr, {t: p.loc[:cut] for t, p in daily.items()})
    st = tr.book.state
    first = st["trades"][0]
    nxt = daily["SPY"].index[daily["SPY"].index > start][0]
    assert first["time"].startswith(str(nxt.date())) and "official open" in first["time"]
    assert first["price"] == pytest.approx(daily[first["ticker"]].at[nxt, "Open"], rel=1e-6)
    # the paper account follows the backtest of the same strategy over the same days (no cash interest in either)
    window = {t: p.loc[start:end] for t, p in daily.items()}
    bt = E.run_spec(spec, window, 0.0, capital=10_000)
    paper = pd.Series({pd.Timestamp(h["time"]): h["equity"] for h in st["history"]})
    assert abs(paper.iloc[-1] / bt.equity.iloc[-1] - 1) < 0.002
    assert len({h["time"] for h in st["history"]}) == len(st["history"])  # one value per day


def test_status_and_weekly_reports(setup, monkeypatch):
    daily, lib, tmp, cfg = setup
    monkeypatch.setattr(RPD, "PAPER_DIR", tmp)
    tr = SPP.SpecPaperTrader(lib["spy-gld-70-30-risk-cap"], "shadow", tmp / "l.json", cfg)
    RPD.process(tr, {t: p.loc[:"2024-03-01"] for t, p in daily.items()})
    RPD.process(tr, {t: p.loc[:"2024-03-22"] for t, p in daily.items()})
    part = {t: p.loc[:"2024-03-22"] for t, p in daily.items()}
    s = RPD.status_md([tr], part)
    assert "SHADOW" in s and "Equity" in s
    w = RPD.weekly_md([tr], part, 0.0)
    assert "SPY bought and held" in w and "backtest of the same strategy" in w
