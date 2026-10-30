"""Platform phase 8: the new pages render offline without errors."""

import pytest
from streamlit.testing.v1 import AppTest

from aurum.config import ROOT


@pytest.mark.parametrize("page", ["pages/6_Market_Overview.py", "pages/7_Portfolio.py"])
def test_page_renders_offline(page):
    at = AppTest.from_file(str(ROOT / page), default_timeout=300)
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def test_live_analysis_shows_long_term_and_swing_verdicts():
    at = AppTest.from_file(str(ROOT / "pages/1_Live_Analysis.py"), default_timeout=300)
    at.query_params["symbol"] = "SPY"
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    text = " ".join(m.value for m in at.markdown)
    assert "Long-Term:" in text and "Swing:" in text


def test_portfolio_page_says_paper_and_orders_off():
    at = AppTest.from_file(str(ROOT / "pages/7_Portfolio.py"), default_timeout=300)
    at.run()
    text = " ".join(m.value for m in at.markdown) + " ".join(i.value for i in at.info)
    assert "PAPER TRADING" in text and "switched off" in text
