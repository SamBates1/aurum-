"""Swing exit lab (EXP-052): one target at 2R versus selling in four steps (a "ladder").

Every variant takes the same entries (the swing pot's live-test signal, `trend_strength`, top 10 each Friday) with the
live swing plan's stop (`aurum/investplan.py`) and 28-day time stop; only the profit-taking differs, so the comparison
is paired trade by trade. Daily bars cannot show the order of moves within a day: by default a day that touches both
the stop and a target is assumed to hit the stop first (conservative); `order="optimistic"` reverses that as a check.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

VARIANTS: dict[str, dict] = {
    "A_single_2R": {"targets": ((2.0, 1.0),), "breakeven": False},
    "B_ladder": {"targets": ((0.5, 0.25), (1.0, 0.25), (1.5, 0.25), (2.0, 0.25)), "breakeven": False},
    "C_ladder_breakeven": {"targets": ((0.5, 0.25), (1.0, 0.25), (1.5, 0.25), (2.0, 0.25)), "breakeven": True},
}
TIME_STOP_DAYS = 28
COST = 0.0005  # 5 bps of traded value per fill
TOP_N = 10


@dataclass
class Trade:
    ret: float  # after costs, fraction of the entry value
    r_multiple: float  # (exit value - entry value) / (shares x R), before costs
    exit_kind: str  # how the last part left: stop / breakeven / target / time / end


def simulate(
    o: np.ndarray,
    h: np.ndarray,
    lo: np.ndarray,
    c: np.ndarray,
    time_idx: int | None,
    ref: float,
    stop: float,
    targets: tuple[tuple[float, float], ...],
    breakeven: bool = False,
    order: str = "conservative",
    cost: float = COST,
) -> Trade:
    """One trade. Arrays start on the entry day (bought at o[0]); `ref` is the signal close C and R = ref - stop.

    Each target is (multiple of R above ref, fraction of the position). time_idx: the bar whose open sells whatever is
    left (None: hold to the last bar's close)."""
    entry = float(o[0])
    R = ref - stop
    levels = sorted(((ref + m * R, f) for m, f in targets), key=lambda x: x[0])
    left, proceeds, stp, kind = 1.0, 0.0, float(stop), "end"
    pending = list(levels)

    def sell(frac: float, px: float) -> None:
        nonlocal left, proceeds
        proceeds += frac * px
        left -= frac

    def raise_stop() -> None:
        nonlocal stp
        if breakeven and left < 1.0 - 1e-12:
            stp = max(stp, ref)

    n = len(o)
    for i in range(n):
        if time_idx is not None and i == time_idx and i > 0:
            sell(left, float(o[i]))
            kind = "time"
            break
        # at the open: gaps through a level fill at the open (on day 0 the open is the entry price itself)
        if o[i] <= stp:
            sell(left, float(o[i]))
            kind = "breakeven" if stp > stop else "stop"
            break
        for lv in [x for x in pending if o[i] >= x[0]]:
            sell(lv[1], float(o[i]))
            pending.remove(lv)
        raise_stop()
        if left <= 1e-12:
            kind = "target"
            break
        hit_targets = [x for x in pending if h[i] >= x[0]]
        stop_hit = lo[i] <= stp
        if stop_hit and (order == "conservative" or not hit_targets):
            sell(left, stp)
            kind = "breakeven" if stp > stop else "stop"
            break
        for lv in hit_targets:
            sell(lv[1], lv[0])
            pending.remove(lv)
        raise_stop()
        if left <= 1e-12:
            kind = "target"
            break
        if lo[i] <= stp:  # the stop (possibly just raised) was also reached later that day
            sell(left, stp)
            kind = "breakeven" if stp > stop else "stop"
            break
    else:
        sell(left, float(c[-1]))
        kind = "end"
    ret = proceeds / entry - 1 - 2 * cost
    return Trade(ret, (proceeds - entry) / R if R > 0 else np.nan, kind)


def entries(signal: pd.DataFrame, fridays: pd.DatetimeIndex, top_n: int = TOP_N) -> list[tuple[pd.Timestamp, str]]:
    out = []
    for d in fridays:
        if d not in signal.index:
            continue
        x = signal.loc[d].dropna()
        out += [(d, s) for s in x.sort_values(ascending=False).index[:top_n]]
    return out


def paired_stats(trades: pd.DataFrame, a: str, b: str, halves=("2020-12-31", "2021-01-01"), recent="2024-01-01"):
    """Mean per-trade difference b - a, with a Newey-West t on the weekly averages (lags 4: trades overlap 4 weeks)."""
    from .xlab import newey_west_t

    d = (trades[b] - trades[a]).groupby(trades["week"]).mean().sort_index()
    y = d.to_numpy(float)
    _, t = newey_west_t(y, np.ones((len(y), 1)), 4) if len(y) > 8 else (None, [np.nan])
    idx = pd.DatetimeIndex(d.index)
    return {
        "mean_diff": float(np.mean(y)) if len(y) else np.nan,
        "t": float(t[0]),
        "first_half": float(d[idx <= pd.Timestamp(halves[0])].mean()),
        "second_half": float(d[idx >= pd.Timestamp(halves[1])].mean()),
        "recent": float(d[idx >= pd.Timestamp(recent)].mean()),
        "weeks": int(len(y)),
    }
