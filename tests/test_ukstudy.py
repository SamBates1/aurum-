"""EXP-046..048 building blocks on hand-built data."""

import numpy as np
import pandas as pd
import pytest
from conftest import make_prices

from aurum import ukstudy as U


def test_pound_return_of_a_dollar_asset():
    idx = pd.date_range("2020-01-01", periods=3, freq="MS")
    r = pd.Series([0.0, 0.10, 0.0], index=idx)
    gbp_per_usd = pd.Series([0.8, 0.8, 0.88], index=idx)  # the dollar strengthens 10% in month 3
    g = U.to_gbp(r, gbp_per_usd)
    assert g.iloc[0] == pytest.approx(0.10) and g.iloc[1] == pytest.approx(0.10)


def test_monthly_mix_rebalances_and_charges_costs():
    idx = pd.date_range("2020-01-01", periods=2, freq="MS")
    R = pd.DataFrame({"a": [0.10, 0.0], "b": [0.0, 0.0]}, index=idx)
    out = U.monthly_mix(R, {"a": 0.5, "b": 0.5}, trade_cost=0.01, fees={})
    assert out.iloc[0] == pytest.approx(0.05 - 0.01)  # initial purchase of 100% at 1%
    drift = abs(0.5 - 0.55 / 1.05) * 2
    assert out.iloc[1] == pytest.approx(-0.01 * drift)


def test_spx_total_return_fills_missing_dividends_with_the_last_yield():
    raw = pd.DataFrame(
        {
            "Date": ["2023-05-01", "2023-06-01", "2023-07-01"],
            "SP500": [100.0, 100.0, 100.0],
            "Dividend": [1.2, 1.2, 0.0],
        }
    )
    r, info = U.spx_total_return(raw)
    assert r.iloc[0] == pytest.approx(0.001) and r.iloc[1] == pytest.approx(0.001)
    assert info["dividends_known_until"] == "2023-06"


def test_gbp_frame_divides_by_the_rate_and_applies_the_fund_drag():
    p = make_prices([100.0] * 253)
    fx = pd.Series(2.0, index=p.index)
    g = U.gbp_frame(p, fx, 0.01)
    assert g["Close"].iloc[0] == pytest.approx(50.0) and g["Close"].iloc[-1] == pytest.approx(
        50.0 * np.exp(-0.01 * 252 / 252)
    )


def test_tracking_check_ignores_unit_changes():
    idx = pd.bdate_range("2020-01-01", periods=600)
    model = pd.Series(np.exp(np.linspace(0, 0.2, 600)), index=idx)
    actual = model.copy()
    actual.iloc[300:] *= 100  # pounds to pence switch
    c = U.tracking_check(model, actual)
    assert abs(c["diff"]) < 1e-3 and c["excluded_days"] == 1


def test_outcomes_with_zero_returns_and_contributions():
    r = pd.Series(0.0, index=pd.date_range("2000-01-01", periods=240, freq="MS"))
    t = U.outcomes(r, lump=1000, monthly=100, horizons=(12,), reps=50)
    row = t.iloc[0]
    assert row["paid_in"] == 1000 + 11 * 100 and row["median"] == pytest.approx(row["paid_in"])
    assert row["chance_fall_20pct"] == 0
