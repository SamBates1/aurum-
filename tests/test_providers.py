"""Market-data providers (live-charts stage 1): keys, labels, Alpaca feed split, stream parsing, synthetic data."""

import pandas as pd
import pytest

from aurum.providers import alpaca as A
from aurum.providers import base, keys
from aurum.providers.synthetic import SyntheticProvider


def test_keys_from_env_file_and_environment(tmp_path, monkeypatch):
    monkeypatch.setattr(keys, "ROOT", tmp_path)
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    assert keys.alpaca_keys() is None
    (tmp_path / ".env").write_text('# private\nALPACA_API_KEY="PKTEST"\nALPACA_SECRET_KEY=s3cr3t\n')
    assert keys.alpaca_keys() == ("PKTEST", "s3cr3t")
    monkeypatch.setenv("ALPACA_API_KEY", "PKENV")
    assert keys.alpaca_keys()[0] == "PKENV"
    assert "s3cr3t" not in keys.redact("error with s3cr3t inside")


def _rows(times, price):
    return [{"t": t, "o": price, "h": price + 1, "l": price - 1, "c": price, "v": 100} for t in times]


def test_alpaca_history_from_sip_and_latest_from_iex(monkeypatch):
    now = pd.Timestamp.now(tz="UTC").floor("5min")
    sip_t = [(now - pd.Timedelta(minutes=m)).isoformat() for m in (60, 55, 50, 30)]
    iex_t = [(now - pd.Timedelta(minutes=m)).isoformat() for m in (30, 10, 5)]
    calls = []

    def fake_get(url, params=None, timeout=30):
        calls.append(params["feed"])
        times = sip_t if params["feed"] == "sip" else iex_t
        return {"bars": {"SPY": _rows(times, 100 if params["feed"] == "sip" else 101)}, "next_page_token": None}

    monkeypatch.setattr(A, "_get", fake_get)
    b = A.AlpacaProvider().bars("SPY", "5m", start=now - pd.Timedelta(hours=2))
    assert calls == ["sip", "iex"]
    assert list(b["source"]) == ["SIP"] * 4 + ["IEX"] * 2  # the IEX bar overlapping SIP history is dropped
    lab = base.data_label(b, "Alpaca", last_trade_age_s=5)
    assert lab.live and "IEX real-time" in lab.text and "consolidated" in lab.text
    assert not base.data_label(b, "Alpaca", last_trade_age_s=600).live


def test_stream_messages_are_parsed_without_a_connection(monkeypatch):
    monkeypatch.setattr(A.IEXStream, "_run", lambda self: None)
    s = A.IEXStream(["spy", "AAPL"] + [f"X{i}" for i in range(40)])
    assert len(s.symbols) == A.MAX_STREAM_SYMBOLS and s.symbols[0] == "SPY"
    s._handle({"T": "t", "S": "SPY", "p": 501.25, "s": 10, "t": pd.Timestamp.now(tz="UTC").isoformat()})
    s._handle(
        {
            "T": "b",
            "S": "SPY",
            "o": 500,
            "h": 502,
            "l": 499,
            "c": 501,
            "v": 1000,
            "t": pd.Timestamp.now(tz="UTC").isoformat(),
        }
    )
    snap = s.snapshot("spy")
    assert snap["trade"]["price"] == 501.25 and snap["age_s"] < 60 and len(snap["minute_bars"]) == 1


@pytest.mark.parametrize("tf", list(base.TIMEFRAMES))
def test_synthetic_provider_serves_every_timeframe(tf):
    p = SyntheticProvider(now=pd.Timestamp("2026-10-30 18:00", tz="UTC"))
    b = p.bars("AAPL", tf)
    assert len(b) > 20 and set(b["source"]) == {"SYNTHETIC"} and b.index.tz is not None
    assert (b["High"] >= b[["Open", "Close"]].max(axis=1) - 1e-9).all()
    if tf in base.INTRADAY:
        ny = b.index.tz_convert("America/New_York")
        assert ((ny.hour * 60 + ny.minute) >= 570).all() and (ny.day_of_week < 5).all()  # regular session only


def test_get_provider_falls_back_without_keys(monkeypatch, cfg):
    from aurum import providers

    monkeypatch.setattr(providers, "alpaca_keys", lambda: None)
    assert providers.get_provider(cfg).name.startswith("Synthetic")
    cfg2 = dict(cfg, offline=False)
    assert providers.get_provider(cfg2).name.startswith("Yahoo")
    monkeypatch.setattr(providers, "alpaca_keys", lambda: ("k", "s"))
    assert providers.get_provider(cfg2).name == "Alpaca"


def test_keys_from_hosting_secrets_when_no_env_or_dotenv(monkeypatch, tmp_path):
    from aurum.providers import keys as K

    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    monkeypatch.setattr(K, "_dotenv", lambda: {})
    monkeypatch.setattr(K, "_streamlit_secrets", lambda: {"ALPACA_API_KEY": "kid", "ALPACA_SECRET_KEY": "sec"})
    assert K.alpaca_keys() == ("kid", "sec") and K.redact("x sec y") == "x *** y"
    monkeypatch.setenv("ALPACA_API_KEY", "envk")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "envs")
    assert K.alpaca_keys() == ("envk", "envs")


def test_cloud_entry_point_opens_live_analysis():
    from streamlit.testing.v1 import AppTest

    from aurum.config import ROOT

    at = AppTest.from_file(str(ROOT / "cloud_app.py"), default_timeout=300)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Paper trading only" in c.value for c in at.caption)
