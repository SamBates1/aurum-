"""Comparison strategies, all run through the same simulator, dates and costs.

cash            uninvested, earning the T-bill rate
buy_hold        100% invested from the first day, no stops (the passive alternative)
vol_sized_hold  always invested with the strategy's volatility sizing (no stops,
                no timing): isolates the value of *timing* from the value of sizing
sma_trend       long when price > 200-day average (classic trend following)
momentum        long when the 12-month return excluding the last month is positive
technical_only  the strategy's technical rule with no ML
ml_only         the ML vote alone, full feature set, no skill weighting
ml_no_macro     the ML vote alone, trained on technical features only (ablation)
strategy        the traded composite
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import strategy as S


def score_to_decisions(score: pd.Series, scfg: dict) -> pd.Series:
    return S.decisions(score, scfg["buy_above"], scfg["sell_below"])


def sma_trend_score(close: pd.Series, n: int = 200) -> pd.Series:
    sma = close.rolling(n).mean()
    return pd.Series(np.where(close > sma, 1.0, -1.0), close.index).where(sma.notna())


def momentum_score(close: pd.Series, lookback: int = 252, skip: int = 21) -> pd.Series:
    mom = close.shift(skip) / close.shift(lookback) - 1
    return pd.Series(np.where(mom > 0, 1.0, -1.0), close.index).where(mom.notna())


def run_all(
    prices: pd.DataFrame,
    features: pd.DataFrame,
    strategy_score: pd.Series,
    prob_full: pd.Series,
    prob_tech: pd.Series | None,
    atr: pd.Series,
    rf: pd.Series,
    scfg: dict,
    cost_bps: float,
    start,
) -> dict[str, S.SimResult]:
    """Simulate every comparison over prices.loc[start:]."""
    p = prices.loc[start:]
    vol = features["vol_21"]
    common = dict(cost_bps=cost_bps, cash_rate=rf, target_vol=scfg["target_vol"], stop_atr_mult=scfg["stop_atr_mult"])

    def sized(score):
        return S.simulate(p, score_to_decisions(score.loc[start:], scfg), vol, atr, **common)

    always = pd.Series(S.BUY, index=p.index, dtype=object)
    out = {
        "strategy": sized(strategy_score),
        "buy_hold": S.simulate(
            p, always, vol, atr, cost_bps=cost_bps, cash_rate=rf, stop_atr_mult=None, fixed_exposure=1.0
        ),
        "vol_sized_hold": S.simulate(
            p, always, vol, atr, cost_bps=cost_bps, cash_rate=rf, target_vol=scfg["target_vol"], stop_atr_mult=None
        ),
        "cash": S.simulate(p, pd.Series(S.HOLD, index=p.index, dtype=object), vol, atr, **common),
        "sma_trend": sized(sma_trend_score(prices["Close"])),
        "momentum": sized(momentum_score(prices["Close"])),
        "technical_only": sized(S.technical_score(features)),
        "ml_only": sized(S.ml_score(prob_full)),
    }
    if prob_tech is not None:
        out["ml_no_macro"] = sized(S.ml_score(prob_tech))
    return out
