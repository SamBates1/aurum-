"""Point-in-time US company accounts from the SEC (platform phase 1).

Source: SEC EDGAR "company facts" (data.sec.gov/api/xbrl/companyfacts), free. Every reported number carries the date
its filing reached the SEC (`filed`), so a question "what did we know on date D?" uses only facts filed on or before
D, including the version of a figure as it stood then (later restatements are ignored until they were filed).

Coverage limits (stated, never hidden): only US companies that file with the SEC; foreign filers using IFRS forms and
funds/ETFs have few or no facts; small companies tag inconsistently, so a metric can be missing (reported as missing,
never filled in). The SEC asks every automated client to identify itself and to stay under 10 requests a second.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from .config import ROOT

CACHE = ROOT / "data" / "sec"
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
USER_AGENT = os.environ.get("SEC_USER_AGENT", "Aurum research project SamBates1@users.noreply.github.com")

# concept -> XBRL tags tried in order (companies use different tags for the same thing)
CONCEPTS = {
    "revenue": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
    ],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "operating_income": ["OperatingIncomeLoss"],
    "cfo": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
    "equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "assets": ["Assets"],
    "debt": ["LongTermDebt", "LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
    "current_assets": ["AssetsCurrent"],
    "current_liabilities": ["LiabilitiesCurrent"],
    "shares": ["EntityCommonStockSharesOutstanding", "CommonStockSharesOutstanding"],
}
DURATION = {"revenue", "net_income", "operating_income", "cfo", "capex"}  # flows over a period; the rest are levels
TAX_RATE = 0.21  # US federal rate, for after-tax return on invested capital


def _fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < 3:
                time.sleep(2 * (attempt + 1))
                continue
            raise
    raise RuntimeError(f"SEC unreachable: {url}")


def ticker_map(cache: Path = CACHE, max_age_days: float = 7) -> dict[str, int]:
    """Ticker -> SEC central index key (CIK)."""
    cache.mkdir(parents=True, exist_ok=True)
    p = cache / "company_tickers.json"
    if not p.is_file() or time.time() - p.stat().st_mtime > max_age_days * 86400:
        p.write_text(json.dumps(_fetch_json(TICKERS_URL)))
    raw = json.loads(p.read_text())
    return {v["ticker"].upper().replace("-", "."): int(v["cik_str"]) for v in raw.values()}


def company_facts(cik: int, cache: Path = CACHE, max_age_days: float = 7) -> dict:
    cache.mkdir(parents=True, exist_ok=True)
    p = cache / f"CIK{cik:010d}.json"
    if not p.is_file() or time.time() - p.stat().st_mtime > max_age_days * 86400:
        p.write_text(json.dumps(_fetch_json(FACTS_URL.format(cik=cik))))
        time.sleep(0.15)  # stay well under the SEC's 10 requests a second
    return json.loads(p.read_text())


def facts_table(facts: dict) -> pd.DataFrame:
    """Every fact for the concepts Aurum uses: concept, tag, unit, start, end, value, filed, form, fiscal period."""
    rows = []
    groups = facts.get("facts", {})
    for concept, tags in CONCEPTS.items():
        for tag in tags:
            node = groups.get("us-gaap", {}).get(tag) or groups.get("dei", {}).get(tag)
            if not node:
                continue
            for unit, items in node.get("units", {}).items():
                if unit not in ("USD", "shares"):
                    continue
                for it in items:
                    rows.append(
                        {
                            "concept": concept,
                            "tag": tag,
                            "unit": unit,
                            "start": it.get("start"),
                            "end": it.get("end"),
                            "value": float(it["val"]),
                            "filed": it.get("filed"),
                            "form": it.get("form"),
                            "fp": it.get("fp"),
                        }
                    )
            break  # first tag with data wins, so a concept never mixes two tags' definitions
    t = pd.DataFrame(rows)
    if len(t):
        for c in ("start", "end", "filed"):
            t[c] = pd.to_datetime(t[c])
        t["days"] = (t["end"] - t["start"]).dt.days
    return t


def _latest(t: pd.DataFrame, concept: str, asof, annual: bool) -> pd.Series | None:
    """Most recent value of `concept` known on `asof` (filed on or before it). Annual = a ~12-month period."""
    x = t[(t["concept"] == concept) & (t["filed"] <= pd.Timestamp(asof))]
    if concept in DURATION:
        x = x[x["days"].between(330, 400)] if annual else x
    if not len(x):
        return None
    x = x.sort_values(["end", "filed"])
    last_end = x["end"].iloc[-1]
    return x[x["end"] == last_end].iloc[-1]  # the latest version of that period known by asof


def _prior_year(t: pd.DataFrame, concept: str, asof, end) -> float | None:
    x = t[(t["concept"] == concept) & (t["filed"] <= pd.Timestamp(asof)) & t["days"].between(330, 400)]
    x = x[(x["end"] < end - pd.Timedelta(days=300)) & (x["end"] > end - pd.Timedelta(days=430))]
    if not len(x):
        return None
    return float(x.sort_values("filed")["value"].iloc[-1])


def metrics(t: pd.DataFrame, asof, price: float | None = None) -> dict:
    """Fundamental metrics as known on `asof`. Missing inputs give None, listed in `missing`."""
    out: dict = {"asof": str(pd.Timestamp(asof).date()), "missing": []}
    if t is None or not len(t):
        out["missing"] = ["no SEC facts"]
        return out
    v = {}
    for c in CONCEPTS:
        r = _latest(t, c, asof, annual=c in DURATION)
        v[c] = r
        if r is None:
            out["missing"].append(c)
    num = {c: (float(r["value"]) if r is not None else None) for c, r in v.items()}

    def ratio(a, b):
        return a / b if a is not None and b not in (None, 0) else None

    rev = v["revenue"]
    out["period_end"] = str(rev["end"].date()) if rev is not None else None
    out["filed"] = str(rev["filed"].date()) if rev is not None else None
    out["revenue"] = num["revenue"]
    prev = _prior_year(t, "revenue", asof, rev["end"]) if rev is not None else None
    out["revenue_growth"] = ratio(num["revenue"] - prev, abs(prev)) if prev and num["revenue"] is not None else None
    ni = v["net_income"]
    prev_ni = _prior_year(t, "net_income", asof, ni["end"]) if ni is not None else None
    out["earnings_growth"] = (
        ratio(num["net_income"] - prev_ni, abs(prev_ni)) if prev_ni and num["net_income"] is not None else None
    )
    out["net_margin"] = ratio(num["net_income"], num["revenue"])
    out["operating_margin"] = ratio(num["operating_income"], num["revenue"])
    out["roe"] = ratio(num["net_income"], num["equity"]) if (num["equity"] or 0) > 0 else None
    invested = None
    if num["equity"] is not None:
        invested = num["equity"] + (num["debt"] or 0) - (num["cash"] or 0)
    out["roic"] = (
        ratio(num["operating_income"] * (1 - TAX_RATE), invested)
        if num["operating_income"] is not None and invested and invested > 0
        else None
    )
    fcf = num["cfo"] - (num["capex"] or 0) if num["cfo"] is not None else None
    out["free_cash_flow"] = fcf
    out["fcf_margin"] = ratio(fcf, num["revenue"])
    out["cash_conversion"] = ratio(fcf, num["net_income"]) if (num["net_income"] or 0) > 0 else None
    out["debt_to_equity"] = ratio(num["debt"] or 0.0, num["equity"]) if (num["equity"] or 0) > 0 else None
    out["current_ratio"] = ratio(num["current_assets"], num["current_liabilities"])
    out["shares"] = num["shares"]
    if price and num["shares"]:
        mcap = price * num["shares"]
        out["market_cap"] = mcap
        out["pe"] = ratio(mcap, num["net_income"]) if (num["net_income"] or 0) > 0 else None
        out["ps"] = ratio(mcap, num["revenue"])
        out["fcf_yield"] = ratio(fcf, mcap)
    return {k: (None if isinstance(x, float) and not np.isfinite(x) else x) for k, x in out.items()}


def fundamentals(ticker: str, asof, price: float | None = None, tmap: dict | None = None) -> dict:
    """Convenience: fetch (cached) and compute metrics for one ticker. Raises KeyError if the SEC has no such ticker."""
    tmap = tmap or ticker_map()
    cik = tmap[ticker.upper()]
    return metrics(facts_table(company_facts(cik)), asof, price) | {"ticker": ticker.upper(), "cik": cik}
