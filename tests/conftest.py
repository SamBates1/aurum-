"""Shared fixtures. Tests never touch the network: offline mode is forced
before aurum is imported, and live-data functions are mocked where tested."""

import copy
import os

os.environ["AURUM_OFFLINE"] = "1"

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from aurum import data  # noqa: E402
from aurum.config import load_config  # noqa: E402


@pytest.fixture
def cfg():
    c = load_config()
    c["offline"] = True
    return copy.deepcopy(c)


@pytest.fixture(scope="session")
def gld():
    c = load_config()
    c["offline"] = True
    return data.daily_prices("GLD", cfg=c)


def make_prices(closes, opens=None, start="2024-01-01"):
    """Tiny hand-built OHLCV frame for exact accounting tests."""
    closes = np.asarray(closes, dtype=float)
    opens = closes if opens is None else np.asarray(opens, dtype=float)
    idx = pd.bdate_range(start, periods=len(closes))
    return pd.DataFrame(
        {
            "Open": opens,
            "High": np.maximum(opens, closes),
            "Low": np.minimum(opens, closes),
            "Close": closes,
            "Volume": 1e6,
        },
        index=idx,
    )
