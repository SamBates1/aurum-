"""Decision Board: what the chosen strategy says to do right now, in pounds, for the owner to act on himself (D-036).

Two answers, always shown side by side:

  OFFICIAL   the decision from the last COMPLETED daily close, exactly as backtested and paper-traded (same engine,
             aurum/engine.py). This is the one to act on.
  PREVIEW    what the decision would be if today ended at the latest price (about 15 minutes delayed). Only
             meaningful while the US market is open; it can change before the close and is never acted on by the bot.

For each asset: BUY / SELL / HOLD, the target share and amount in pounds, the trade needed from the owner's current
holdings, when to act, the exit rule, the reason, a UK-listed fund that tracks the same thing, and the evidence
behind the strategy (Fair Test verdict and approval). This is what the strategy says, not personal financial advice;
Aurum never places real-money orders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timezone

import numpy as np
import pandas as pd

from . import engine as E
from . import spec as SP

# UK-listed (UCITS) funds tracking the same thing as the US ETFs the research uses. US-domiciled ETFs are usually not
# available to UK retail investors. Examples only: check the exact fund, currency and fees on your platform.
UK_FUNDS = {
    "SPY": [("VUSA", "Vanguard S&P 500 UCITS ETF"), ("CSPX", "iShares Core S&P 500 UCITS ETF")],
    "GLD": [("SGLN", "iShares Physical Gold ETC"), ("PHGP", "WisdomTree Physical Gold")],
    "QQQ": [("EQQQ", "Invesco EQQQ Nasdaq-100 UCITS ETF")],
    "SLV": [("SSLN", "iShares Physical Silver ETC")],
    "TLT": [("IDTL", "iShares $ Treasury Bond 20+yr UCITS ETF")],
    "IEF": [("IBTM", "iShares $ Treasury Bond 7-10yr UCITS ETF")],
    "GDX": [("GDGB", "VanEck Gold Miners UCITS ETF")],
}
NY = "America/New_York"


def uk_fund(ticker: str) -> str:
    f = UK_FUNDS.get(ticker)
    if not f:
        return f"look for a UCITS fund tracking the same index as {ticker} on your platform"
    return " or ".join(f"{code} ({name})" for code, name in f)


def market_status(now: datetime | None = None) -> dict:
    """US market open or closed (weekdays 09:30-16:00 New York; exchange holidays are not modelled)."""
    t = pd.Timestamp(now or datetime.now(timezone.utc)).tz_convert(NY)
    open_ = t.weekday() < 5 and time(9, 30) <= t.time() < time(16, 0)
    uk = t.tz_convert("Europe/London")
    return {
        "open": open_,
        "ny_time": t.strftime("%a %H:%M"),
        "uk_time": uk.strftime("%a %H:%M"),
        "label": "US market OPEN (prices about 15 minutes delayed)" if open_ else "US market CLOSED",
    }


def next_decision_day(spec: dict, after: pd.Timestamp) -> pd.Timestamp | None:
    """Next weekday on which the strategy may decide (US holidays not modelled, so it may be a day later)."""
    rule = SP.normalise(spec)["schedule"]["rebalance"]
    if rule == "once":
        return None
    days = pd.bdate_range(after - pd.Timedelta(days=40), after + pd.Timedelta(days=400))
    sched = E.schedule_days(days, rule)
    later = sched[(sched.index > after) & sched]
    return later.index[0] if len(later) else None


def exit_rule(spec: dict, ticker: str) -> str:
    s = SP.normalise(spec)
    parts = []
    sch = s["schedule"]
    if s["sizing"]["method"] == "vol_cap":
        parts.append(
            f"trim when {ticker}'s {s['sizing']['vol_window']}-day volatility rises above "
            f"{s['sizing']['target_vol']:.0%}"
        )
    for g in s["signals"]:
        if ticker in g["apply_to"]:
            parts.append(f"cut to {g['when_false']:.0%} of normal when '{g['label']}' stops being met")
    if "trailing_stop" in s["exits"]:
        parts.append(f"sell after a {float(s['exits']['trailing_stop']['pct']):.0%} fall from its peak")
    stg = s["exits"].get("stop_target")
    if stg:
        u = stg.get("unit", "atr")
        if stg.get("stop") is not None:
            parts.append(
                f"sell if it closes {stg['stop']:g} ATR below the buy price"
                if u == "atr"
                else f"sell if it closes {float(stg['stop']):.0%} below the buy price"
            )
        if stg.get("target") is not None:
            parts.append(
                f"take profit if it closes {stg['target']:g} ATR above the buy price"
                if u == "atr"
                else f"take profit if it closes {float(stg['target']):.0%} above the buy price"
            )
    if sch["rebalance"] != "once":
        drift = f"more than {sch['band']:.0%} of the account above target" if sch["band"] > 0 else "above target"
        parts.append(f"trim back to target at each {sch['rebalance']} check if it has grown {drift}")
    return "; ".join(parts) or "never sold (buy and hold)"


@dataclass
class Board:
    strategy: dict
    official_date: pd.Timestamp
    official_rebalance: bool
    first_investment: bool
    rows: list[dict]
    preview_date: pd.Timestamp | None = None
    preview_changes: list[str] = field(default_factory=list)
    next_check: pd.Timestamp | None = None
    money: float = 0.0
    cash_after: float = 0.0
    headline: str = ""


def _with_live_bar(daily: pd.DataFrame, live: float | None, today: pd.Timestamp) -> pd.DataFrame:
    """Completed bars plus a provisional bar for today at the live price (used for the preview only)."""
    if live is None or not np.isfinite(live):
        return daily
    d = daily.loc[daily.index < today]
    if not len(d):
        return daily
    bar = pd.DataFrame(
        {
            "Open": [d["Close"].iloc[-1]],
            "High": [max(live, d["Close"].iloc[-1])],
            "Low": [min(live, d["Close"].iloc[-1])],
            "Close": [live],
            "Volume": [np.nan],
        },
        index=[today],
    )
    return pd.concat([d, bar])


def build(
    spec: dict,
    completed: dict[str, pd.DataFrame],
    holdings: dict[str, float],
    cash: float,
    *,
    live: dict[str, float] | None = None,
    now: datetime | None = None,
    fair_test: dict | None = None,
    approval: dict | None = None,
) -> Board:
    """completed: completed daily bars per asset; holdings: pounds currently held in each asset's fund."""
    s = SP.validate(spec)
    uni = s["universe"]
    comp = E.compile_targets(s, completed)
    d = comp.index[-1]
    tgt = {t: float(comp.raw_target[t].iloc[-1]) for t in uni}
    money = float(cash) + sum(float(holdings.get(t, 0.0)) for t in uni)
    cur = {t: (float(holdings.get(t, 0.0)) / money if money > 0 else 0.0) for t in uni}
    first = money > 0 and all(float(holdings.get(t, 0.0)) == 0 for t in uni)
    reb = bool(comp.rebalance.iloc[-1])
    band = s["schedule"]["band"]
    # a rebalance in the last 5 trading days still counts: acting a few days late made no difference (EXP-044)
    recent = comp.rebalance.iloc[-5:]
    last_reb = recent[recent].index[-1] if recent.any() else None
    act_day = reb or first or last_reb is not None or s["schedule"]["rebalance"] == "daily"
    ms = market_status(now)
    today = pd.Timestamp(pd.Timestamp(now or datetime.now(timezone.utc)).tz_convert(NY).date())
    nxt = next_decision_day(s, d)
    evidence = (
        f"Fair Test {fair_test['status'].upper()} ({fair_test['run_at'][:10]})" if fair_test else "no Fair Test saved"
    ) + (f"; approved by you as {approval['role']}" if approval else "; not approved by you")
    from .risk import limits

    min_trade = float(limits()["min_order_value"])  # ignore dust trades (risk engine minimum, $ ~ £ here)
    rows, buys = [], 0.0
    for t in uni:
        w, c = tgt[t], cur[t]
        move = abs(w - c) > band or ((w == 0) != (c == 0) and abs(w - c) > 1e-9)
        amount = (w - c) * money
        if not act_day:
            action, when = (
                "HOLD",
                (f"no change until the next decision day ({nxt.date()})" if nxt is not None else "never traded again"),
            )
        elif not move or abs(amount) < max(min_trade, 0.005 * money):
            action, when = "HOLD", "already close enough to target"
        else:
            action = "BUY" if amount > 0 else "SELL"
            when = "now: at or after the next US open" if not ms["open"] else "now (market open)"
        reasons = []
        if first and act_day:
            reasons.append("first investment of this money")
        elif reb:
            reasons.append(f"{s['schedule']['rebalance']} rebalance day (close of {d.date()})")
        elif last_reb is not None and s["schedule"]["rebalance"] != "daily":
            reasons.append(
                f"{s['schedule']['rebalance']} rebalance of {last_reb.date()} not yet done (a few days late is fine)"
            )
        if s["sizing"]["method"] == "vol_cap" and np.isfinite(comp.vol.at[d, t]):
            reasons.append(f"{t} volatility {comp.vol.at[d, t]:.0%} -> size x{comp.sizing.at[d, t]:.2f}")
        for g in s["signals"]:
            if t in g["apply_to"]:
                st_ = comp.signal_state.at[d, g["id"]]
                word = "unknown" if not np.isfinite(st_) else ("met" if st_ == 1 else "NOT met")
                reasons.append(f"'{g['label']}' {word}")
        if band > 0 and act_day and not move:
            reasons.append(f"within the {band:.0%} no-trade band")
        rows.append(
            {
                "asset": t,
                "action": action,
                "target_share": w,
                "target_amount": w * money,
                "current_amount": float(holdings.get(t, 0.0)),
                "trade_amount": amount if action != "HOLD" else 0.0,
                "when": when,
                "uk_fund": uk_fund(t),
                "exit_rule": exit_rule(s, t),
                "reason": "; ".join(reasons) or "strategy weights",
                "evidence": evidence,
            }
        )
        if action == "BUY":
            buys += amount
    sells = -sum(r["trade_amount"] for r in rows if r["action"] == "SELL")
    cash_after = cash + sells - buys
    acts = [r for r in rows if r["action"] != "HOLD"]
    if acts:

        def short(r):
            code = UK_FUNDS.get(r["asset"], [(r["asset"], "")])[0][0]
            fund = f" (e.g. {code})" if code != r["asset"] else ""
            return f"{r['action']} £{abs(r['trade_amount']):,.0f} of {r['asset']}{fund}"

        headline = "; ".join(short(r) for r in sorted(acts, key=lambda r: r["action"] != "SELL"))
        headline += (
            " (sell first, then buy)"
            if any(r["action"] == "SELL" for r in acts) and any(r["action"] == "BUY" for r in acts)
            else ""
        )
    else:
        headline = "HOLD: no trade needed" + (f" until {nxt.date()}" if nxt is not None and not act_day else "")
    board = Board(s, d, reb, first, rows, next_check=nxt, money=money, cash_after=cash_after, headline=headline)

    # live preview: only while the market is open and today's bar is not complete
    if live and ms["open"] and today > d:
        prev = {t: _with_live_bar(p, live.get(t), today) for t, p in completed.items()}
        try:
            pc = E.compile_targets(s, prev)
            board.preview_date = pc.index[-1]
            for t in uni:
                pw = float(pc.raw_target[t].iloc[-1])
                if abs(pw - tgt[t]) > max(band, 0.01):
                    board.preview_changes.append(
                        f"If {t} closed at today's price, its target would be {pw:.0%} instead of {tgt[t]:.0%}"
                    )
            for g in s["signals"]:
                a, b = comp.signal_state[g["id"]].iloc[-1], pc.signal_state[g["id"]].iloc[-1]
                if np.isfinite(a) and np.isfinite(b) and a != b:
                    board.preview_changes.append(
                        f"'{g['label']}' would flip to {'met' if b == 1 else 'NOT met'} if today closed at this price"
                    )
        except Exception as exc:  # the preview is optional; the official decision stands
            board.preview_changes.append(f"preview unavailable: {exc}")
    return board


def board_text(b: Board) -> str:
    """Plain-text version to copy or download."""
    lines = [
        f"Aurum Decision Board: {b.strategy['name']} (v{b.strategy['version']})",
        f"Decision from the close of {b.official_date.date()} (completed daily prices). Your money: £{b.money:,.2f}.",
        f"Decision: {b.headline}",
        "",
    ]
    for r in b.rows:
        lines.append(
            f"- {r['action']} {r['asset']}: target {r['target_share']:.0%} = £{r['target_amount']:,.2f} "
            f"(now £{r['current_amount']:,.2f}); trade £{abs(r['trade_amount']):,.2f}; when: {r['when']}"
        )
        lines.append(f"    UK fund: {r['uk_fund']}")
        lines.append(f"    Exit rule: {r['exit_rule']}")
        lines.append(f"    Why: {r['reason']}. Evidence: {r['evidence']}")
    if b.next_check is not None:
        lines.append(f"\nNext decision day: about {b.next_check.date()} (after the US close).")
    lines.append(
        "\nThis is what the strategy says based on historical testing, not personal financial advice. "
        "Past results do not guarantee future returns. Aurum never places real-money orders."
    )
    return "\n".join(lines)
