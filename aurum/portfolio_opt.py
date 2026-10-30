"""Portfolio-aware allocation (platform phase 5): look at the whole portfolio before adding anything.

Holdings come from the Alpaca paper account (phase 7) and/or manual entries (anything held elsewhere, e.g. a UK
fund), each with quantity, average price, currency and asset class. From daily returns this module measures the
portfolio (value, weights, volatility, correlations, concentration, risk contribution per holding, exposure by asset
class and sector), checks a candidate against it (diversifies? duplicates? too concentrated?), and builds target
weights with four methods that are shown side by side, because each rests on different assumptions:

  volatility targeting   inverse-volatility weights scaled to a target volatility; ignores correlations
  risk parity            equal risk contribution from each holding; uses correlations, no return forecasts
  maximum diversification maximises (weighted average volatility / portfolio volatility)
  mean-variance          maximises return - risk aversion x variance, with shrunk covariance; very sensitive to the
                         expected returns, which here are only a weak tilt from scores (labelled as such)

All methods are long-only, respect a cap per position and per sector, and may leave cash. Cash is the answer when
nothing attractive is available. Nothing here places an order.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import minimize

TRADING_DAYS = 252
LIMITS = {
    "max_stock": 0.10,  # one company at most 10% of a pot
    "max_etf": 0.25,  # one broad fund at most 25%
    "max_sector": 0.30,
    "duplicate_corr": 0.90,  # a candidate this correlated with a holding duplicates it
    "target_vol": 0.15,
}


@dataclass
class Holding:
    symbol: str
    quantity: float
    avg_price: float
    currency: str = "USD"
    asset_class: str = "stock"  # stock, etf, commodity etf, bond etf, cash-like, other
    sector: str | None = None
    source: str = "manual"  # "alpaca" or "manual"


@dataclass
class PortfolioView:
    value: float
    cash: float
    weights: pd.Series
    volatility: float | None
    risk_contribution: pd.Series
    by_asset_class: pd.Series
    by_sector: pd.Series
    concentration: float  # effective number of holdings (1 / sum of squared weights)
    correlations: pd.DataFrame
    notes: list[str] = field(default_factory=list)


def shrunk_cov(returns: pd.DataFrame) -> pd.DataFrame:
    """Ledoit-Wolf style shrinkage towards a constant-correlation target (stabler than the raw sample)."""
    r = returns.dropna(how="all").fillna(0.0)
    s = r.cov().to_numpy() * TRADING_DAYS
    sd = np.sqrt(np.diag(s))
    corr = s / np.outer(sd, sd)
    n = len(sd)
    avg = (corr.sum() - n) / max(n * (n - 1), 1)
    target = avg * np.outer(sd, sd)
    np.fill_diagonal(target, np.diag(s))
    shrink = 0.3
    return pd.DataFrame((1 - shrink) * s + shrink * target, index=returns.columns, columns=returns.columns)


def view(
    holdings: list[Holding],
    prices: dict[str, float],
    cash: float,
    returns: pd.DataFrame | None,
    fx_usd_per_gbp: float = 1.0,
) -> PortfolioView:
    """Everything in dollars (GBP holdings converted at the given rate)."""
    vals = {}
    for h in holdings:
        px = prices.get(h.symbol, h.avg_price)
        v = h.quantity * px
        vals[h.symbol] = v * (fx_usd_per_gbp if h.currency == "GBP" else 1.0)
    total = sum(vals.values()) + cash
    w = pd.Series(vals, dtype=float) / total if total > 0 else pd.Series(dtype=float)
    notes = []
    vol, rc, corr = None, pd.Series(dtype=float), pd.DataFrame()
    if returns is not None and len(w):
        cols = [s for s in w.index if s in returns.columns]
        missing = sorted(set(w.index) - set(cols))
        if missing:
            notes.append(f"No price history for {', '.join(missing)}: left out of the risk figures")
        if cols:
            cov = shrunk_cov(returns[cols].tail(TRADING_DAYS))
            ww = w[cols].to_numpy()
            pv = float(ww @ cov.to_numpy() @ ww)
            vol = float(np.sqrt(pv))
            rc = pd.Series(ww * (cov.to_numpy() @ ww) / pv if pv > 0 else 0, index=cols)
            corr = returns[cols].tail(TRADING_DAYS).corr()
    ac = pd.Series({h.symbol: h.asset_class for h in holdings})
    sec_ = pd.Series({h.symbol: h.sector or "unknown" for h in holdings})
    by_ac = w.groupby(ac.reindex(w.index)).sum() if len(w) else pd.Series(dtype=float)
    by_sector = w.groupby(sec_.reindex(w.index)).sum() if len(w) else pd.Series(dtype=float)
    if total > 0:
        by_ac = pd.concat([by_ac, pd.Series({"cash": cash / total})])
    eff = float(1 / (w**2).sum()) if len(w) and (w**2).sum() > 0 else 0.0
    for s, x in w.items():
        cap = LIMITS["max_stock"] if ac.get(s) == "stock" else LIMITS["max_etf"]
        if x > cap:
            notes.append(f"{s} is {x:.0%} of the portfolio (limit {cap:.0%})")
    for s, x in by_sector.items():
        if s != "unknown" and x > LIMITS["max_sector"]:
            notes.append(f"Sector {s} is {x:.0%} (limit {LIMITS['max_sector']:.0%})")
    return PortfolioView(total, cash, w, vol, rc, by_ac, by_sector, eff, corr, notes)


def check_candidate(
    pv: PortfolioView,
    symbol: str,
    returns: pd.DataFrame,
    add_weight: float,
    asset_class: str = "stock",
    sector: str | None = None,
) -> dict:
    """What adding `add_weight` of `symbol` (funded from cash) would do. Verdict: ok / duplicate / too concentrated /
    no cash / no data."""
    out = {"symbol": symbol, "add_weight": add_weight, "problems": [], "notes": []}
    if symbol not in returns.columns:
        out["problems"].append("no price history")
        out["verdict"] = "no data"
        return out
    cash_w = pv.cash / pv.value if pv.value else 0.0
    if add_weight > cash_w + 1e-9:
        out["problems"].append(f"needs {add_weight:.0%} of the portfolio but only {cash_w:.0%} is cash")
    cap = LIMITS["max_stock"] if asset_class == "stock" else LIMITS["max_etf"]
    now_w = float(pv.weights.get(symbol, 0.0))
    if now_w + add_weight > cap + 1e-9:
        out["problems"].append(f"would be {now_w + add_weight:.0%} of the portfolio (limit {cap:.0%})")
    if sector and pv.by_sector.get(sector, 0) + add_weight > LIMITS["max_sector"] + 1e-9:
        out["problems"].append(f"sector {sector} would exceed {LIMITS['max_sector']:.0%}")
    held = [s for s in pv.weights.index if s in returns.columns and s != symbol]
    if held:
        c = returns[held + [symbol]].tail(TRADING_DAYS).corr()[symbol].drop(symbol)
        out["max_corr"] = (str(c.idxmax()), float(c.max()))
        if c.max() >= LIMITS["duplicate_corr"]:
            out["problems"].append(f"moves almost exactly like {c.idxmax()} (correlation {c.max():.2f}): a duplicate")
        w_old = pv.weights[held]
        w_new = pd.concat([w_old, pd.Series({symbol: add_weight})])
        cov = shrunk_cov(returns[list(w_new.index)].tail(TRADING_DAYS))
        v_old = float(np.sqrt(w_old.to_numpy() @ cov.loc[held, held].to_numpy() @ w_old.to_numpy()))
        v_new = float(np.sqrt(w_new.to_numpy() @ cov.to_numpy() @ w_new.to_numpy()))
        port = (returns[held].tail(TRADING_DAYS) * w_old / max(w_old.sum(), 1e-9)).sum(axis=1)
        out["corr_with_portfolio"] = float(returns[symbol].tail(TRADING_DAYS).corr(port))
        out["vol_before"], out["vol_after"] = v_old, v_new
        out["notes"].append(
            f"Correlation with the portfolio {out['corr_with_portfolio']:+.2f}; portfolio volatility "
            f"{v_old:.1%} -> {v_new:.1%}"
        )
        if out["corr_with_portfolio"] < 0.3:
            out["notes"].append("Diversifies: moves differently from what is held")
    out["verdict"] = (
        "ok" if not out["problems"] else ("duplicate" if any("duplicate" in p for p in out["problems"]) else "blocked")
    )
    return out


# ---------------------------------------------------------------------------------------------------------------
# allocation methods
# ---------------------------------------------------------------------------------------------------------------
def _caps(symbols: list[str], kinds: dict[str, str]) -> np.ndarray:
    return np.array([LIMITS["max_stock"] if kinds.get(s, "stock") == "stock" else LIMITS["max_etf"] for s in symbols])


def _clip_to_caps(w: np.ndarray, caps: np.ndarray, budget: float) -> np.ndarray:
    """Scale to the budget, cap each weight, and leave the excess as cash (never redistributed past a cap)."""
    w = np.maximum(w, 0)
    w = w / w.sum() * budget if w.sum() > 0 else w
    return np.minimum(w, caps)


def vol_target(cov: pd.DataFrame, caps: np.ndarray, budget: float) -> np.ndarray:
    sd = np.sqrt(np.diag(cov.to_numpy()))
    w = _clip_to_caps(1 / sd, caps, budget)
    pv = float(np.sqrt(w @ cov.to_numpy() @ w))
    if pv > LIMITS["target_vol"]:
        w = w * LIMITS["target_vol"] / pv  # the rest stays in cash
    return w


def _scale_up(w: np.ndarray, caps: np.ndarray, budget: float) -> np.ndarray:
    """Grow a mix uniformly until the budget or the first cap is reached (keeps its shape; the rest is cash)."""
    w = np.maximum(w, 0)
    if w.sum() <= 0:
        return w
    room = min(budget / w.sum(), min(c / x for c, x in zip(caps, w) if x > 1e-12))
    return w * room


def _shape(obj, n: int, caps: np.ndarray, budget: float) -> np.ndarray:
    """Optimise the mix with at least half the budget invested, then scale up within the caps. Risk parity and
    maximum diversification are scale-free, so this finds their best mix even when the caps leave cash."""
    hi = min(budget, caps.sum())
    res = minimize(
        obj,
        np.minimum(np.full(n, hi / n), caps),
        bounds=[(0, c) for c in caps],
        constraints=[
            {"type": "ineq", "fun": lambda x: hi - x.sum()},
            {"type": "ineq", "fun": lambda x: x.sum() - hi / 2},
        ],
        method="SLSQP",
    )
    return _scale_up(res.x, caps, budget)


def risk_parity(cov: pd.DataFrame, caps: np.ndarray, budget: float) -> np.ndarray:
    s = cov.to_numpy()

    def obj(x):
        rc = x * (s @ x)
        tot = rc.sum()
        return float((((rc / tot) - 1 / len(x)) ** 2).sum()) * 1e4 if tot > 0 else 1e9

    return _shape(obj, len(s), caps, budget)


def max_diversification(cov: pd.DataFrame, caps: np.ndarray, budget: float) -> np.ndarray:
    s = cov.to_numpy()
    sd = np.sqrt(np.diag(s))

    def obj(x):
        return -float(x @ sd / np.sqrt(max(x @ s @ x, 1e-12)))

    return _shape(obj, len(s), caps, budget)


def mean_variance(
    cov: pd.DataFrame, expected: np.ndarray, caps: np.ndarray, budget: float, risk_aversion: float = 4.0
) -> np.ndarray:
    s = cov.to_numpy()

    def obj(x):
        return -float(x @ expected - 0.5 * risk_aversion * x @ s @ x)

    n = len(s)
    res = minimize(
        obj,
        np.full(n, budget / n),
        bounds=[(0, c) for c in caps],
        constraints=[{"type": "ineq", "fun": lambda x: budget - x.sum()}],
        method="SLSQP",
    )
    return np.maximum(res.x, 0)


def compare(
    returns: pd.DataFrame,
    candidates: list[str],
    kinds: dict[str, str],
    budget: float = 1.0,
    scores: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Target weights from all four methods for the same candidates, plus each result's expected volatility and
    diversification ratio. `scores` (0-100) tilt mean-variance only: a weak, labelled guess, not a forecast."""
    if not candidates:
        return pd.DataFrame()
    cov = shrunk_cov(returns[candidates].tail(TRADING_DAYS))
    caps = _caps(candidates, kinds)
    sd = np.sqrt(np.diag(cov.to_numpy()))
    sc = np.array([(scores or {}).get(s, 50.0) for s in candidates])
    expected = 0.02 + 0.06 * (sc - 50) / 50 * sd  # +-6% x volatility at the score extremes: deliberately modest
    out = {
        "volatility targeting": vol_target(cov, caps, budget),
        "risk parity": risk_parity(cov, caps, budget),
        "maximum diversification": max_diversification(cov, caps, budget),
        "mean-variance (score tilt)": mean_variance(cov, expected, caps, budget),
    }
    t = pd.DataFrame(out, index=candidates)
    s = cov.to_numpy()
    stats = {}
    for m, w in out.items():
        pv = float(np.sqrt(w @ s @ w))
        stats[m] = {
            "invested": w.sum(),
            "cash": budget - w.sum(),
            "volatility": pv,
            "diversification ratio": float(w @ sd / pv) if pv > 0 else np.nan,
        }
    return pd.concat([t, pd.DataFrame(stats)])
