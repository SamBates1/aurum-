"""Pre-registered experiments: each is a hypothesis about an idea borrowed from another
trading system or from published research, written down in research/experiments/
BEFORE it is run. This module defines how every variant is simulated; run_experiments.py
runs them all through identical data, dates, costs and accounting and applies the
acceptance rules stated in research/experiments/README.md.

Every variant reuses the shared engine (strategy.simulate), so a kept variant can be
switched on in config.yaml without writing a second implementation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace

import numpy as np
import pandas as pd

from . import model
from . import strategy as S
from .features import align, triple_barrier_labels
from .features import atr as atr_fn
from .pipeline import Research

TB = dict(pt_mult=2.0, sl_mult=2.0, horizon=20)  # EXP-007 barriers, fixed a priori


@dataclass
class Context:
    """Everything a variant may use for one ticker. Caches expensive model runs."""

    ticker: str
    res: Research
    cfg: dict
    gdx_close: pd.Series | None = None
    is_equity: bool = False
    extras: dict = field(default_factory=dict)  # cross-ticker data: xs_returns, gvz, gld_vol (stages 3-4)
    _cache: dict = field(default_factory=dict)

    @property
    def scfg(self) -> dict:
        return self.cfg["strategy"]

    @property
    def start(self):
        return self.res.eval_start

    @property
    def prices(self) -> pd.DataFrame:
        return self.res.prices

    @property
    def atr(self) -> pd.Series:
        if "atr" not in self._cache:
            self._cache["atr"] = atr_fn(self.res.prices)
        return self._cache["atr"]

    def macro_col(self, name: str) -> pd.Series | None:
        m = self.res.macro
        return align(m[[name]], self.prices.index)[name] if name in m else None

    def model_probs(self, name: str) -> pd.Series:
        """Walk-forward probabilities from an alternative model (same features, labels, folds)."""
        key = f"probs:{name}"
        if key not in self._cache:
            mc = self.cfg["model"]
            wf = model.walk_forward(
                self.res.X,
                self.res.y,
                mc["horizon_days"],
                mc["min_train_days"],
                mc["retrain_every_days"],
                mc.get("random_state", 0),
                factory=model.MODEL_FACTORIES[name],
            )
            self._cache[key] = wf.probs
        return self._cache[key]

    def horizon_probs(self, h: int) -> tuple[pd.Series, pd.Series]:
        """Walk-forward P(up over the next h days) with the same features; returns (probs, labels).
        The purge gap equals h, so no training label overlaps the test block."""
        if h == self.cfg["model"]["horizon_days"]:
            return self.res.wf.probs, self.res.y
        key = f"h{h}"
        if key not in self._cache:
            c = self.prices["Close"]
            fwd = c.shift(-h) / c - 1
            y = (fwd > self.cfg["model"]["threshold"]).astype(float).where(fwd.notna())
            mc = self.cfg["model"]
            wf = model.walk_forward(self.res.X, y, h, mc["min_train_days"], mc["retrain_every_days"])
            self._cache[key] = (wf.probs, y)
        return self._cache[key]

    def base_weight(self, vol: pd.Series | None = None, target_vol: float | None = None) -> pd.Series:
        vol = self.res.X["vol_21"] if vol is None else vol
        return S.vol_target_weight(vol, target_vol or self.scfg["target_vol"])

    def simw(self, weight: pd.Series, *, cost_bps: float, band: float = 0.05) -> S.SimResult:
        """Target-weight simulation over the evaluation period with the configured fill."""
        return S.simulate_weights(
            self.prices.loc[self.start :],
            weight.reindex(self.prices.index).loc[self.start :],
            cost_bps=cost_bps,
            cash_rate=self.res.rf,
            band=band,
            fill=self.scfg.get("fill", "open"),
        )

    def tb_labels(self) -> pd.Series:
        if "tb" not in self._cache:
            self._cache["tb"] = triple_barrier_labels(self.prices, self.atr, **TB)
        return self._cache["tb"]

    def tb_probs(self) -> pd.Series:
        if "probs:tb" not in self._cache:
            mc = self.cfg["model"]
            wf = model.walk_forward(
                self.res.X, self.tb_labels(), TB["horizon"], mc["min_train_days"], mc["retrain_every_days"]
            )
            self._cache["probs:tb"] = wf.probs
        return self._cache["probs:tb"]

    def score_with(self, probs: pd.Series, label: pd.Series | None = None, horizon: int | None = None) -> pd.Series:
        """The traded scoring rule with a different model's probabilities (skill measured point-in-time)."""
        label = self.res.y if label is None else label
        horizon = horizon or self.cfg["model"]["horizon_days"]
        auc = S.rolling_auc(probs, label, horizon, self.scfg["ml_skill_min_obs"])
        return S.strategy_score(self.res.X, probs, auc, self.scfg)

    def sim(
        self,
        score: pd.Series | None = None,
        *,
        decisions: pd.Series | None = None,
        cost_bps: float,
        rules: S.RiskRules | None = None,
        block: pd.Series | None = None,
        target_vol: float | None = None,
        fixed_exposure: float | None = None,
    ) -> S.SimResult:
        if decisions is None:
            score = self.res.score if score is None else score
            decisions = S.decisions(score, self.scfg["buy_above"], self.scfg["sell_below"])
        return S.simulate(
            self.prices.loc[self.start :],
            decisions.loc[self.start :],
            self.res.X["vol_21"],
            self.atr,
            cost_bps=cost_bps,
            cash_rate=self.res.rf,
            target_vol=target_vol or self.scfg["target_vol"],
            # every variant uses the configured fill convention (EXP-010 switches it for the whole run)
            rules=replace(rules, fill=self.scfg.get("fill", "open")) if rules else S.rules_from_config(self.scfg),
            block_entries=block,
            fixed_exposure=fixed_exposure,
        )


@dataclass
class Variant:
    exp: str
    name: str
    description: str
    run: Callable[[Context, float], S.SimResult]
    applies_to: str = "all"  # "all" or "miners": non-applicable sleeves run the baseline


# ---------------------------------------------------------------------------
# signal helpers (all use data known at the close of each day)
# ---------------------------------------------------------------------------
def tsmom_score(close: pd.Series, horizons=(252,)) -> pd.Series:
    """Time-series momentum (Moskowitz, Ooi & Pedersen 2012): sign of the past return.
    With several horizons, the average sign (Hurst, Ooi & Pedersen 2017 use 1, 3, 12 months)."""
    signs = [np.sign(close / close.shift(h) - 1) for h in horizons]
    s = pd.concat(signs, axis=1)
    return s.mean(axis=1).where(s.notna().all(axis=1))


def donchian_decisions(prices: pd.DataFrame, entry: int = 50, exit_: int = 20) -> pd.Series:
    """Breakout: BUY when the close exceeds the prior `entry`-day high; SELL when it falls
    below the prior `exit_`-day low (turtle-style). Prior windows exclude today."""
    c = prices["Close"]
    hi, lo = c.shift(1).rolling(entry).max(), c.shift(1).rolling(exit_).min()
    d = pd.Series(S.HOLD, index=c.index, dtype=object)
    d[c > hi] = S.BUY
    d[c < lo] = S.SELL
    return d


def above_sma(s: pd.Series, n: int = 200) -> pd.Series:
    sma = s.rolling(n).mean()
    return (s > sma).where(sma.notna())


def build_variants() -> list[Variant]:
    V = []

    def add(exp, name, desc, fn, applies_to="all"):
        V.append(Variant(exp, name, desc, fn, applies_to))

    # baseline: the strategy exactly as traded
    add("BASE", "baseline", "Traded strategy (config.yaml)", lambda c, k: c.sim(cost_bps=k))

    # EXP-001 stop execution convention
    add(
        "EXP-001",
        "stop_on_close",
        "Stop checked on the close, exit next open (Aurum v0.2 convention)",
        lambda c, k: c.sim(cost_bps=k, rules=S.RiskRules(c.scfg["stop_atr_mult"], stop_mode="close")),
    )

    # EXP-002 trend following / momentum as strategies or filters
    add(
        "EXP-002",
        "tsmom_12m",
        "Long when 12-month return > 0 (time-series momentum)",
        lambda c, k: c.sim(tsmom_score(c.prices["Close"], (252,)), cost_bps=k),
    )
    add(
        "EXP-002",
        "tsmom_1_3_12",
        "Average sign of 1-, 3- and 12-month returns",
        lambda c, k: c.sim(tsmom_score(c.prices["Close"], (21, 63, 252)), cost_bps=k),
    )
    add(
        "EXP-002",
        "donchian_50_20",
        "Breakout: enter on 50-day high, exit on 20-day low",
        lambda c, k: c.sim(decisions=donchian_decisions(c.prices), cost_bps=k),
    )
    add(
        "EXP-002",
        "baseline_trend_filter",
        "Baseline, but no new entries unless 1/3/12-month trend is positive",
        lambda c, k: c.sim(cost_bps=k, block=~(tsmom_score(c.prices["Close"], (21, 63, 252)) > 0)),
    )

    # EXP-003 regime gates (entries blocked in unfavourable regimes; exits unchanged)
    def ry_rising(c):
        ry = c.macro_col("real_yield_10y")
        return None if ry is None else ry.diff(63) > 0

    def vix_stress(c):
        v = c.macro_col("vix")
        return None if v is None else v > 30

    def dollar_up(c):
        d = c.macro_col("dxy")
        return None if d is None else above_sma(d).fillna(False).astype(bool)

    def gold_down(c):
        g = c.macro_col("gold")
        return None if g is None else ~above_sma(g).fillna(True).astype(bool)

    for name, desc, gate in (
        ("gate_real_yields", "No entries while 10y real yield rose over the last 63 days", ry_rising),
        ("gate_vix", "No entries while VIX > 30", vix_stress),
        ("gate_dollar", "No entries while the dollar index is above its 200-day average", dollar_up),
        ("gate_gold_trend", "No entries while gold futures are below their 200-day average", gold_down),
    ):
        add("EXP-003", name, desc, lambda c, k, g=gate: c.sim(cost_bps=k, block=g(c)))

    # EXP-004 model families (same features, labels, folds, scoring rule and skill weighting)
    for m, desc in (
        ("logit", "Regularised logistic regression"),
        ("forest", "Random forest (shallow)"),
        ("hgb_calibrated", "Gradient boosting + chronological Platt calibration"),
        ("ensemble", "Equal-weight average of logistic, boosting and forest"),
    ):
        add("EXP-004", f"model_{m}", desc, lambda c, k, m=m: c.sim(c.score_with(c.model_probs(m)), cost_bps=k))

    # EXP-005 position sizing and risk management
    sc = lambda c: c.scfg  # noqa: E731
    add("EXP-005", "no_stop", "No stop-loss", lambda c, k: c.sim(cost_bps=k, rules=S.RiskRules(stop_atr_mult=None)))
    add(
        "EXP-005",
        "chandelier_3atr",
        "Trailing stop: highest close since entry - 3 ATR (plus initial 2 ATR stop)",
        lambda c, k: c.sim(cost_bps=k, rules=S.RiskRules(sc(c)["stop_atr_mult"], trail_atr_mult=3.0)),
    )
    add(
        "EXP-005",
        "dd_breaker",
        "Exit and pause 21 days if the sleeve falls 15% from its peak",
        lambda c, k: c.sim(cost_bps=k, rules=S.RiskRules(sc(c)["stop_atr_mult"], dd_breaker=(0.15, 21))),
    )
    add(
        "EXP-005",
        "stop_guard",
        "Pause 30 days after 2 stop-outs within 60 days",
        lambda c, k: c.sim(cost_bps=k, rules=S.RiskRules(sc(c)["stop_atr_mult"], stop_guard=(2, 60, 30))),
    )
    add(
        "EXP-005",
        "no_vol_target",
        "Full exposure on entry (no volatility targeting)",
        lambda c, k: c.sim(cost_bps=k, fixed_exposure=1.0),
    )
    add("EXP-005", "target_vol_10", "Volatility target 10%", lambda c, k: c.sim(cost_bps=k, target_vol=0.10))
    add("EXP-005", "target_vol_20", "Volatility target 20%", lambda c, k: c.sim(cost_bps=k, target_vol=0.20))

    # EXP-006 mean reversion
    def boll_rev(c):
        X = c.res.X
        d = pd.Series(S.HOLD, index=X.index, dtype=object)
        d[(X["boll_z"] < -2) & (X["sma200_gap"] > 0)] = S.BUY
        d[X["boll_z"] > 0] = S.SELL
        return d

    def miner_rel(c):
        if c.gdx_close is None:
            return None
        ratio = np.log(c.prices["Close"] / align(c.gdx_close.to_frame("g"), c.prices.index)["g"])
        z = (ratio - ratio.rolling(60).mean()) / ratio.rolling(60).std()
        d = pd.Series(S.HOLD, index=z.index, dtype=object)
        d[z < -2] = S.BUY
        d[z > 0] = S.SELL
        return d

    add(
        "EXP-006",
        "bollinger_reversion",
        "Buy 2-sigma dips in an uptrend; exit at the 20-day mean",
        lambda c, k: c.sim(decisions=boll_rev(c), cost_bps=k),
    )
    add(
        "EXP-006",
        "miner_vs_gdx_reversion",
        "Miners only: buy when 60-day z-score of miner/GDX < -2; exit at 0",
        lambda c, k: c.sim(decisions=miner_rel(c), cost_bps=k) if c.is_equity else c.sim(cost_bps=k),
        applies_to="miners",
    )

    # EXP-007 triple-barrier labelling (and the matching trade plan: stop, target, max hold)
    tb_rules = lambda c: S.RiskRules(  # noqa: E731
        TB["sl_mult"], take_profit_atr_mult=TB["pt_mult"], max_hold_days=TB["horizon"]
    )
    add(
        "EXP-007",
        "tb_model_tb_exits",
        "Model trained on triple-barrier labels; trades exit at the same barriers",
        lambda c, k: c.sim(c.score_with(c.tb_probs(), c.tb_labels(), TB["horizon"]), cost_bps=k, rules=tb_rules(c)),
    )
    add(
        "EXP-007",
        "tb_model_base_exits",
        "Triple-barrier model, baseline exits (ablation)",
        lambda c, k: c.sim(c.score_with(c.tb_probs(), c.tb_labels(), TB["horizon"]), cost_bps=k),
    )
    add(
        "EXP-007",
        "base_model_tb_exits",
        "Baseline model, triple-barrier exits (ablation)",
        lambda c, k: c.sim(cost_bps=k, rules=tb_rules(c)),
    )

    # EXP-013 invested by default: hold unless the score says SELL; protect with stops/exits
    def default_long(c):
        sc = c.res.score
        d = pd.Series(S.HOLD, index=sc.index, dtype=object)
        d[sc > c.scfg["sell_below"]] = S.BUY
        d[sc <= c.scfg["sell_below"]] = S.SELL
        return d

    cool = 10  # trading days before re-entering after a stop, fixed a priori
    add(
        "EXP-013",
        "default_long",
        "Invested unless score <= -0.20; vol-targeted; 2-ATR stop; re-enter 10 days after a stop",
        lambda c, k: c.sim(
            decisions=default_long(c), cost_bps=k, rules=S.RiskRules(sc(c)["stop_atr_mult"], reentry_cooldown_days=cool)
        ),
    )
    add(
        "EXP-013",
        "default_long_full",
        "As default_long but fully invested when in (no vol targeting)",
        lambda c, k: c.sim(
            decisions=default_long(c),
            cost_bps=k,
            fixed_exposure=1.0,
            rules=S.RiskRules(sc(c)["stop_atr_mult"], reentry_cooldown_days=cool),
        ),
    )
    add(
        "EXP-013",
        "default_long_full_nostop",
        "Fully invested unless score <= -0.20; no stop-loss",
        lambda c, k: c.sim(
            decisions=default_long(c), cost_bps=k, fixed_exposure=1.0, rules=S.RiskRules(stop_atr_mult=None)
        ),
    )
    add(
        "EXP-013",
        "default_long_full_chandelier",
        "Fully invested unless score <= -0.20; 3-ATR trailing stop; re-enter 10 days after a stop",
        lambda c, k: c.sim(
            decisions=default_long(c),
            cost_bps=k,
            fixed_exposure=1.0,
            rules=S.RiskRules(sc(c)["stop_atr_mult"], trail_atr_mult=3.0, reentry_cooldown_days=cool),
        ),
    )

    # ------------------------------------------------------------------ stages 3-4 (weights engine)
    from . import volatility as VOL

    # EXP-014: dynamic volatility-sized holding (candidate new baseline, D-019)
    add(
        "EXP-014",
        "vol_hold",
        "Always invested, weight = min(1, 15% / 21-day vol), rebalanced when off by >5 pts",
        lambda c, k: c.simw(c.base_weight(), cost_bps=k),
    )
    add(
        "EXP-014",
        "vol_hold_band0",
        "vol_hold rebalanced every day (no band)",
        lambda c, k: c.simw(c.base_weight(), cost_bps=k, band=0.0),
    )
    add(
        "EXP-014",
        "vol_hold_band10",
        "vol_hold with a 10-point band",
        lambda c, k: c.simw(c.base_weight(), cost_bps=k, band=0.10),
    )

    def monthly(w):
        keep = np.arange(len(w)) % 21 == 0
        return w.where(keep)  # NaN = no order that day

    add(
        "EXP-014",
        "vol_hold_monthly",
        "vol_hold resized only every 21 trading days",
        lambda c, k: c.simw(monthly(c.base_weight()), cost_bps=k, band=0.0),
    )
    add(
        "EXP-014",
        "vol_hold_tv20",
        "vol_hold with a 20% volatility target (more invested)",
        lambda c, k: c.simw(c.base_weight(target_vol=0.20), cost_bps=k),
    )

    # EXP-015: does a prediction model add value on top of vol_hold? (horizons 5, 21, 63 days)
    def ml_tilt(c, h):
        probs, y = c.horizon_probs(h)
        auc = S.rolling_auc(probs, y, h, c.scfg["ml_skill_min_obs"])
        skill = pd.Series(
            S.skill_from_auc(auc.fillna(0.5), c.scfg["ml_auc_floor"], c.scfg["ml_auc_full"]), index=auc.index
        )
        tilt = 1 + skill * (2 * probs.reindex(skill.index).fillna(0.5) - 1)  # 0.5..1.5, 1 = no view
        return (c.base_weight() * tilt.reindex(c.prices.index).fillna(1.0)).clip(0, 1)

    for h in (5, 21, 63):
        add(
            "EXP-015",
            f"ml_tilt_h{h}",
            f"vol_hold weight x (1 + skill x (2P(up over {h}d) - 1)), capped at 1",
            lambda c, k, h=h: c.simw(ml_tilt(c, h), cost_bps=k),
        )

    # EXP-016: cross-sectional ranking among the six assets
    def xs_tilt(c, lookback, skip=0):
        closes = c.extras["xs_closes"]
        mom = closes.shift(skip) / closes.shift(lookback) - 1
        ranks = mom.rank(axis=1)
        n = closes.shape[1]
        r = ranks[c.ticker].where(mom.notna().all(axis=1))
        mult = pd.Series(1.0, index=r.index)
        mult[r > n - 2] = 1.5  # top two
        mult[r <= 2] = 0.5  # bottom two
        return (c.base_weight() * mult.reindex(c.prices.index).fillna(1.0)).clip(0, 1)

    add(
        "EXP-016",
        "xs_mom_126",
        "Rank the six by 6-month return: top two x1.5, bottom two x0.5 (on vol_hold)",
        lambda c, k: c.simw(xs_tilt(c, 126), cost_bps=k),
    )
    add(
        "EXP-016",
        "xs_mom_252_21",
        "Rank by 12-month return skipping the last month: top x1.5, bottom x0.5",
        lambda c, k: c.simw(xs_tilt(c, 252, 21), cost_bps=k),
    )

    # EXP-017: better volatility forecasts for sizing
    add(
        "EXP-017",
        "vol_hold_ewma",
        "vol_hold sized with EWMA volatility (lambda 0.94)",
        lambda c, k: c.simw(c.base_weight(VOL.ewma(c.prices["Close"])), cost_bps=k),
    )
    add(
        "EXP-017",
        "vol_hold_har",
        "vol_hold sized with a HAR forecast (Parkinson regressors)",
        lambda c, k: c.simw(c.base_weight(VOL.har_parkinson(c.prices)), cost_bps=k),
    )

    def gvz_vol(c):
        g = c.extras.get("gvz")
        if g is None:
            raise RuntimeError("GVZ data unavailable")
        gl = align(g.to_frame("g"), c.prices.index)["g"]
        gold_vol = align(c.extras["gld_vol"].to_frame("v"), c.prices.index)["v"]
        return VOL.gvz_adjusted(c.res.X["vol_21"], gl, gold_vol)

    add(
        "EXP-017",
        "vol_hold_gvz",
        "21-day vol scaled by gold implied/realised ratio (GVZ / GLD vol)",
        lambda c, k: c.simw(c.base_weight(gvz_vol(c)), cost_bps=k),
    )

    # EXP-018: GVZ as a risk gate
    def gvz_gate(c):
        g = c.extras.get("gvz")
        if g is None:
            raise RuntimeError("GVZ data unavailable")
        hi = g > g.rolling(252).quantile(0.8)
        hi = align(hi.astype(float).to_frame("h"), c.prices.index)["h"].fillna(0) > 0.5
        return c.base_weight().where(~hi, c.base_weight() * 0.5)

    add(
        "EXP-018",
        "gvz_gate",
        "Halve vol_hold weights while GVZ is above its 1-year 80th percentile",
        lambda c, k: c.simw(gvz_gate(c), cost_bps=k),
    )

    # EXP-019: miner vs GDX relative value as a tilt on vol_hold (follow-up to EXP-006 / EXP-010)
    def miner_tilt(c):
        if not c.is_equity or c.gdx_close is None:
            return c.base_weight()
        ratio = np.log(c.prices["Close"] / align(c.gdx_close.to_frame("g"), c.prices.index)["g"])
        z = (ratio - ratio.rolling(60).mean()) / ratio.rolling(60).std()
        on, state = np.zeros(len(z)), False
        for i, v in enumerate(z.to_numpy()):
            if np.isfinite(v):
                state = True if v < -2 else (False if v > 0 else state)
            on[i] = state
        mult = pd.Series(np.where(on, 1.5, 1.0), index=z.index)
        return (c.base_weight() * mult).clip(0, 1)

    add(
        "EXP-019",
        "miner_gdx_tilt",
        "Miners: vol_hold weight x1.5 while 60-day z of miner/GDX went < -2 until > 0",
        lambda c, k: c.simw(miner_tilt(c), cost_bps=k),
        applies_to="miners",
    )

    # reference rows: shown for comparison, not counted as trials
    always = lambda c: pd.Series(S.BUY, index=c.prices.index, dtype=object)  # noqa: E731
    add(
        "REF",
        "buy_hold",
        "Buy and hold, fully invested, no stops",
        lambda c, k: c.sim(decisions=always(c), cost_bps=k, fixed_exposure=1.0, rules=S.RiskRules(stop_atr_mult=None)),
    )
    add(
        "REF",
        "vol_sized_hold",
        "Always invested, volatility-targeted, no stops",
        lambda c, k: c.sim(decisions=always(c), cost_bps=k, rules=S.RiskRules(stop_atr_mult=None)),
    )
    return V
