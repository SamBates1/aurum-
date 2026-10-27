"""Run with:  AURUM_OFFLINE=1 pytest -q"""
import os

os.environ["AURUM_OFFLINE"] = "1"

import numpy as np
import pandas as pd

from aurum import data
from aurum.backtest import run_backtest
from aurum.config import load_config
from aurum.features import build_dataset, technical_features
from aurum.paper import PaperPortfolio
from aurum.pipeline import analyse

CFG = load_config()
CFG["offline"] = True


def test_no_lookahead_in_features():
    """Features computed on truncated history must equal those on full history.
    If any feature peeked at the future, cutting the future off would change it."""
    prices = data.daily_prices("GLD", cfg=CFG)
    full = technical_features(prices)
    cut = 2000
    partial = technical_features(prices.iloc[:cut])
    pd.testing.assert_frame_equal(full.iloc[:cut], partial)


def test_backtest_trades_next_day():
    """A perfect-foresight signal applied *without* the one-day shift would be
    impossible; with the shift, a signal about today's return earns nothing extra."""
    prices = data.daily_prices("GLD", cfg=CFG)
    today_up = (prices["Close"].pct_change() > 0).astype(float)  # knows today's return
    res, _ = run_backtest(prices, today_up, 0.55, 0.45, cost_bps=0)
    # executed tomorrow, knowledge of today's move is worth ~nothing
    assert abs(res["strategy"].mean() * 252) < 0.10


def test_backtest_perfect_foresight_wins():
    prices = data.daily_prices("GLD", cfg=CFG)
    tomorrow_up = (prices["Close"].pct_change().shift(-1) > 0).astype(float)
    res, summary = run_backtest(prices, tomorrow_up, 0.55, 0.45, cost_bps=5)
    assert summary.loc["Sharpe", "Strategy"] > 3


def test_labels_are_future_only():
    prices = data.daily_prices("GLD", cfg=CFG)
    X, y, fwd = build_dataset(prices, None, horizon=5)
    assert y.iloc[-5:].isna().all() and y.iloc[:-5].notna().all()


def test_end_to_end_and_paper(tmp_path):
    a = analyse("NEM", cfg=CFG)
    assert a.signal["decision"] in {"BUY", "SELL", "HOLD"}
    assert 0 <= a.prob_up <= 1
    assert set(a.signal["components"]) >= {"ml", "technical"}
    book = PaperPortfolio(tmp_path / "ledger.json", cfg=CFG)
    px = {"NEM": a.last_price}
    book.apply("NEM", "BUY", a.last_price, a.ann_vol, a.atr, px)
    assert abs(book.equity(px) - 10000) < 1e-6  # buying at market price doesn't change equity
    assert book.state["positions"]["NEM"]["qty"] * a.last_price <= 0.2 * 10000 + 1e-6
    book.apply("NEM", "SELL", a.last_price * 1.1, a.ann_vol, a.atr, px)
    assert "NEM" not in book.state["positions"] and book.state["cash"] > 10000
