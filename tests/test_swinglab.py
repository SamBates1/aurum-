import numpy as np
import pandas as pd

from aurum import swinglab as SL

A = SL.VARIANTS["A_single_2R"]
B = SL.VARIANTS["B_ladder"]
C = SL.VARIANTS["C_ladder_breakeven"]


def run(bars, v, order="conservative", time_idx=None, ref=100.0, stop=90.0):
    o, h, lo, c = (np.array(x, float) for x in zip(*bars))
    return SL.simulate(o, h, lo, c, time_idx, ref, stop, v["targets"], v["breakeven"], order, cost=0.0)


def test_single_target_hit():
    t = run([(100, 101, 99, 100), (100, 121, 99, 120)], A)
    assert t.exit_kind == "target" and abs(t.ret - 0.20) < 1e-12 and abs(t.r_multiple - 2.0) < 1e-12


def test_ladder_sells_each_quarter():
    # R = 10: levels 105, 110, 115, 120
    t = run([(100, 101, 99, 100), (100, 111, 99, 110), (110, 121, 109, 120)], B)
    assert t.exit_kind == "target"
    assert abs(t.ret - (0.25 * (105 + 110 + 115 + 120) / 100 - 1)) < 1e-12


def test_ladder_then_reversal_to_stop():
    t = run([(100, 101, 99, 100), (100, 110.5, 99, 108), (100, 100, 85, 86)], B)
    assert t.exit_kind == "stop"
    assert abs(t.ret - ((0.25 * 105 + 0.25 * 110 + 0.5 * 90) / 100 - 1)) < 1e-12


def test_breakeven_moves_stop_after_first_sale():
    t = run([(100, 101, 99, 100), (100, 106, 99, 104), (103, 103, 95, 96)], C)
    assert t.exit_kind == "breakeven"
    assert abs(t.ret - ((0.25 * 105 + 0.75 * 100) / 100 - 1)) < 1e-12


def test_same_day_stop_and_target_conservative_vs_optimistic():
    bars = [(100, 101, 99, 100), (100, 121, 89, 100)]
    assert run(bars, A).exit_kind == "stop"
    assert run(bars, A, "optimistic").exit_kind == "target"


def test_gap_through_stop_fills_at_open():
    t = run([(100, 101, 99, 100), (80, 82, 78, 81)], A)
    assert t.exit_kind == "stop" and abs(t.ret - (-0.20)) < 1e-12


def test_time_stop_sells_at_open():
    t = run([(100, 101, 99, 100), (101, 103, 100, 102), (104, 105, 103, 104)], A, time_idx=2)
    assert t.exit_kind == "time" and abs(t.ret - 0.04) < 1e-12


def test_costs_charged_on_entry_and_exit():
    o, h, lo, c = (np.array(x, float) for x in zip(*[(100, 101, 99, 100), (100, 121, 99, 120)]))
    t = SL.simulate(o, h, lo, c, None, 100, 90, A["targets"], False, cost=0.0005)
    assert abs(t.ret - (0.20 - 0.001)) < 1e-12


def test_paired_stats_detects_a_consistent_gain():
    rng = np.random.default_rng(0)
    weeks = pd.date_range("2017-01-06", periods=400, freq="W-FRI")
    rows = [{"week": w, "a": x, "b": x + 0.01} for w in weeks for x in rng.normal(0, 0.05, 5)]
    s = SL.paired_stats(pd.DataFrame(rows), "a", "b")
    assert abs(s["mean_diff"] - 0.01) < 1e-9 and s["t"] > 10


def run_add(bars, frac, order="conservative", time_idx=None):
    o, h, lo, c = (np.array(x, float) for x in zip(*bars))
    return SL.simulate_add(o, h, lo, c, time_idx, 100.0, 90.0, frac, order=order, cost=0.0)


def test_no_add_matches_single_target():
    bars = [(100, 101, 99, 100), (100, 121, 99, 120)]
    assert abs(run_add(bars, 0.0)[0] - run(bars, A).ret) < 1e-12


def test_add_half_then_target():
    # add 0.5 at 110, target 120 for 1.5 units: profit 20 + 0.5 x 10 = 25 on 100
    ret, kind, added = run_add([(100, 101, 99, 100), (100, 111, 100.5, 110), (110, 121, 109, 120)], 0.5)
    assert added and kind == "target" and abs(ret - 0.25) < 1e-12


def test_add_then_fall_to_breakeven_loses_only_on_the_add():
    ret, kind, added = run_add([(100, 101, 99, 100), (100, 111, 100.5, 110), (108, 108, 95, 96)], 1.0)
    assert added and kind == "breakeven" and abs(ret - (-0.10)) < 1e-12  # 1 unit x (100 - 110) on 100


def test_add_same_day_low_hits_raised_stop_worst_case():
    ret, kind, added = run_add([(100, 101, 99, 100), (101, 111, 99.5, 100)], 0.5)
    assert added and kind == "breakeven" and abs(ret - (-0.05)) < 1e-12


def test_stop_before_add_level_never_adds():
    ret, kind, added = run_add([(100, 101, 99, 100), (99, 100, 85, 86)], 1.0)
    assert not added and kind == "stop" and abs(ret - (-0.10)) < 1e-12
