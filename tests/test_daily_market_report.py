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


def test_documented_command_runs_offline(tmp_path):
    """The README command `python scripts/daily_market_report.py` must work from the project root
    (it previously failed with ModuleNotFoundError: aurum)."""
    import os
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    out = tmp_path / "r.md"
    env = {**os.environ, "AURUM_OFFLINE": "1"}
    r = subprocess.run(
        [
            sys.executable,
            "scripts/daily_market_report.py",
            "--offline",
            "--tickers",
            "GLD",
            "SPY",
            "--output",
            str(out),
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr
    text = out.read_text()
    assert "SYNTHETIC/OFFLINE DATA" in text and "| GLD |" in text and "| SPY |" in text


def test_stale_data_is_flagged(monkeypatch):
    from aurum import data

    monkeypatch.setattr(data, "daily_prices", lambda ticker, cfg=None: prices())  # ends in 2025: very old
    report = build_report(["OLD"], cfg={"offline": True, "data": {"max_stale_days": 4}})
    assert "(STALE)" in report
