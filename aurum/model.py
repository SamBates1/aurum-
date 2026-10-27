"""Direction model with walk-forward (out-of-sample) evaluation.

Validation design
  * Expanding-window walk-forward: train on everything before a test block,
    predict the block, move forward `step` days, repeat. No random splits.
  * Purging: a label at day s uses prices up to s + horizon. Training rows
    whose label window reaches into the test block are dropped (the last
    `horizon` rows before it). Because training never includes data after the
    test block, no extra embargo is needed in this expanding design.
  * Overlapping labels: consecutive 5-day labels share 4 days, so daily
    predictions are not independent. Uncertainty is therefore estimated with
    a block bootstrap (see stats.py), not with i.i.d. formulas.
  * The model has no preprocessing to fit (trees are scale-invariant) and no
    hyperparameter search; parameters are fixed a priori below.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    confusion_matrix,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)

MODEL_PARAMS = dict(max_depth=3, learning_rate=0.05, max_iter=150, l2_regularization=1.0, min_samples_leaf=50)


def make_model(random_state: int = 0) -> HistGradientBoostingClassifier:
    # Shallow trees + strong regularisation: daily returns are mostly noise.
    return HistGradientBoostingClassifier(**MODEL_PARAMS, random_state=random_state)


def usable(X: pd.DataFrame, y: pd.Series | None = None):
    """Rows with every feature present (and a label, if y given)."""
    mask = X.notna().all(axis=1)
    if y is not None:
        mask &= y.notna()
        return X.loc[mask], y.loc[mask].astype(int)
    return X.loc[mask]


@dataclass
class WalkForward:
    probs: pd.Series  # out-of-sample P(up), NaN where no prediction was possible
    folds: pd.DataFrame  # one row per retrain: dates, sizes, fold AUC


def walk_forward(
    X: pd.DataFrame, y: pd.Series, horizon: int, min_train: int = 756, step: int = 63, random_state: int = 0
) -> WalkForward:
    Xv, yv = usable(X, y)
    Xall = usable(X)  # includes the latest rows whose labels aren't known yet
    probs = pd.Series(np.nan, index=X.index, name="prob_up")
    folds = []
    if len(Xv) <= min_train:
        return WalkForward(probs, pd.DataFrame(folds))
    for start in range(min_train, len(Xv), step):
        test_start = Xv.index[start]
        train_end = start - horizon  # purge: these labels would overlap the test block
        ytr = yv.iloc[:train_end]
        if ytr.nunique() < 2:
            continue
        model = make_model(random_state).fit(Xv.iloc[:train_end], ytr)
        nxt = Xv.index[start + step] if start + step < len(Xv) else None
        block = Xall.loc[test_start:] if nxt is None else Xall.loc[test_start:nxt].iloc[:-1]
        probs.loc[block.index] = model.predict_proba(block)[:, 1]
        yb = y.reindex(block.index).dropna()
        pb = probs.reindex(yb.index)
        folds.append(
            {
                "train_start": Xv.index[0],
                "train_end": Xv.index[train_end - 1],
                "test_start": block.index[0],
                "test_end": block.index[-1],
                "n_train": train_end,
                "n_test": len(block),
                "auc": roc_auc_score(yb, pb) if yb.nunique() == 2 else np.nan,
            }
        )
    return WalkForward(probs, pd.DataFrame(folds))


def fit_final(X: pd.DataFrame, y: pd.Series, random_state: int = 0) -> HistGradientBoostingClassifier:
    """Fit on all labelled history (every label is realised) for live predictions."""
    Xv, yv = usable(X, y)
    if yv.nunique() < 2:
        raise ValueError("cannot fit: labels have a single class")
    return make_model(random_state).fit(Xv, yv)


def predict_row(model, X: pd.DataFrame) -> float:
    """P(up) for the last row of X, or NaN if any feature is missing/invalid."""
    row = X.iloc[[-1]]
    if row.isna().any(axis=None) or not np.isfinite(row.to_numpy(float)).all():
        return float("nan")
    p = float(model.predict_proba(row[model.feature_names_in_])[0, 1])
    return p if 0.0 <= p <= 1.0 else float("nan")


# ---------------------------------------------------------------------------
# diagnostics
# ---------------------------------------------------------------------------
def classification_metrics(probs: pd.Series, y: pd.Series, threshold: float = 0.5) -> dict:
    df = pd.concat([probs, y], axis=1, keys=["p", "y"]).dropna()
    if len(df) < 20 or df["y"].nunique() < 2:
        return {"n": len(df)}
    yt, p = df["y"].astype(int), df["p"].clip(1e-6, 1 - 1e-6)
    pred = (p > threshold).astype(int)
    base = yt.mean()
    tn, fp, fn, tp = confusion_matrix(yt, pred, labels=[0, 1]).ravel()
    return {
        "n": len(df),
        "auc": roc_auc_score(yt, p),
        "accuracy": accuracy_score(yt, pred),
        "base_rate": base,  # accuracy of always predicting "up"
        "precision": precision_score(yt, pred, zero_division=0),
        "recall": recall_score(yt, pred, zero_division=0),
        "brier": brier_score_loss(yt, p),
        "brier_baseline": brier_score_loss(yt, np.full(len(yt), base)),  # constant forecast at the base rate
        "log_loss": log_loss(yt, p, labels=[0, 1]),
        "log_loss_baseline": log_loss(yt, np.full(len(yt), base), labels=[0, 1]),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
    }


def calibration_table(probs: pd.Series, y: pd.Series, bins: int = 10) -> pd.DataFrame:
    df = pd.concat([probs, y], axis=1, keys=["p", "y"]).dropna()
    if df.empty:
        return pd.DataFrame(columns=["bin", "mean_pred", "freq_up", "n"])
    df["bin"] = pd.cut(df["p"], np.linspace(0, 1, bins + 1), include_lowest=True)
    out = df.groupby("bin", observed=True).agg(mean_pred=("p", "mean"), freq_up=("y", "mean"), n=("y", "size"))
    return out.reset_index()
