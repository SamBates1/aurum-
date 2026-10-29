"""Glue between data, model and strategy.

research()  slow, run once a day: walk-forward model, point-in-time skill,
            backtest of the traded strategy, final model for live use.
decide()    fast, run on every refresh: rebuilds features from the latest
            completed bars (never reuses stale ones), predicts with the final
            model, and applies exactly the same scoring rule as the backtest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd

from . import data, model, sentiment, signals
from . import strategy as S
from .backtest import performance
from .config import CFG, all_tickers, cost_bps, is_equity
from .features import atr as atr_fn
from .features import build_dataset


@dataclass
class Research:
    ticker: str
    prices: pd.DataFrame
    macro: pd.DataFrame
    rf: pd.Series
    X: pd.DataFrame
    y: pd.Series
    groups: dict
    wf: model.WalkForward
    auc_pit: pd.Series
    score: pd.Series
    sim: S.SimResult
    perf: dict
    final_model: object
    feature_cols: list
    eval_start: pd.Timestamp
    built_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


def research(
    ticker: str, macro: pd.DataFrame | None = None, cfg: dict = CFG, feature_groups: tuple[str, ...] | None = None
) -> Research:
    mcfg, scfg = cfg["model"], cfg["strategy"]
    prices = data.daily_prices(ticker, cfg=cfg)
    if len(prices) < cfg["data"]["min_history_days"]:
        raise data.DataError(f"{ticker}: {len(prices)} days of history, need {cfg['data']['min_history_days']}")
    macro = data.macro_daily(cfg) if macro is None else macro
    X, y, _, groups = build_dataset(prices, macro, mcfg["horizon_days"], mcfg["threshold"])
    if feature_groups:
        X = X[[c for g in feature_groups for c in groups.get(g, [])]]
    wf = model.walk_forward(
        X, y, mcfg["horizon_days"], mcfg["min_train_days"], mcfg["retrain_every_days"], mcfg.get("random_state", 0)
    )
    if wf.probs.notna().sum() == 0:
        raise data.DataError(f"{ticker}: not enough clean history for any out-of-sample prediction")
    auc_pit = S.rolling_auc(wf.probs, y, mcfg["horizon_days"], scfg["ml_skill_min_obs"])
    score = S.strategy_score(X, wf.probs, auc_pit, scfg)
    eval_start = wf.probs.first_valid_index()
    rf = data.cash_rate(prices.index, cfg)
    atr = atr_fn(prices)
    if scfg.get("mode", "timing") == "vol_hold":  # always invested, sized by volatility (EXP-014)
        sim = S.simulate_weights(
            prices.loc[eval_start:],
            S.vol_target_weight(X["vol_21"], scfg["target_vol"]).loc[eval_start:],
            cost_bps=cost_bps(ticker, cfg),
            cash_rate=rf,
            band=scfg.get("rebalance_band", 0.05),
            fill=scfg.get("fill", "open"),
        )
    else:
        sim = S.simulate(
            prices.loc[eval_start:],
            S.decisions(score, scfg["buy_above"], scfg["sell_below"]),
            X["vol_21"],
            atr,
            cost_bps=cost_bps(ticker, cfg),
            cash_rate=rf,
            target_vol=scfg["target_vol"],
            rules=S.rules_from_config(scfg),
        )
    return Research(
        ticker=ticker,
        prices=prices,
        macro=macro,
        rf=rf,
        X=X,
        y=y,
        groups=groups,
        wf=wf,
        auc_pit=auc_pit,
        score=score,
        sim=sim,
        perf=performance(sim, rf),
        final_model=model.fit_final(X, y, mcfg.get("random_state", 0)),
        feature_cols=list(X.columns),
        eval_start=eval_start,
    )


@dataclass
class Decision:
    ticker: str
    decision: str  # BUY / SELL / HOLD
    score: float
    components: dict  # name -> {score, weight, reasons}
    prob_up: float
    auc: float
    skill: float
    bars: pd.DataFrame  # price bars the decision was based on
    features: pd.DataFrame
    last_price: float  # latest traded price (for marking and paper fills)
    ann_vol: float
    atr: float
    tradeable: bool  # False when data is stale or invalid: never trade on it
    sentiment: dict
    fundamentals: dict
    notes: list[str]
    as_of: str
    target_weight: float | None = None  # vol_hold mode: share of the sleeve to hold in the asset


def decide(
    ticker: str,
    res: Research,
    cfg: dict = CFG,
    prices: pd.DataFrame | None = None,
    live_price: float | None = None,
    now: datetime | None = None,
    context: bool = True,
) -> Decision:
    mcfg, scfg = cfg["model"], cfg["strategy"]
    notes: list[str] = []
    prices = res.prices if prices is None else prices
    bars = prices if cfg["live"].get("use_partial_bar") else data.completed_bars(prices, now)
    if cfg["live"].get("use_partial_bar"):
        notes.append("Using today's partial bar: this behaviour is NOT what was backtested.")

    # Fresh features from the latest bars (the old bot reused the morning's features).
    X, *_ = build_dataset(bars, res.macro, mcfg["horizon_days"], mcfg["threshold"])
    X = X.reindex(columns=res.feature_cols)
    row = X.iloc[-1]
    prob = model.predict_row(res.final_model, X)
    known_auc = res.auc_pit.loc[: bars.index[-1]].dropna()  # skill as known on the decision date
    auc = float(known_auc.iloc[-1]) if len(known_auc) else float("nan")
    skill = float(S.skill_from_auc(auc, scfg["ml_auc_floor"], scfg["ml_auc_full"])) if np.isfinite(auc) else 0.0

    w = scfg["weights"]
    tech = float(S.technical_score(X.iloc[[-1]]).iloc[0])
    comps = {
        "ml": (S.ml_score(prob), w["ml"] * skill, signals.ml_reasons(prob, auc, skill)),
        "technical": (tech, w["technical"], signals.technical_reasons(row)),
    }
    sent, fund = {"score": None, "n": 0, "headlines": []}, {}
    if context:
        sent = sentiment.headline_sentiment(data.news(ticker, cfg=cfg), cfg["signals"]["news_max_age_days"])
        fund = data.fundamentals(ticker, cfg=cfg) if is_equity(ticker, cfg) else {}
        s_score, s_reasons = signals.sentiment_score(sent)
        f_score, f_reasons = signals.fundamental_score(fund)
        comps["sentiment"] = (s_score, w.get("sentiment", 0.0), s_reasons)
        if is_equity(ticker, cfg):
            comps["fundamentals"] = (f_score, w.get("fundamentals", 0.0), f_reasons)
        if w.get("sentiment", 0) > 0 or w.get("fundamentals", 0) > 0:
            notes.append("Sentiment/fundamentals have non-zero weight: these inputs are not backtested.")

    score = S.combine({k: v[0] for k, v in comps.items()}, {k: v[1] for k, v in comps.items()})
    decision = S.decision_for(score, scfg["buy_above"], scfg["sell_below"])
    total_w = sum(v[1] for v in comps.values() if v[0] is not None and np.isfinite(v[0]))
    components = {
        k: {
            "score": v[0],
            "weight": (v[1] / total_w if total_w and v[0] is not None and np.isfinite(v[0]) else 0.0),
            "reasons": v[2],
        }
        for k, v in comps.items()
    }

    # --- safety checks: never trade silently on bad or stale data
    tradeable = True
    stale = data.staleness_days(bars, now)
    if stale > cfg["data"]["max_stale_days"]:
        tradeable = False
        notes.append(f"Latest completed bar is {stale} days old: data looks stale, no trading.")
    macro_age = (bars.index[-1] - res.macro.dropna(how="all").index[-1]).days
    if macro_age > cfg["data"]["max_stale_days"] + 3:  # FRED lag + weekends allowed for
        notes.append(f"Macro data ends {macro_age} days before prices: macro features are stale.")
    if not np.isfinite(prob):
        notes.append("Model prediction unavailable: decision uses technical signals only.")
    if not np.isfinite(score):
        tradeable, decision = False, S.HOLD
        notes.append("No valid score could be computed: HOLD, no trading.")
    if 0 < skill < 0.3:
        notes.append(
            f"Out-of-sample AUC is {auc:.2f}: the model is barely better than a coin flip, "
            f"so its vote is down-weighted to {skill:.0%}."
        )
    elif skill == 0:
        notes.append("The model has no proven out-of-sample skill for this ticker, so the ML vote is switched off.")
    price = (
        float(live_price)
        if live_price is not None and np.isfinite(live_price) and live_price > 0
        else float(prices["Close"].iloc[-1])
    )
    if not tradeable:
        decision = S.HOLD

    atr_now = float(atr_fn(bars).iloc[-1])
    target_weight = None
    if scfg.get("mode", "timing") == "vol_hold":
        # The score and its reasons are still shown as context, but in this mode the position is
        # simply min(1, target_vol / volatility) of the sleeve: the rule tested in EXP-014.
        target_weight = float(S.vol_target_weight(pd.Series([row["vol_21"]]), scfg["target_vol"]).iloc[0])
        decision = S.BUY if tradeable and target_weight > 0 else S.HOLD
        notes.insert(0, f"Always-invested mode: hold {target_weight:.0%} of this sleeve (15% volatility target).")
    return Decision(
        ticker=ticker,
        target_weight=target_weight,
        decision=decision,
        score=score,
        components=components,
        prob_up=prob,
        auc=auc,
        skill=skill,
        bars=bars,
        features=X,
        last_price=price,
        ann_vol=float(row["vol_21"]),
        atr=atr_now,
        tradeable=tradeable,
        sentiment=sent,
        fundamentals=fund,
        notes=notes,
        as_of=str(bars.index[-1].date()),
    )


def research_universe(cfg: dict = CFG) -> dict[str, Research]:
    macro = data.macro_daily(cfg)
    out = {}
    for t in all_tickers(cfg):
        try:
            out[t] = research(t, macro, cfg)
        except Exception as exc:
            data.log_event("error", t, f"research failed: {exc}")
    return out


def summary(res: Research) -> dict:
    return {"ticker": res.ticker, **res.perf, **model.classification_metrics(res.wf.probs, res.y)}
