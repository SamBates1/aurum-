"""Plain-English summary for one ticker (live-charts stage 5): why we might be interested, why we might be wrong (a
rule-based devil's advocate) and what the strategy says to do. Also dashboard alerts.

Everything is derived from the trade plan, the timeframe check, the recommendation history and the strategy's test
record, by fixed rules (no AI). The devil's advocate always argues against the current view, so a reader sees the
strongest case on both sides before acting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import yaml

from .config import ROOT

ALERTS_FILE = ROOT / "alerts.yaml"  # the owner's own price alerts (local, git-ignored)


@dataclass
class Summary:
    headline: str
    interested: list[str] = field(default_factory=list)
    wrong: list[str] = field(default_factory=list)
    do: list[str] = field(default_factory=list)


def build(
    plan, timeframes: dict | None = None, history: list[dict] | None = None, evidence: str | None = None
) -> Summary:
    """plan: tradeplan.TradePlan; timeframes: analysis.multi_timeframe(); history: this ticker's records;
    evidence: the strategy's Fair Test status in words (e.g. 'Inconclusive (DSR 0.40)')."""
    s = Summary(headline=f"{plan.symbol}: {plan.action_text}")
    ok = [t for good, t in plan.confidence_points if good]
    bad = [t for good, t in plan.confidence_points if not good]
    holding = plan.target_weight > 0

    # why interested
    if holding:
        s.interested.append(f"The strategy wants {plan.target_weight:.0%} of the account in {plan.symbol}.")
    s.interested += [f"{t[0].upper()}{t[1:]}." for t in ok if "strategy wants" not in t]
    best = max((rr for _, _, rr in plan.targets), default=0)
    if best >= 2:
        s.interested.append(f"The plan offers up to {best:.1f} times the risk if a target is reached.")
    if plan.correlation is not None and plan.correlation < 0.3:
        s.interested.append("It moves differently from the main account, so it would spread risk.")

    # devil's advocate: the case against the current view
    s.wrong += [f"{t[0].upper()}{t[1:]}." for t in bad]
    if timeframes and "conflict" in timeframes.get("verdict", ""):
        s.wrong.append("Short and long timeframes disagree: a trend change may be under way.")
    if plan.resistance and holding:
        room = plan.resistance / plan.entry - 1
        if room < 0.02:
            s.wrong.append(f"Resistance at ${plan.resistance:,.2f} is only {room:.1%} above: limited room to rise.")
    stop_frac = 1 - plan.stop / plan.entry
    if stop_frac < 0.01:
        s.wrong.append("The stop is very close: ordinary daily noise could hit it.")
    s.wrong.append(
        f"A gap at the open can go straight through the stop; the real loss could be larger than £{plan.risk_gbp:,.0f}."
    )
    if "plan default" in plan.stop_source:
        s.wrong.append(
            "The stop and targets are risk information, not part of the tested strategy: in EXP-049 fixed stops and "
            "profit targets made the 70/30 strategy worse, not better."
        )
    if evidence and not evidence.lower().startswith("pass"):
        s.wrong.append(f"The strategy's own test is not a clear pass: {evidence}.")
    if history:
        flips = sum(1 for r in history[-20:] if any(c.startswith("action") for c in r.get("changed", [])))
        if flips >= 3:
            s.wrong.append(f"The view has changed {flips} times in the last {min(20, len(history))} records: unstable.")
    if plan.correlation is not None and plan.correlation > 0.7 and holding:
        s.wrong.append("It moves closely with what the main account already holds: little extra diversification.")
    if not holding:
        s.wrong.append("Staying out can miss a rally: the strategy re-enters only when its rules are met again.")

    # what to do
    if plan.notes:
        s.do.append("Research only: no size, because this ticker is outside the risk engine's allowed list.")
    if plan.action == "BUY":
        s.do.append(
            f"The strategy says buy about £{plan.size_gbp:,.0f} of {plan.uk_fund.split(' (')[0]} at the next open, "
            f"with a stop near ${plan.stop:,.2f} on {plan.symbol}."
        )
    elif plan.action == "HOLD":
        s.do.append(f"Hold. Review if {plan.invalidation[0]}.")
    elif plan.action == "SELL":
        s.do.append(f"The strategy says sell {plan.symbol} at the next open.")
    else:
        s.do.append("Nothing to do: the strategy does not want this ticker now.")
    s.do.append("You decide and place any real trade yourself; this is what the strategy says, not advice.")
    return s


# ---------------------------------------------------------------------------------------------------------------
# alerts (shown on the dashboard; email can be added later)
# ---------------------------------------------------------------------------------------------------------------
def load_alerts(path: Path = ALERTS_FILE) -> list[dict]:
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except FileNotFoundError:
        return []
    return [a for a in data.get("alerts", []) if isinstance(a, dict)]


def save_alerts(alerts: list[dict], path: Path = ALERTS_FILE) -> None:
    path.write_text(yaml.safe_dump({"alerts": alerts}, sort_keys=False))


def check_alerts(symbol: str, price: float, plan=None, history: list[dict] | None = None, custom=None) -> list[str]:
    """Alerts that are true right now for `symbol`: automatic ones (stop reached, near support/resistance, the
    recommendation changed at the last close) plus the owner's price alerts."""
    out = []
    if plan is not None:
        if price <= plan.stop:
            out.append(f"🔴 {symbol} is at or below the plan's stop (${plan.stop:,.2f}).")
        near = 0.5 * plan.atr
        if plan.support and abs(price - plan.support) <= near:
            out.append(f"🟡 {symbol} is near support (${plan.support:,.2f}).")
        if plan.resistance and abs(price - plan.resistance) <= near:
            out.append(f"🟡 {symbol} is near resistance (${plan.resistance:,.2f}).")
    if history:
        last = history[-1]
        if last.get("changed"):
            out.append(f"🔵 At the close of {last['as_of']}: {'; '.join(last['changed'])}.")
    for a in custom if custom is not None else load_alerts():
        if a.get("symbol") != symbol:
            continue
        lvl = float(a.get("price", 0))
        if a.get("when") == "above" and price >= lvl:
            out.append(f"🔔 {symbol} is above your alert level ${lvl:,.2f}.")
        if a.get("when") == "below" and price <= lvl:
            out.append(f"🔔 {symbol} is below your alert level ${lvl:,.2f}.")
    return out


def news_table(items: list[dict], limit: int = 10) -> pd.DataFrame:
    rows = []
    for n in items[:limit]:
        t = pd.Timestamp(n.get("time")) if n.get("time") else None
        rows.append(
            {
                "When (UK)": t.tz_convert("Europe/London").strftime("%d %b %H:%M")
                if t is not None and t.tzinfo
                else "",
                "Headline": n.get("headline", ""),
                "Source": n.get("source", ""),
                "Link": n.get("url", ""),
            }
        )
    return pd.DataFrame(rows)
