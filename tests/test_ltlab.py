import numpy as np
import pandas as pd

from aurum import ltlab as LL


def _panel(paths: dict[str, list[float]], start="2020-01-01"):
    idx = pd.bdate_range(start, periods=len(next(iter(paths.values()))))
    c = pd.DataFrame(paths, index=idx, dtype=float)
    return c.copy(), c  # open = close: fills at the same price as the previous day's mark is not assumed anywhere


def _run(variant, paths, ranks, level=None, **kw):
    o, c = _panel(paths)
    rank = pd.DataFrame(ranks, index=c.index, dtype=float)
    lv = pd.DataFrame(np.nan if level is None else level, index=c.index, columns=c.columns, dtype=float)
    return LL.simulate(o, c, rank, lv, variant, "2020-01-01", cash0=1200.0, cost=0.0, **kw)


def test_buys_next_open_with_one_twelfth_each_and_never_borrows():
    res = _run("A_none", {"X": [10.0] * 5, "Y": [20.0] * 5}, {"X": [1] * 5, "Y": [2] * 5})
    assert (
        res.equity.iloc[-1] == 1200.0 and abs(res.invested - 0.8 * (200 / 1200)) < 1e-12
    )  # 2 of 12 places, from day 2
    assert res.trades == []


def test_fixed_20pct_limit_sells_at_the_open_after_the_close_that_broke_it():
    px = [100.0, 100.0, 79.0, 60.0, 60.0, 60.0]  # bought day 2 at 100; closes at 79 on day 3; sold day 4's open (60)
    held = _run("A_none", {"X": px}, {"X": [1] * 6})
    cut = _run("C_fixed_20pct", {"X": px}, {"X": [1] * 6})
    assert held.trades == [] and abs(held.equity.iloc[-1] - (1200 - 100 + 60)) < 1e-9
    (t,) = cut.trades
    assert t["why"] == "loss limit" and abs(t["ret"] - (-0.40)) < 1e-12  # a gap below the limit is taken in full
    assert abs(cut.equity.iloc[-1] - (1200 - 40)) < 1e-9


def test_plan_level_is_fixed_on_the_day_the_stock_was_chosen():
    px = [100.0, 100.0, 96.0, 94.0, 94.0, 94.0]
    level = {"X": [95.0, 99.0, 99.0, 99.0, 99.0, 99.0]}  # chosen on day 1 with level 95; later levels are ignored
    res = _run("B_plan_level", {"X": px}, {"X": [1] * 6}, level)
    (t,) = res.trades
    assert t["sold"] == res.equity.index[4] and t["why"] == "loss limit"  # 96 held; 94 < 95 on day 4, sold day 5


def test_monthly_rank_exit_and_replacement():
    n = 45  # two month starts
    res = _run(
        "A_none",
        {"X": [10.0] * n, "Y": [10.0] * n},
        {"X": [1] * 22 + [200] * (n - 22), "Y": [np.nan] * 22 + [1] * (n - 22)},
        max_pos=1,
    )
    (t,) = res.trades
    assert t["symbol"] == "X" and t["why"] == "rank" and t["sold"].month == 2
    assert res.equity.iloc[-1] == 1200.0


def test_rank_and_level_helpers():
    idx = pd.bdate_range("2019-01-01", periods=300)
    c = pd.DataFrame({"UP": np.linspace(20, 60, 300), "DOWN": np.linspace(60, 20, 300), "PENNY": 5.0}, index=idx)
    v = pd.DataFrame(5e6, index=idx, columns=c.columns)
    r = LL.momentum_rank(c, v).iloc[-1]
    assert r["UP"] == 1 and r["DOWN"] == 2 and np.isnan(r["PENNY"])
    lv = LL.plan_level(c * 1.01, c * 0.99, c).iloc[-1]
    assert lv["UP"] < c["UP"].iloc[-1] and lv["DOWN"] < c["DOWN"].iloc[-1]


def test_pass_rule():
    a = {"max_dd": -0.40, "cagr": 0.10}
    ok = {"max_dd": -0.32, "cagr": 0.095}
    assert LL.passes(a, ok, a, ok, a, ok)
    assert not LL.passes(a, {"max_dd": -0.33, "cagr": 0.10}, a, ok, a, ok)  # fall only 17.5% smaller
    assert not LL.passes(a, {"max_dd": -0.30, "cagr": 0.089}, a, ok, a, ok)  # gives up more than 1 point a year
    assert not LL.passes(a, ok, a, {"max_dd": -0.41, "cagr": 0.1}, a, ok)  # worse than the control in one half
