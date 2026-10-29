"""Portfolio research lab (brief of 2026-10-29: entries, scaling, stops, sizing, risk rules; EXP-032 to EXP-036).

Every variant returns a table of target *portfolio* weights (assets x dates) that portfolio.simulate_portfolio
trades in one account, like the paper trader and a broker. Rules that depend on the account's own equity
(circuit breakers, loss limits) are passed as an `overlay` factory, so each simulation starts with fresh state.
Parameters are fixed in the EXP files before any run; nothing here is tuned on results.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import portfolio as P
from . import strategy as S
from .lab import LabCtx, chandelier_weights

MINER_GROUP = {"GDX", "NEM", "AEM", "WPM", "GDXJ", "SIL", "RGLD", "FNV", "KGC", "AU"}
TILT_UP = 1.25  # size of every pre-registered "add" rule (x1.25), fixed a priori


@dataclass
class PortCtx:
    ctxs: dict[str, LabCtx]
    cfg: dict

    @property
    def tickers(self) -> list[str]:
        return list(self.ctxs)

    @property
    def index(self) -> pd.DatetimeIndex:
        idx = None
        for c in self.ctxs.values():
            idx = c.prices.index if idx is None else idx.intersection(c.prices.index)
        return idx.sort_values()

    @property
    def sleeve(self) -> float:
        return S.sleeve_weight(len(self.ctxs), self.cfg["strategy"]["max_position_pct"])

    def frame(self, fn: Callable[[LabCtx], pd.Series]) -> pd.DataFrame:
        return pd.DataFrame({t: fn(c).reindex(self.index) for t, c in self.ctxs.items()})

    def base(self, tv: float | None = None, vol: str = "sizing") -> pd.DataFrame:
        """Traded rule: sleeve share x min(1, target vol / forecast vol), as a share of total equity."""

        def w(c: LabCtx):
            v = c.sizing_vol() if vol == "sizing" else vol_window(c, int(vol))
            return c.weight(v, tv)

        return self.frame(w) * self.sleeve


def vol_window(c: LabCtx, n: int) -> pd.Series:
    """Sizing volatility with an n-day realised window, with the same GVZ ratio as the traded rule (EXP-035)."""
    plain = c.close.pct_change(fill_method=None).rolling(n).std() * np.sqrt(252)
    ratio = c.sizing_vol() / c.vol21
    return plain * ratio.fillna(1.0)


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()


def cond_tilt(c: LabCtx, cond: pd.Series, mult: float) -> pd.Series:
    """Multiplier series: `mult` where cond is True, else 1 (unknown -> 1)."""
    return pd.Series(np.where(cond.fillna(False).to_numpy(bool), mult, 1.0), index=c.prices.index)


def trailing_pct_weights(c: LabCtx, base: pd.Series, pct: float, cooldown: int = 21) -> pd.Series:
    """Cash for `cooldown` days after the close falls more than `pct` below its highest close since (re-)entry."""
    close = c.close.to_numpy(float)
    w = base.reindex(c.prices.index).to_numpy(float).copy()
    peak, off_until = -np.inf, -1
    for i in range(len(w)):
        if i < off_until:
            w[i] = 0.0
            continue
        if not np.isfinite(close[i]):
            continue
        peak = max(peak, close[i])
        if close[i] < peak * (1 - pct):
            w[i], off_until, peak = 0.0, i + cooldown + 1, -np.inf
    return pd.Series(w, index=c.prices.index)


def months_since_start(idx: pd.DatetimeIndex) -> np.ndarray:
    return np.array([(d.year - idx[0].year) * 12 + d.month - idx[0].month for d in idx])


def cap_group(w: pd.DataFrame, group: set[str], cap: float) -> pd.DataFrame:
    cols = [t for t in w.columns if t in group]
    tot = w[cols].sum(axis=1)
    f = (cap / tot).where(tot > cap, 1.0)
    out = w.copy()
    out[cols] = w[cols].mul(f, axis=0)
    return out


def inverse_vol_same_gross(pc: PortCtx) -> pd.DataFrame:
    """Same total exposure as the traded rule each day, allocated in proportion to 1 / volatility."""
    base = pc.base()
    inv = pc.frame(lambda c: 1 / c.sizing_vol().where(c.sizing_vol() > 0))
    alloc = inv.div(inv.sum(axis=1), axis=0)
    return alloc.mul(base.sum(axis=1), axis=0).clip(upper=1.0)


def cov_risk_target(pc: PortCtx, target: float = 0.12, window: int = 126) -> pd.DataFrame:
    """Inverse-vol allocation scaled so the portfolio's forecast volatility (126-day covariance) equals 12%,
    never above full investment. Covariance re-estimated every 21 days."""
    rets = pd.DataFrame({t: c.close.pct_change(fill_method=None) for t, c in pc.ctxs.items()}).reindex(pc.index)
    inv = pc.frame(lambda c: 1 / c.sizing_vol().where(c.sizing_vol() > 0))
    alloc = inv.div(inv.sum(axis=1), axis=0)
    out = pd.DataFrame(np.nan, index=pc.index, columns=pc.tickers)
    lev = np.nan
    for i in range(window, len(pc.index)):
        if (i - window) % 21 == 0 or not np.isfinite(lev):
            cov = rets.iloc[i - window + 1 : i + 1].cov().to_numpy() * 252
        a = alloc.iloc[i].to_numpy(float)
        if not np.isfinite(a).all():
            continue
        pv = float(np.sqrt(max(a @ cov @ a, 1e-12)))
        lev = min(1.0, target / pv)
        out.iloc[i] = a * lev
    return out


@dataclass
class PVariant:
    exp: str
    name: str
    description: str
    target: Callable[[PortCtx], pd.DataFrame]
    overlay: Callable[[], Callable] | None = None  # factory: fresh state per simulation
    schedule: str | None = None  # None = as configured
    trial: bool = True
    initial_only: bool = False  # target used on the first day only (buy & hold)


def build_port_variants() -> list[PVariant]:
    V: list[PVariant] = []

    def add(*a, **k):
        V.append(PVariant(*a, **k))

    def per_asset(fn):  # weight function on each asset's own sleeve weight -> portfolio frame
        return lambda pc: pc.frame(lambda c: fn(c, c.weight())) * pc.sleeve

    add("BASE", "traded", "Traded rule in one account: sleeve x min(1, 15% / GVZ-adjusted vol)", lambda pc: pc.base())
    add(
        "REF",
        "buy_hold",
        "Equal amounts on day one, never rebalanced",
        lambda pc: pd.DataFrame(pc.sleeve, index=pc.index, columns=pc.tickers),
        trial=False,
        initial_only=True,
    )
    add(
        "REF",
        "equal_rebalanced",
        "Fully invested, equal weights, rebalanced when 5 pts off",
        lambda pc: pd.DataFrame(pc.sleeve, index=pc.index, columns=pc.tickers),
        trial=False,
    )
    add(
        "REF",
        "weekly",
        "Traded rule, orders after Friday's close only",
        lambda pc: pc.base(),
        schedule="weekly",
        trial=False,
    )
    add("REF", "daily", "Traded rule, orders any day", lambda pc: pc.base(), schedule="daily", trial=False)

    # EXP-032 how to enter and add
    def dca(pc):
        m = months_since_start(pc.index)
        return pc.base().mul(np.minimum(1.0, (m + 1) / 12.0), axis=0)

    add("EXP-032", "dca_12m", "Deploy the starting capital over 12 monthly steps, then as traded", dca, trial=False)
    add(
        "EXP-032",
        "add_to_winners",
        "x1.25 while above the 200-day average and up over 3 months (pyramiding)",
        per_asset(lambda c, w: w * cond_tilt(c, (c.close > sma(c.close, 200)) & (c.close.pct_change(63) > 0), TILT_UP)),
    )
    add(
        "EXP-032",
        "average_down",
        "x1.25 while more than 15% below the 1-year high (one addition, capped)",
        per_asset(lambda c, w: w * cond_tilt(c, c.close < 0.85 * c.close.rolling(252).max(), TILT_UP)),
    )
    add(
        "EXP-032",
        "buy_pullbacks",
        "x1.25 in an uptrend (above 200-day average) after a 1-sigma 10-day dip",
        per_asset(
            lambda c, w: (
                w
                * cond_tilt(
                    c,
                    (c.close > sma(c.close, 200)) & (c.close.pct_change(10) < -c.vol21 * np.sqrt(10 / 252)),
                    TILT_UP,
                )
            )
        ),
    )

    # EXP-033 stops, exits and circuit breakers
    add(
        "EXP-033",
        "trail_15pct",
        "Asset to cash for 21 days after a 15% fall from its high since entry",
        per_asset(lambda c, w: trailing_pct_weights(c, w, 0.15)),
    )
    add("EXP-033", "trail_25pct", "As trail_15pct with 25%", per_asset(lambda c, w: trailing_pct_weights(c, w, 0.25)))
    add(
        "EXP-033",
        "trend_exit_200",
        "Asset to cash while below its 200-day average",
        per_asset(lambda c, w: w * cond_tilt(c, c.close < sma(c.close, 200), 0.0)),
    )
    add(
        "EXP-033",
        "trend_half_200",
        "Half weight while below the 200-day average",
        per_asset(lambda c, w: w * cond_tilt(c, c.close < sma(c.close, 200), 0.5)),
    )
    add(
        "EXP-033",
        "trim_overextended",
        "Take profit: x0.75 while more than 20% above the 200-day average",
        per_asset(lambda c, w: w * cond_tilt(c, c.close > 1.2 * sma(c.close, 200), 0.75)),
    )
    add(
        "EXP-033",
        "breaker_15",
        "Halve everything when the account is 15% below its peak, until back within 7.5%",
        lambda pc: pc.base(),
        overlay=lambda: P.drawdown_breaker(0.15, 0.075, 0.5, 126),
    )
    add(
        "EXP-033",
        "breaker_25",
        "As breaker_15 at 25% / 12.5%",
        lambda pc: pc.base(),
        overlay=lambda: P.drawdown_breaker(0.25, 0.125, 0.5, 126),
    )
    add(
        "EXP-033",
        "weekly_loss_limit",
        "Halve everything for a week after a 5% weekly loss",
        lambda pc: pc.base(),
        overlay=lambda: P.loss_limit(5, 0.05, 0.5, 5),
    )
    add(
        "EXP-033",
        "equity_curve_filter",
        "Halve everything while the account is below its 100-day average",
        lambda pc: pc.base(),
        overlay=lambda: P.equity_curve_filter(100, 0.5),
    )

    # EXP-034 how much to invest
    add(
        "EXP-034",
        "fixed_weights",
        "No volatility sizing: each asset fixed at 60% of its sleeve",
        lambda pc: pd.DataFrame(pc.sleeve * 0.6, index=pc.index, columns=pc.tickers),
    )
    add(
        "EXP-034",
        "inverse_vol_alloc",
        "Same total exposure as traded, allocated by 1 / volatility",
        inverse_vol_same_gross,
    )
    add(
        "EXP-034",
        "portfolio_vol_12",
        "Inverse-vol allocation scaled to 12% forecast portfolio volatility (covariance)",
        cov_risk_target,
    )
    add(
        "EXP-034",
        "miners_cap_40",
        "Miners together at most 40% of the account",
        lambda pc: cap_group(pc.base(), MINER_GROUP, 0.40),
    )
    add("EXP-034", "cash_reserve_10", "Always keep 10% more in cash (all targets x0.9)", lambda pc: pc.base() * 0.9)

    def ff_atr(c, w):
        # portfolio weight = 0.5% of equity / stop distance (2 ATR, as a fraction of price); per sleeve: / sleeve
        size = (0.005 / (2 * c.atr / c.close) / c.shared["_sleeve"]).clip(upper=1.0)
        return chandelier_weights(c, size.fillna(0.0), mult=2.0, cooldown=10)

    add(
        "EXP-034",
        "fixed_fractional_atr",
        "Risk 0.5% of the account per asset to a 2-ATR trailing stop",
        per_asset(ff_atr),
    )

    # EXP-035 risk levels (conservative / moderate / aggressive), descriptive
    for name, tv in (("conservative_10", 0.10), ("aggressive_20", 0.20)):
        add(
            "EXP-035",
            name,
            f"Traded rule with a {tv:.0%} volatility target",
            lambda pc, tv=tv: pc.base(tv),
            trial=False,
        )
    return V


# ---------------------------------------------------------------------------
# extra statistics requested by the brief (all from daily returns)
# ---------------------------------------------------------------------------
def extra_stats(ret: pd.Series) -> dict:
    r = ret.dropna()
    if len(r) < 30:
        return {}
    m = (1 + r).groupby([r.index.year, r.index.month]).prod() - 1
    gains, losses = m[m > 0], m[m <= 0]
    eq = (1 + r).cumprod()
    dd = eq / eq.cummax() - 1
    under = (dd < 0).astype(int)
    # longest stretch below a previous peak, in trading days
    runs = under.groupby((under != under.shift()).cumsum()).sum()
    q = r.quantile(0.05)
    return {
        "months_positive": float((m > 0).mean()),
        "profit_factor_monthly": float(gains.sum() / -losses.sum()) if len(losses) and losses.sum() < 0 else np.nan,
        "avg_up_month": float(gains.mean()) if len(gains) else np.nan,
        "avg_down_month": float(losses.mean()) if len(losses) else np.nan,
        "worst_month": float(m.min()),
        "worst_day": float(r.min()),
        "cvar_5_daily": float(r[r <= q].mean()),
        "longest_underwater_days": int(runs.max()) if len(runs) else 0,
        "time_underwater": float(under.mean()),
    }


def rolling_window_returns(ret: pd.Series, days: int) -> pd.Series:
    eq = (1 + ret.fillna(0)).cumprod()
    return (eq / eq.shift(days) - 1).dropna()
