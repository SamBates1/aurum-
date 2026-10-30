"""Market and company events (platform phase 1): Fed meetings, earnings and dividend dates.

Fed (FOMC) meeting dates are copied from the Federal Reserve's published calendar (2027 dates are tentative until
confirmed at the preceding meeting). Earnings and dividend dates come from Yahoo Finance and can move: they are
re-checked on every run and labelled "expected". Other economic releases (CPI, jobs) are not covered yet.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import CFG

FOMC_SOURCE = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
# (first day, decision day, with Summary of Economic Projections)
FOMC = [
    ("2026-01-27", "2026-01-28", False),
    ("2026-03-17", "2026-03-18", True),
    ("2026-04-28", "2026-04-29", False),
    ("2026-06-16", "2026-06-17", True),
    ("2026-07-28", "2026-07-29", False),
    ("2026-09-15", "2026-09-16", True),
    ("2026-10-27", "2026-10-28", False),
    ("2026-12-08", "2026-12-09", True),
    ("2027-01-26", "2027-01-27", False),
    ("2027-03-16", "2027-03-17", True),
    ("2027-04-27", "2027-04-28", False),
    ("2027-06-08", "2027-06-09", True),
    ("2027-07-27", "2027-07-28", False),
    ("2027-09-14", "2027-09-15", True),
    ("2027-10-26", "2027-10-27", False),
    ("2027-12-07", "2027-12-08", True),
]


@dataclass
class Event:
    date: str
    kind: str  # "fomc", "earnings", "ex-dividend"
    symbol: str | None
    text: str
    confirmed: bool
    source: str

    @property
    def gap_risk(self) -> bool:
        """Can move the price overnight (relevant for swing trades held through it)."""
        return self.kind in ("earnings", "fomc")


def fomc_events(start, end) -> list[Event]:
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    out = []
    for d1, d2, sep in FOMC:
        if s <= pd.Timestamp(d2) <= e:
            tentative = d2 >= "2027-01-01"
            out.append(
                Event(
                    d2,
                    "fomc",
                    None,
                    f"Fed rate decision ({d1} to {d2})" + (", with projections" if sep else ""),
                    not tentative,
                    FOMC_SOURCE,
                )
            )
    return out


def company_events(symbol: str, cfg: dict = CFG) -> list[Event]:
    """Expected earnings dates and recent/next ex-dividend dates from Yahoo Finance (empty offline or on failure)."""
    if cfg.get("offline"):
        return []
    out = []
    try:
        import yfinance as yf

        t = yf.Ticker(symbol)
        try:
            ed = t.get_earnings_dates(limit=8)
        except Exception:
            ed = None
        if ed is not None and len(ed):
            for ts in ed.index:
                out.append(
                    Event(
                        str(pd.Timestamp(ts).date()),
                        "earnings",
                        symbol,
                        f"{symbol} earnings",
                        False,
                        "Yahoo Finance (expected; can move)",
                    )
                )
        cal = getattr(t, "calendar", None) or {}
        exd = cal.get("Ex-Dividend Date") if isinstance(cal, dict) else None
        if exd:
            out.append(
                Event(
                    str(pd.Timestamp(exd).date()),
                    "ex-dividend",
                    symbol,
                    f"{symbol} goes ex-dividend",
                    False,
                    "Yahoo Finance",
                )
            )
    except Exception:
        return out
    return out


def upcoming(symbol: str | None, start, days: int = 56, cfg: dict = CFG) -> list[Event]:
    """Events between `start` and `start + days` (8 weeks covers a swing trade), soonest first."""
    s = pd.Timestamp(start).normalize()
    e = s + pd.Timedelta(days=days)
    ev = fomc_events(s, e) + (
        [x for x in company_events(symbol, cfg) if s <= pd.Timestamp(x.date) <= e] if symbol else []
    )
    return sorted(ev, key=lambda x: x.date)
