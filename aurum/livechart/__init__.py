"""Live chart component (TradingView Lightweight Charts inside Streamlit) and the payload it draws.

    from aurum.livechart import live_chart, build_payload
    live_chart(build_payload(...), key="aapl-15m")

The browser receives only prices and Aurum's own calculations (never API keys). While the layout key (symbol,
timeframe, indicator set) stays the same, new data updates the chart in place, keeping the user's zoom.
"""

from __future__ import annotations

from pathlib import Path

from .payload import build_payload, chart_time

_FRONTEND = Path(__file__).parent / "frontend"
_component = None


def live_chart(payload: dict, key: str | None = None):
    """Render the chart. Imported lazily so the payload builder can be used and tested without Streamlit."""
    global _component
    import streamlit.components.v1 as components

    if _component is None:
        _component = components.declare_component("aurum_live_chart", path=str(_FRONTEND))
    return _component(payload=payload, key=key, default=None)


__all__ = ["build_payload", "chart_time", "live_chart"]
