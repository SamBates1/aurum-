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
    scfg = cfg["signals"]
    news = data.news(ticker, cfg=cfg)
    sent = sentiment.headline_sentiment(news, scfg.get("news_max_age_days", 7))
    fund = data.fundamentals(ticker, cfg=cfg) if is_equity(ticker, cfg) else {}

    # Trust the model only as far as it has proven itself out of sample.
    oos = res["oos"]
    auc = oos.get("auc", 0.5) if oos else 0.5
    skill = signals.ml_skill(auc, scfg.get("ml_auc_floor", 0.50), scfg.get("ml_auc_full", 0.56))
    weights = dict(scfg["weights"])
    weights["ml"] = weights["ml"] * skill

    comps = {
        "ml": signals.ml_score(res["prob_now"], auc, skill),
        "technical": signals.technical_score(row),
        "sentiment": signals.sentiment_score(sent),
        "fundamentals": signals.fundamental_score(fund),
    }
    sig = signals.combine(comps, weights, scfg["buy_above"], scfg["sell_below"])
    notes = []
    if skill < 0.3:
        notes.append(f"Out-of-sample AUC is {auc:.2f}: the model is close to a coin flip for {ticker}, "
                     f"so its vote is down-weighted to {skill:.0%} of normal.")
    if sent["n"] == 0:
        notes.append("No recent headlines found, so news sentiment isn't part of this decision.")
    return Analysis(
        ticker=ticker, prices=prices, features=X, prob_up=res["prob_now"], oos_probs=res["probs"],
        oos_metrics=oos, backtest=res["bt"], backtest_summary=res["summary"], sentiment=sent,
        fundamentals=fund, signal=sig, last_price=float(live_price or prices["Close"].iloc[-1]),
        ann_vol=float(row["vol_21"]), atr=float(atr(prices).iloc[-1]), notes=notes,
    )


def analyse(ticker: str, macro: pd.DataFrame | None = None, cfg: dict = CFG) -> Analysis:
    return decide(ticker, research(ticker, macro, cfg), cfg)
