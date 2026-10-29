"""Data validation, caching and parsing. External calls are mocked."""

import io
from datetime import datetime, timedelta, timezone
from unittest import mock

import pandas as pd
import pytest
from conftest import make_prices

from aurum import data
from aurum.sentiment import headline_sentiment


def test_validate_sorts_dedupes_and_drops_bad_rows():
    p = make_prices([100, 101, 102, 103])
    messy = pd.concat([p.iloc[[2]], p, p.iloc[[1]]])
    messy.iloc[3, messy.columns.get_loc("Close")] = -5
    clean = data.validate_ohlcv(messy, "TEST")
    assert clean.index.is_monotonic_increasing and clean.index.is_unique
    assert (clean["Close"] > 0).all() and len(clean) == 3


def test_validate_rejects_empty_and_short():
    with pytest.raises(data.DataError):
        data.validate_ohlcv(pd.DataFrame(), "EMPTY")
    with pytest.raises(data.DataError):
        data.validate_ohlcv(make_prices([1, 2]), "SHORT", min_rows=10)


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "CACHE_DIR", tmp_path)
    return tmp_path


def test_cache_used_when_fresh(cache_dir):
    p = make_prices([1, 2, 3])
    fetch = mock.Mock(return_value=p)
    data._cached("X", "test", fetch, max_age_hours=12)
    data._cached("X", "test", fetch, max_age_hours=12)
    assert fetch.call_count == 1
    assert data.cache_info("X")["rows"] == 3


def test_cache_refreshed_when_max_age_zero(cache_dir):
    fetch = mock.Mock(return_value=make_prices([1, 2, 3]))
    data._cached("X", "test", fetch, max_age_hours=0)
    data._cached("X", "test", fetch, max_age_hours=0)
    assert fetch.call_count == 2


def test_failed_download_falls_back_to_cache_loudly(cache_dir):
    data._cached("X", "test", lambda: make_prices([1, 2, 3]), max_age_hours=0)
    n_events = len(data.DATA_EVENTS)
    out = data._cached("X", "test", mock.Mock(side_effect=OSError("offline")), max_age_hours=0)
    assert len(out) == 3
    assert "STALE" in data.DATA_EVENTS[n_events]["message"]


def test_failed_download_without_cache_raises(cache_dir):
    with pytest.raises(data.DataError):
        data._cached("Y", "test", mock.Mock(side_effect=OSError("offline")), max_age_hours=0)


@pytest.mark.parametrize(
    "csv",
    ["observation_date,DFII10\n2026-10-22,1.85\n2026-10-23,.\n", "DATE,DFII10\n2026-10-22,1.85\n"],
)
def test_fred_parser_handles_both_header_formats(csv):
    with mock.patch("pandas.read_csv", return_value=pd.read_csv(io.StringIO(csv))):
        s = data._fred_series("DFII10")
    assert s.to_dict() == {pd.Timestamp("2026-10-22"): 1.85}


def test_news_parser_handles_both_yfinance_formats_and_drops_undated():
    items = [
        {
            "content": {
                "title": "Gold rallies",
                "pubDate": "2026-10-27T10:00:00Z",
                "provider": {"displayName": "Reuters"},
                "canonicalUrl": {"url": "https://x"},
            }
        },
        {"title": "Old style", "publisher": "AP", "link": "https://y", "providerPublishTime": 1761559200},
        {"title": "No date"},
    ]
    ticker = mock.Mock(news=items)
    cfg = {"offline": False, "signals": {"news_aliases": {}}}
    with mock.patch("yfinance.Ticker", return_value=ticker):
        out = data.news("GLD", cfg=cfg)
    assert [o["title"] for o in out] == ["Gold rallies", "Old style"]
    assert out[0]["publisher"] == "Reuters" and out[1]["publisher"] == "AP"


def test_sentiment_ignores_old_future_and_undated_headlines():
    now = datetime(2026, 10, 27, 12, tzinfo=timezone.utc)
    items = [
        {"title": "Gold rallies to record", "published": now - timedelta(hours=2)},
        {"title": "Gold plunges", "published": now - timedelta(days=30)},
        {"title": "Gold slumps", "published": now + timedelta(hours=1)},
        {"title": "Gold falls", "published": None},
    ]
    s = headline_sentiment(items, max_age_days=7, now=now)
    assert s["n"] == 1 and s["score"] > 0


def test_staleness_measured_in_new_york_days():
    p = make_prices([1, 2], start="2026-10-21")  # Wed, Thu
    now = pd.Timestamp("2026-10-27 12:00", tz="America/New_York")
    assert data.staleness_days(p, now) == 5


def test_retry_recovers_from_transient_failures(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    calls = iter([OSError("rate limited"), pd.DataFrame(), make_prices([1, 2])])

    def flaky():
        x = next(calls)
        if isinstance(x, Exception):
            raise x
        return x

    assert len(data._retry(flaky, "test")) == 2
    with pytest.raises(OSError):
        data._retry(mock.Mock(side_effect=OSError("down")), "test", attempts=2)
