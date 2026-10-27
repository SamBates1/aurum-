"""ML model with honest walk-forward (out-of-sample) evaluation.

Key ideas worth explaining in an interview:
  * Walk-forward: the model is only ever scored on data after its training set.
  * Purging: labels look `horizon` days ahead, so the last `horizon` training
    rows would overlap the test period. We drop them (a "purge gap").
  * Baseline: accuracy is compared with the base rate (always predicting "up").
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, roc_auc_score


def make_model() -> HistGradientBoostingClassifier:
    # Shallow trees + strong regularisation: financial data is mostly noise.
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=150,
                                          l2_regularization=1.0, min_samples_leaf=50, random_state=0)


def _usable(X: pd.DataFrame, y: pd.Series):
    mask = X.notna().all(axis=1) & y.notna()
    return X.loc[mask], y.loc[mask].astype(int)


def walk_forward(X: pd.DataFrame, y: pd.Series, horizon: int, min_train: int = 756, step: int = 63) -> pd.Series:
    """Out-of-sample P(up) for every date after the first `min_train` usable rows."""
    Xv, yv = _usable(X, y)
    probs = pd.Series(np.nan, index=X.index, name="prob_up")
    for start in range(min_train, len(Xv), step):
        train_end = start - horizon  # purge gap
        if yv.iloc[:train_end].nunique() < 2:
            continue
        model = make_model().fit(Xv.iloc[:train_end], yv.iloc[:train_end])
        test = Xv.iloc[start:start + step]
        probs.loc[test.index] = model.predict_proba(test)[:, 1]
    return probs


def oos_metrics(probs: pd.Series, y: pd.Series) -> dict:
    df = pd.concat([probs, y], axis=1, keys=["p", "y"]).dropna()
    if df.empty or df["y"].nunique() < 2:
        return {}
    pred = (df["p"] > 0.5).astype(int)
    return {
        "oos_days": len(df),
        "accuracy": accuracy_score(df["y"], pred),
        "base_rate": df["y"].mean(),       # accuracy of always saying "up"
        "auc": roc_auc_score(df["y"], df["p"]),  # 0.5 = coin flip
    }


def predict_latest(X: pd.DataFrame, y: pd.Series, horizon: int) -> float:
    """Fit on all labelled history (every label is already realised), then
    predict P(up) over the next `horizon` days for the latest bar."""
    Xv, yv = _usable(X, y)
    model = make_model().fit(Xv, yv)
    latest = X.iloc[[-1]]
    return float(model.predict_proba(latest)[0, 1])
