"""Vectorised backtest with transaction costs and a buy-and-hold benchmark."""
import numpy as np
import pandas as pd

TRADING_DAYS = 252


def positions_from_probs(probs: pd.Series, buy_prob: float, sell_prob: float, allow_short: bool = False) -> pd.Series:
    """Go long above buy_prob, exit (or short) below sell_prob, otherwise keep
    the previous position. The band in between avoids churning on noise."""
    pos = pd.Series(np.nan, index=probs.index)
    pos[probs >= buy_prob] = 1.0
    pos[probs <= sell_prob] = -1.0 if allow_short else 0.0
    pos = pos.ffill().fillna(0.0)
    pos[probs.isna()] = 0.0
    return pos


def run_backtest(prices: pd.DataFrame, probs: pd.Series, buy_prob: float = 0.55, sell_prob: float = 0.45,
                 cost_bps: float = 5, allow_short: bool = False):
    ret = prices["Close"].pct_change().fillna(0.0)
    target = positions_from_probs(probs.reindex(prices.index), buy_prob, sell_prob, allow_short)
    held = target.shift(1).fillna(0.0)  # decide at today's close, earn tomorrow's return
    turnover = held.diff().abs().fillna(held.abs())
    strat = held * ret - turnover * cost_bps / 1e4

    first = probs.first_valid_index()
    res = pd.DataFrame({"strategy": strat, "benchmark": ret, "position": held}).loc[first:]
    res["strategy_equity"] = (1 + res["strategy"]).cumprod()
    res["benchmark_equity"] = (1 + res["benchmark"]).cumprod()
    summary = pd.DataFrame({"Strategy": metrics(res["strategy"], res["position"]),
                            "Buy & hold": metrics(res["benchmark"], pd.Series(1.0, index=res.index))})
    return res, summary


def metrics(r: pd.Series, position: pd.Series | None = None) -> dict:
    r = r.dropna()
    if len(r) < 2:
        return {}
    equity = (1 + r).cumprod()
    years = len(r) / TRADING_DAYS
    vol = r.std() * np.sqrt(TRADING_DAYS)
    downside = r[r < 0].std() * np.sqrt(TRADING_DAYS)
    drawdown = equity / equity.cummax() - 1
    out = {
        "CAGR": equity.iloc[-1] ** (1 / years) - 1,
        "Volatility": vol,
        "Sharpe": r.mean() * TRADING_DAYS / vol if vol else np.nan,
        "Sortino": r.mean() * TRADING_DAYS / downside if downside else np.nan,
        "Max drawdown": drawdown.min(),
        "Hit rate": (r[r != 0] > 0).mean(),
    }
    if position is not None:
        out["Time in market"] = (position.reindex(r.index) != 0).mean()
    return out
