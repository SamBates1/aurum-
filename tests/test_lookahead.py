"""Look-ahead and leakage checks: the most important tests in the project."""

import numpy as np
import pandas as pd

from aurum import data, model
from aurum import strategy as S
from aurum.features import build_dataset, technical_features


def test_features_do_not_change_when_future_is_removed(gld, cfg):
    """If any feature peeked at the future, cutting the future off would change it."""
    macro = data.macro_daily(cfg)
    full, *_ = build_dataset(gld, macro, horizon=5)
    cut = 2500
    part, *_ = build_dataset(gld.iloc[:cut], macro, horizon=5)
    pd.testing.assert_frame_equal(full.iloc[:cut], part)
    pd.testing.assert_frame_equal(technical_features(gld).iloc[:cut], technical_features(gld.iloc[:cut]))


def test_labels_are_strictly_future(gld):
    X, y, fwd, _ = build_dataset(gld, None, horizon=5)
    assert y.iloc[-5:].isna().all() and y.iloc[:-5].notna().all()
    t = 100
    expected = gld["Close"].iloc[t + 5] / gld["Close"].iloc[t] - 1
    assert np.isclose(fwd.iloc[t], expected)


def test_walk_forward_predictions_unaffected_by_later_data(gld, cfg):
    """Predictions up to a fold boundary must be identical whether or not later data exists."""
    X, y, _, _ = build_dataset(gld, data.macro_daily(cfg), horizon=5)
    wf_full = model.walk_forward(X, y, 5, min_train=756, step=126)
    cut_date = wf_full.folds["test_start"].iloc[3]
    keep = X.index < cut_date
    wf_cut = model.walk_forward(X[keep], y[keep].where(y[keep].index < cut_date), 5, min_train=756, step=126)
    a = wf_full.probs[wf_full.probs.index < wf_full.folds["test_start"].iloc[3]].dropna()
    b = wf_cut.probs.reindex(a.index)
    # the last fold before the cut can only see labels known before the cut, so compare earlier folds
    early = a.index < wf_full.folds["test_start"].iloc[2]
    np.testing.assert_allclose(a[early], b[early])


def test_purge_gap_separates_train_labels_from_test(gld):
    X, y, _, _ = build_dataset(gld, None, horizon=5)
    wf = model.walk_forward(X, y, 5, min_train=756, step=126)
    idx = gld.index
    for _, f in wf.folds.iterrows():
        last_label_day = idx[idx.get_loc(f["train_end"]) + 5]  # the label of the last training row ends here
        assert last_label_day < f["test_start"]


def test_fred_values_shift_to_publication_date():
    s = pd.Series([1.0, 2.0], index=pd.to_datetime(["2024-03-07", "2024-03-08"]))  # Thu, Fri
    lagged = data.publication_lag(s, 2)
    assert list(lagged.index) == list(pd.to_datetime(["2024-03-11", "2024-03-12"]))  # Mon, Tue


def test_partial_bar_dropped_before_us_close():
    idx = pd.bdate_range("2026-10-26", periods=2)  # Mon, Tue
    prices = pd.DataFrame({"Close": [1.0, 2.0]}, index=idx)
    before_close = pd.Timestamp("2026-10-27 15:00", tz="America/New_York")
    after_close = pd.Timestamp("2026-10-27 16:30", tz="America/New_York")
    assert data.completed_bars(prices, before_close).index[-1] == idx[0]
    assert data.completed_bars(prices, after_close).index[-1] == idx[1]


def test_rolling_auc_only_uses_revealed_labels():
    """Perfect predictions whose labels aren't revealed yet must not raise the AUC."""
    n, h = 600, 5
    idx = pd.bdate_range("2020-01-01", periods=n)
    rng = np.random.default_rng(0)
    y = pd.Series(rng.integers(0, 2, n).astype(float), idx)
    p = pd.Series(rng.random(n), idx)
    p.iloc[400:] = y.iloc[400:]  # from day 400 on, predictions are perfect
    auc = S.rolling_auc(p, y, h, min_obs=100, every=1)
    assert abs(auc.iloc[400 + h - 2] - 0.5) < 0.1  # perfect predictions not yet revealed
    assert auc.iloc[-1] > auc.iloc[400 + h - 2]  # once revealed they count
