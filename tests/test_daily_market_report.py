import numpy as np
import pandas as pd

from scripts.daily_market_report import build_report, summarise_prices


def prices(n=280):
    idx = pd.bdate_range("2024-01-01", periods=n)
    close = pd.Series(np.linspace(100, 140, n), index=idx)
    return pd.DataFrame(
        {
            "Open": close * 0.999,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": 1_000_000,
        },
        index=idx,
    )


def test_summary_has_trend_metrics():
    result = summarise_prices(prices())
    assert result["close"] == 140.0
    assert result["return_21d_pct"] > 0
    assert result["sma200_gap_pct"] > 0
    assert result["last_date"] == prices().index[-1].date().isoformat()


def test_summary_rejects_too_little_data():
    try:
        summarise_prices(prices(n=1))
    except ValueError as exc:
        assert "two valid" in str(exc)
    else:
        raise AssertionError("Expected a short history to be rejected")


def test_report_records_data_failures_and_never_claims_trading(monkeypatch):
    from aurum import data

    def fake_prices(ticker, cfg=None):
        if ticker == "BAD":
            raise RuntimeError("unavailable")
        return prices()

    monkeypatch.setattr(data, "daily_prices", fake_prices)
    report = build_report(["GOOD", "BAD"], cfg={"offline": True})
    assert "GOOD" in report
    assert "BAD" in report
    assert "no orders" in report.lower()
    assert "unavailable" in report
