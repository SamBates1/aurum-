"""Glue: one call to analyse a ticker end to end. Used by the dashboard and the bot."""
from dataclasses import dataclass, field

import pandas as pd

from . import backtest, data, model, sentiment, signals
from .config import CFG, is_equity
from .features import atr, build_dataset


@dataclass
class Analysis:
    ticker: str
    prices: pd.DataFrame
    features: pd.DataFrame
    prob_up: float
    oos_probs: pd.Series
    oos_metrics: dict
    backtest: pd.DataFrame
    backtest_summary: pd.DataFrame
    sentiment: dict
    fundamentals: dict
    signal: dict
    last_price: float
    ann_vol: float
    atr: float
    notes: list[str] = field(default_factory=list)


def research(ticker: str, macro: pd.DataFrame | None = None, cfg: dict = CFG):
    """The slow part (walk-forward ML + backtest). Cache this for a few hours."""
    mcfg = cfg["model"]
    prices = data.daily_prices(ticker, cfg=cfg)
    if macro is None:
        macro = data.macro_daily(cfg)
    X, y, _ = build_dataset(prices, macro, mcfg["horizon_days"], mcfg["threshold"])
    probs = model.walk_forward(X, y, mcfg["horizon_days"], mcfg["min_train_days"], mcfg["retrain_every_days"])
    bt, summary = backtest.run_backtest(prices, probs, mcfg["buy_prob"], mcfg["sell_prob"], cfg["backtest"]["cost_bps"])
    prob_now = model.predict_latest(X, y, mcfg["horizon_days"])
    return {"prices": prices, "X": X, "y": y, "probs": probs, "prob_now": prob_now,
            "oos": model.oos_metrics(probs, y), "bt": bt, "summary": summary}


def decide(ticker: str, res: dict, cfg: dict = CFG, live_price: float | None = None) -> Analysis:
    """The fast part: refresh news and fundamentals, then combine into a decision."""
    prices, X = res["prices"], res["X"]
    row = X.iloc[-1]
    news = data.news(ticker, cfg=cfg)
    sent = sentiment.headline_sentiment(news)
    fund = data.fundamentals(ticker, cfg=cfg) if is_equity(ticker, cfg) else {}

    comps = {
        "ml": signals.ml_score(res["prob_now"]),
        "technical": signals.technical_score(row),
        "sentiment": signals.sentiment_score(sent),
        "fundamentals": signals.fundamental_score(fund),
    }
    sig = signals.combine(comps, cfg["signals"]["weights"], cfg["signals"]["buy_above"], cfg["signals"]["sell_below"])
    notes = []
    oos = res["oos"]
    if oos and oos["auc"] < 0.52:
        notes.append(f"Out-of-sample AUC is {oos['auc']:.2f}: the model is close to a coin flip for {ticker}, "
                     "so treat its vote with caution.")
    return Analysis(
        ticker=ticker, prices=prices, features=X, prob_up=res["prob_now"], oos_probs=res["probs"],
        oos_metrics=oos, backtest=res["bt"], backtest_summary=res["summary"], sentiment=sent,
        fundamentals=fund, signal=sig, last_price=float(live_price or prices["Close"].iloc[-1]),
        ann_vol=float(row["vol_21"]), atr=float(atr(prices).iloc[-1]), notes=notes,
    )


def analyse(ticker: str, macro: pd.DataFrame | None = None, cfg: dict = CFG) -> Analysis:
    return decide(ticker, research(ticker, macro, cfg), cfg)
