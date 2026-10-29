"""Research lab for the always-invested strategy (stages A-8, EXP-020 onwards).

The traded strategy (vol_hold sized with GVZ, D-020/D-021) does not need the ML model, so it can be
tested on much more history and on assets it has never seen. This module defines that baseline and
every pre-registered variant as a *target weight* per asset; run_lab.py simulates them all through the
same engine (strategy.simulate_weights), costs, fills and periods.

Periods (fixed in research/experiments/README.md before any lab result existed):
    pre       data start -> 2013-10-17   never used by any earlier experiment ("new" history)
    dev       2013-10-18 -> 2023-12-31   the development period used so far
    holdout   2024-01-01 ->              looked at several times already, so no longer pristine
Every signal below uses only data known at the close of the day its weight is decided.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import strategy as S
from .features import align
from .features import atr as atr_fn
from .volatility import realised_21d

SETS = {
    "core": ["GLD", "SLV", "GDX", "NEM", "AEM", "WPM"],
    # out-of-asset confirmation set (EXP-021): precious-metal assets never used in any earlier test
    "other": ["GDXJ", "SIL", "RGLD", "FNV", "KGC", "AU", "PPLT", "PALL"],
}
MINERS = {"NEM", "AEM", "WPM", "RGLD", "FNV", "KGC", "AU"}  # single stocks compared with GDX (EXP-023)
METALS = {"GLD", "SLV"}  # safe-haven metal ETFs (EXP-026 applies only to these)
SILVER = {"SLV", "SIL"}  # use silver positioning instead of gold (EXP-025)
DEV_START, HOLD_START = pd.Timestamp("2013-10-18"), pd.Timestamp("2024-01-01")
CRISES = {  # calendar windows of known market stress, chosen from history, not from results
    "2008 financial crisis": ("2008-03-01", "2008-12-31"),
    "2011-15 gold bear market": ("2011-09-01", "2015-12-31"),
    "2013 gold crash": ("2013-04-01", "2013-06-30"),
    "2020 Covid crash": ("2020-02-20", "2020-03-31"),
    "2022 rate rises": ("2022-03-01", "2022-10-31"),
}
TILT = 0.25  # maximum size of every stage 5-7 tilt (weight x 0.75 ... x 1.25), fixed a priori


def periods(start: pd.Timestamp) -> dict:
    return {
        "pre": (start, DEV_START - pd.Timedelta(days=1)),
        "dev": (max(start, DEV_START), HOLD_START - pd.Timedelta(days=1)),
        "holdout": (HOLD_START, None),
    }


@dataclass
class LabCtx:
    ticker: str
    prices: pd.DataFrame
    rf: pd.Series
    cfg: dict
    shared: dict  # cross-asset inputs: gvz, gld_close, gdx_close, gold, dxy, real_yield, cot_*, epu, gpr
    _cache: dict = field(default_factory=dict)

    @property
    def close(self) -> pd.Series:
        return self.prices["Close"]

    def on_index(self, s: pd.Series | None) -> pd.Series | None:
        return None if s is None else align(s.to_frame("v"), self.prices.index)["v"]

    @property
    def vol21(self) -> pd.Series:
        if "vol21" not in self._cache:
            self._cache["vol21"] = realised_21d(self.close)
        return self._cache["vol21"]

    def sizing_vol(self) -> pd.Series:
        """The traded estimator (D-021): 21-day vol x clip(GVZ / GLD 21-day vol, 0.5, 2). Before GVZ
        exists (June 2008) or if it is missing, plain 21-day vol, exactly as the live fallback."""
        if "svol" not in self._cache:
            gvz, gld = self.shared.get("gvz"), self.shared.get("gld_close")
            if gvz is None or gld is None:
                self._cache["svol"] = self.vol21
            else:
                ratio = ((gvz / 100.0) / realised_21d(gld).where(lambda v: v > 0)).clip(0.5, 2.0)
                r = self.on_index(ratio.dropna())
                # a GVZ value older than a week is not used (as live: stale GVZ -> fallback)
                fresh = self.on_index(pd.Series(ratio.dropna().index, index=ratio.dropna().index))
                stale = (self.prices.index.to_series() - fresh).dt.days > 7
                self._cache["svol"] = (self.vol21 * r).where(r.notna() & ~stale, self.vol21)
        return self._cache["svol"]

    def weight(self, vol: pd.Series | None = None, tv: float | None = None) -> pd.Series:
        vol = self.sizing_vol() if vol is None else vol
        return S.vol_target_weight(vol, tv or self.cfg["strategy"]["target_vol"])

    @property
    def atr(self) -> pd.Series:
        if "atr" not in self._cache:
            self._cache["atr"] = atr_fn(self.prices)
        return self._cache["atr"]


@dataclass
class LabVariant:
    exp: str
    name: str
    description: str
    weight: Callable[[LabCtx], pd.Series]
    every: int = 1  # decide only every n-th trading day (EXP-022 weekly)
    account: float | None = None  # whole shares; account value in dollars, split equally across sleeves (EXP-022)
    trial: bool = True  # counted in DSR/PBO (reference and descriptive rows are not)


# ---------------------------------------------------------------------------
# signals (stages 5-7); each returns a multiplier series on the ticker's dates, 1 = no view
# ---------------------------------------------------------------------------
def capped_tilt(z: pd.Series, sign: float) -> pd.Series:
    """1 + sign x TILT x clip(z / 2, -1, 1): full tilt at |z| = 2, none at 0."""
    return 1 + sign * TILT * (z / 2).clip(-1, 1)


def fair_value_z(
    gold: pd.Series, real_yield: pd.Series, dxy: pd.Series, window: int = 756, refit: int = 21, expanding: bool = False
) -> pd.Series:
    """EXP-024: gold's deviation from a macro fair value, in standard deviations.
    log(gold) = a + b x real yield + c x log(dollar) fitted on the last `window` days (or all days so far),
    refitted every `refit` days on data known at that date. z = (actual - fitted) / residual sd."""
    df = pd.concat([np.log(gold), real_yield, np.log(dxy)], axis=1, keys=["g", "ry", "dx"]).ffill().dropna()
    y, X = df["g"].to_numpy(), np.column_stack([np.ones(len(df)), df["ry"], df["dx"]])
    out, coef, sd = np.full(len(df), np.nan), None, None
    for t in range(window, len(df)):
        if coef is None or (t - window) % refit == 0:
            lo = 0 if expanding else t - window + 1
            coef, *_ = np.linalg.lstsq(X[lo : t + 1], y[lo : t + 1], rcond=None)
            sd = np.std(y[lo : t + 1] - X[lo : t + 1] @ coef, ddof=3)
        out[t] = (y[t] - X[t] @ coef) / sd if sd else np.nan
    return pd.Series(out, index=df.index)


def cot_net(cot: pd.DataFrame) -> pd.Series:
    return (cot["long"] - cot["short"]) / cot["oi"]


def zscore(s: pd.Series, n: int) -> pd.Series:
    return (s - s.rolling(n).mean()) / s.rolling(n).std()


def risk_index_z(s: pd.Series) -> pd.Series:
    """EXP-026: news-based risk index smoothed over 21 days, vs its own last year."""
    sm = s.rolling(21, min_periods=15).mean()
    return zscore(sm, 252)


def chandelier_weights(c: LabCtx, base: pd.Series, mult: float = 3.0, cooldown: int = 10) -> pd.Series:
    """EXP-023: always invested, but go to cash when the close falls more than `mult` ATRs below the
    highest close since (re-)entry; re-enter after `cooldown` trading days."""
    close, atr = c.close.to_numpy(float), c.atr.to_numpy(float)
    w = base.reindex(c.prices.index).to_numpy(float).copy()
    peak, off_until = -np.inf, -1
    for i in range(len(w)):
        if i < off_until:
            w[i] = 0.0
            continue
        if not np.isfinite(close[i]):
            continue
        peak = max(peak, close[i])
        if np.isfinite(atr[i]) and close[i] < peak - mult * atr[i]:
            w[i], off_until, peak = 0.0, i + cooldown + 1, -np.inf
    return pd.Series(w, index=c.prices.index)


def miner_gdx_mult(c: LabCtx) -> pd.Series:
    """EXP-019/023: x1.5 while the 60-day z-score of log(miner / GDX) went below -2, until it is back above 0."""
    gdx = c.on_index(c.shared.get("gdx_close"))
    if c.ticker not in MINERS or gdx is None:
        return pd.Series(1.0, index=c.prices.index)
    z = zscore(np.log(c.close / gdx), 60).to_numpy()
    on, state = np.zeros(len(z)), False
    for i, v in enumerate(z):
        if np.isfinite(v):
            state = True if v < -2 else (False if v > 0 else state)
        on[i] = state
    return pd.Series(np.where(on, 1.5, 1.0), index=c.prices.index)


def fv_mult(c: LabCtx, expanding: bool) -> pd.Series:
    key = f"fvz{expanding}"
    if key not in c.shared:
        g, ry, dx = (c.shared.get(k) for k in ("gold", "real_yield", "dxy"))
        if g is None or ry is None or dx is None:
            raise RuntimeError("fair-value inputs unavailable")
        c.shared[key] = fair_value_z(g, ry, dx, expanding=expanding)
    z = c.on_index(c.shared[key])
    return capped_tilt(z, -1.0).fillna(1.0)  # rich gold (z > 0) -> hold less


def cot_mult(c: LabCtx, kind: str) -> pd.Series:
    cot = c.shared.get("cot_silver" if c.ticker in SILVER else "cot_gold")
    if cot is None:
        raise RuntimeError("CFTC data unavailable")
    net = cot_net(cot)
    if kind == "contrarian":  # crowded speculative long -> hold less
        z, sign = zscore(net, 156), -1.0
    else:  # "flow": follow the last 4 weeks' change in speculative positioning
        z, sign = zscore(net.diff(4), 156), 1.0
    return capped_tilt(c.on_index(z), sign).fillna(1.0)


def risk_mult(c: LabCtx, key: str) -> pd.Series:
    s = c.shared.get(key)
    if s is None:
        raise RuntimeError(f"{key} unavailable")
    if c.ticker not in METALS:
        return pd.Series(1.0, index=c.prices.index)
    zkey = f"{key}_z"
    if zkey not in c.shared:
        c.shared[zkey] = risk_index_z(s)
    return capped_tilt(c.on_index(c.shared[zkey]), 1.0).fillna(1.0)  # more risk in the news -> hold more metal


TILTS: dict[str, Callable[[LabCtx], pd.Series]] = {
    "miner_gdx_tilt": miner_gdx_mult,
    "fv_rolling": lambda c: fv_mult(c, False),
    "fv_expanding": lambda c: fv_mult(c, True),
    "cot_contrarian": lambda c: cot_mult(c, "contrarian"),
    "cot_flow": lambda c: cot_mult(c, "flow"),
    "epu_tilt": lambda c: risk_mult(c, "epu"),
    "gpr_tilt": lambda c: risk_mult(c, "gpr"),
}


def tilted(c: LabCtx, names: list[str]) -> pd.Series:
    m = pd.Series(1.0, index=c.prices.index)
    for n in names:
        m = m * TILTS[n](c)
    return (c.weight() * m).clip(0, 1)


def build_lab_variants(combine: list[str] | None = None) -> list[LabVariant]:
    V: list[LabVariant] = []

    def add(*a, **k):
        V.append(LabVariant(*a, **k))

    add("BASE", "vol_hold_gvz", "Traded strategy: always invested, 15% target, GVZ-adjusted vol", lambda c: c.weight())
    # references (not trials)
    add("REF", "buy_hold", "Fully invested, never resized", lambda c: pd.Series(1.0, index=c.prices.index), trial=False)
    add(
        "REF",
        "vol_hold_21d",
        "As traded but sized with plain 21-day vol (pre-D-021)",
        lambda c: c.weight(c.vol21),
        trial=False,
    )

    # EXP-022 trading the way Alpaca will (practical choices, not signals: not trials)
    add(
        "EXP-022", "weekly", "Orders only every 5th trading day (same band)", lambda c: c.weight(), every=5, trial=False
    )
    add(
        "EXP-022",
        "whole_shares_10k",
        "Whole shares only, $10,000 account",
        lambda c: c.weight(),
        account=10_000,
        trial=False,
    )
    add(
        "EXP-022",
        "whole_shares_100k",
        "Whole shares only, $100,000 account (Alpaca paper default)",
        lambda c: c.weight(),
        account=100_000,
        trial=False,
    )

    # EXP-023 near-misses re-tested on the traded strategy
    add(
        "EXP-023",
        "miner_gdx_tilt",
        "Miners x1.5 while cheap vs GDX (z < -2 until > 0)",
        lambda c: tilted(c, ["miner_gdx_tilt"]),
    )
    add(
        "EXP-023",
        "chandelier_3atr",
        "Cash for 10 days after the close falls 3 ATR below its high since entry",
        lambda c: chandelier_weights(c, c.weight()),
    )

    # EXP-024 fair value
    add(
        "EXP-024",
        "fv_rolling",
        "Hold up to 25% less when gold is rich vs real yields and dollar (3-year fit)",
        lambda c: tilted(c, ["fv_rolling"]),
    )
    add("EXP-024", "fv_expanding", "As fv_rolling, fitted on all history so far", lambda c: tilted(c, ["fv_expanding"]))
    # EXP-025 positioning
    add(
        "EXP-025",
        "cot_contrarian",
        "Hold up to 25% less when speculators are crowded long (3-year z)",
        lambda c: tilted(c, ["cot_contrarian"]),
    )
    add(
        "EXP-025",
        "cot_flow",
        "Follow the 4-week change in speculative positioning (up to +-25%)",
        lambda c: tilted(c, ["cot_flow"]),
    )
    # EXP-026 news-based risk indices (GLD and SLV only)
    add(
        "EXP-026",
        "epu_tilt",
        "GLD/SLV: hold up to 25% more when news-based policy uncertainty is high",
        lambda c: tilted(c, ["epu_tilt"]),
    )
    add(
        "EXP-026",
        "gpr_tilt",
        "GLD/SLV: hold up to 25% more when news-based geopolitical risk is high",
        lambda c: tilted(c, ["gpr_tilt"]),
    )

    # EXP-028 risk map (descriptive: the owner chooses the risk level; not trials)
    for tv in (0.10, 0.20, 0.25, 0.30):
        add(
            "EXP-028",
            f"risk_{int(tv * 100)}",
            f"Traded strategy with a {tv:.0%} volatility target",
            lambda c, tv=tv: c.weight(tv=tv),
            trial=False,
        )

    # EXP-027 combination of whatever passed (names given on the command line after the results)
    if combine:
        add("EXP-027", "combo", "Product of tilts: " + ", ".join(combine), lambda c: tilted(c, combine))
    return V
