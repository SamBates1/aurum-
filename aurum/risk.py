"""Independent risk engine (master build prompt: risk checks that a strategy cannot switch off).

The strategy proposes target weights; this module reviews them against limits that live in config.yaml under `risk:`
(changing them needs the owner's approval, like any production setting). It can only REDUCE risk: cut a target,
block a purchase, or halt new buying. It never raises a target or adds an order. Every veto is returned with a reason
and written to the decision log by the paper trader.

Limits (defaults in RISK_DEFAULTS):
  allowed_assets            only these tickers may be held (liquid, US-listed ETFs from the research universe)
  max_gross                 total invested share of the account (1.0 = no borrowing)
  max_weight_per_asset      cap on any one asset's share of the account
  max_turnover_per_day      cap on the total value traded in one day, as a share of the account
  account_drawdown_halt     if the paper account is this far below its peak, block all purchases until the owner
                            reviews (sales that reduce risk are still allowed)
  vol_spike_ratio           if an asset's 21-day volatility is more than this multiple of its 1-year median, block
                            purchases of that asset (reductions still allowed)
  max_data_age_days         no orders on data older than this (calendar days)
  min_order_value           ignore orders smaller than this (dollars) to avoid dust trades
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import CFG

RISK_DEFAULTS = {
    "allowed_assets": ["SPY", "QQQ", "IWM", "EFA", "TLT", "IEF", "GLD", "SLV", "GDX", "DBC"],
    "max_gross": 1.0,
    "max_weight_per_asset": 0.85,
    "max_turnover_per_day": 1.0,
    "account_drawdown_halt": 0.35,
    "vol_spike_ratio": 4.0,
    "max_data_age_days": 4,
    "min_order_value": 25.0,
}


def limits(cfg: dict = CFG) -> dict:
    d = dict(RISK_DEFAULTS)
    d.update(cfg.get("risk", {}) or {})
    return d


@dataclass
class RiskReview:
    approved: dict[str, float]  # target weights after the review
    vetoes: list[dict] = field(default_factory=list)  # {rule, ticker, detail, action}
    halted: bool = False

    @property
    def clean(self) -> bool:
        return not self.vetoes


def static_check(spec: dict, cfg: dict = CFG) -> list[str]:
    """Problems with a strategy definition itself (used by the eligibility gate)."""
    lim = limits(cfg)
    out = []
    for t in spec["universe"]:
        if t not in lim["allowed_assets"]:
            out.append(f"{t} is not on the risk engine's allowed list")
    for t, w in spec["base_weights"].items():
        if w > lim["max_weight_per_asset"] + 1e-9:
            out.append(f"{t} base weight {w:.0%} is above the {lim['max_weight_per_asset']:.0%} per-asset limit")
    if sum(spec["base_weights"].values()) > lim["max_gross"] + 1e-9:
        out.append("base weights add up to more than the gross limit")
    return out


def review(
    targets: dict[str, float],
    current: dict[str, float],
    *,
    equity: float,
    peak_equity: float,
    closes: dict[str, pd.Series],
    data_age_days: float,
    cfg: dict = CFG,
) -> RiskReview:
    """Review proposed account weights against the limits. `current` = weights held now; `closes` = completed daily
    closes per asset (for the volatility-spike rule)."""
    lim = limits(cfg)
    out = {t: max(0.0, float(w)) for t, w in targets.items()}
    vetoes = []

    def veto(rule, ticker, detail, action):
        vetoes.append({"rule": rule, "ticker": ticker, "detail": detail, "action": action})

    if data_age_days > lim["max_data_age_days"]:
        veto(
            "data_age",
            "*",
            f"latest completed bar is {data_age_days:.0f} days old (limit {lim['max_data_age_days']})",
            "no orders",
        )
        return RiskReview(dict(current), vetoes, halted=True)
    for t in list(out):
        if t not in lim["allowed_assets"]:
            veto("allowed_assets", t, f"{t} is not on the allowed list", "target set to 0")
            out[t] = 0.0
        if out[t] > lim["max_weight_per_asset"]:
            veto(
                "max_weight_per_asset",
                t,
                f"target {out[t]:.0%} above limit {lim['max_weight_per_asset']:.0%}",
                "cut to limit",
            )
            out[t] = lim["max_weight_per_asset"]
    gross = sum(out.values())
    if gross > lim["max_gross"] + 1e-9:
        veto("max_gross", "*", f"targets add up to {gross:.0%} (limit {lim['max_gross']:.0%})", "scaled down")
        out = {t: w * lim["max_gross"] / gross for t, w in out.items()}
    dd = equity / peak_equity - 1 if peak_equity > 0 else 0.0
    halted = dd < -lim["account_drawdown_halt"]
    for t, w in list(out.items()):
        cur = float(current.get(t, 0.0))
        if w <= cur:
            continue  # reductions are always allowed
        if halted:
            veto(
                "account_drawdown_halt",
                t,
                f"paper account {dd:.0%} below its peak (limit {-lim['account_drawdown_halt']:.0%}): "
                "purchases need owner review",
                "purchase blocked",
            )
            out[t] = cur
            continue
        c = closes.get(t)
        if c is not None and len(c) > 260:
            v = c.pct_change(fill_method=None).rolling(21).std() * np.sqrt(252)
            med = v.iloc[-252:].median()
            if np.isfinite(v.iloc[-1]) and med > 0 and v.iloc[-1] > lim["vol_spike_ratio"] * med:
                veto(
                    "vol_spike",
                    t,
                    f"21-day volatility {v.iloc[-1]:.0%} is over {lim['vol_spike_ratio']:g}x its 1-year median "
                    f"({med:.0%})",
                    "purchase blocked",
                )
                out[t] = cur
    turnover = sum(abs(out[t] - float(current.get(t, 0.0))) for t in out)
    if turnover > lim["max_turnover_per_day"] + 1e-9:
        veto(
            "max_turnover_per_day",
            "*",
            f"planned trading {turnover:.0%} of the account (limit {lim['max_turnover_per_day']:.0%})",
            "moves scaled down",
        )
        f = lim["max_turnover_per_day"] / turnover
        out = {t: float(current.get(t, 0.0)) + f * (w - float(current.get(t, 0.0))) for t, w in out.items()}
    return RiskReview(out, vetoes, halted)
