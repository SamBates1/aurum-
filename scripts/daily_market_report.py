"""Create a scheduled, read-only market snapshot for Aurum.

Examples:
    python scripts/daily_market_report.py
    python scripts/daily_market_report.py --tickers GLD SLV GDX SPY
    AURUM_OFFLINE=1 python scripts/daily_market_report.py --offline

This is descriptive monitoring, not a trading signal or backtest. No orders are placed.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# `python scripts/daily_market_report.py` puts scripts/ (not the project root) on the import path, so the
# documented command and the scheduled workflow could not import aurum. Add the project root explicitly.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from aurum import data  # noqa: E402
from aurum.config import CFG, ROOT, all_tickers  # noqa: E402
from aurum.features import technical_features  # noqa: E402

DEFAULT_COMPARATORS = ["SPY", "QQQ", "DBC", "TLT"]


def summarise_prices(prices: pd.DataFrame) -> dict[str, float | str]:
    """Summarise price history without using future observations."""
    close = pd.to_numeric(prices["Close"], errors="coerce").dropna()
    if len(close) < 2:
        raise ValueError("At least two valid closing prices are required")
    returns = close.pct_change().dropna()
    features = technical_features(prices.reindex(close.index))
    latest = features.iloc[-1]
    recent_returns = returns.tail(21)
    vol = recent_returns.std(ddof=1) * np.sqrt(252) if len(recent_returns) > 1 else np.nan
    wealth = (1 + returns).cumprod()
    drawdown = wealth / wealth.cummax() - 1
    return {
        "last_date": close.index[-1].date().isoformat(),
        "close": float(close.iloc[-1]),
        "return_1d_pct": float(returns.iloc[-1] * 100),
        "return_21d_pct": float((close.iloc[-1] / close.iloc[-min(22, len(close))] - 1) * 100),
        "return_63d_pct": float((close.iloc[-1] / close.iloc[-min(64, len(close))] - 1) * 100),
        "return_252d_pct": float((close.iloc[-1] / close.iloc[-min(253, len(close))] - 1) * 100),
        "vol_21d_ann_pct": float(vol * 100) if pd.notna(vol) else float("nan"),
        "max_drawdown_history_pct": float(drawdown.min() * 100),
        "rsi_14": float(latest["rsi_14"]) if pd.notna(latest["rsi_14"]) else float("nan"),
        "sma50_gap_pct": float(latest["sma50_gap"] * 100) if pd.notna(latest["sma50_gap"]) else float("nan"),
        "sma200_gap_pct": float(latest["sma200_gap"] * 100) if pd.notna(latest["sma200_gap"]) else float("nan"),
    }


def fmt(value: float, digits: int = 2) -> str:
    return "n/a" if not np.isfinite(value) else f"{value:.{digits}f}"


def extra_sections(closes: dict[str, pd.Series], cfg: dict) -> list[str]:
    """Relative strength, drawdowns, correlations and the adopted strategy's current target weights."""
    if not closes:
        return []
    L = [
        "",
        "## Relative strength and drawdown",
        "",
        "| Rank | Ticker | 126-session return % | Drawdown from 1-year high % |",
        "|---:|---|---:|---:|",
    ]
    rs = {t: float((c.iloc[-1] / c.iloc[-min(127, len(c))] - 1) * 100) for t, c in closes.items()}
    for i, (t, v) in enumerate(sorted(rs.items(), key=lambda kv: -kv[1]), 1):
        dd = (closes[t].iloc[-1] / closes[t].tail(252).max() - 1) * 100
        L.append(f"| {i} | {t} | {fmt(v)} | {fmt(float(dd))} |")
    rets = pd.DataFrame({t: c.pct_change() for t, c in closes.items()}).tail(63)
    refs = [r for r in ("SPY", "GLD") if r in rets]
    if refs and len(rets) > 20:
        corr = rets.corr()
        L += [
            "",
            "## 63-session correlation of daily returns",
            "",
            "| Ticker | " + " | ".join(f"vs {r}" for r in refs) + " |",
            "|---|" + "---:|" * len(refs),
        ]
        L += [f"| {t} | " + " | ".join(fmt(float(corr.loc[t, r])) for r in refs) + " |" for t in corr.index]
    try:  # the adopted strategy's targets (volatility sizing only; never an order)
        from aurum import strategy as S
        from aurum.pipeline import sizing_volatility
        from aurum.volatility import realised_21d

        core = [
            t
            for t in cfg.get("universe", {}).get("core", []) + cfg.get("universe", {}).get("equities", [])
            if t in closes
        ]
        if core:
            sleeve = S.sleeve_weight(len(core), cfg["strategy"]["max_position_pct"])
            L += [
                "",
                "## Adopted strategy: target holdings implied by today's data (no orders placed)",
                "",
                "| Ticker | Sizing volatility % | Target share of sleeve | Target share of account |",
                "|---|---:|---:|---:|",
            ]
            for t in core:
                v21 = realised_21d(closes[t])
                vol, _ = sizing_volatility(v21, closes[t].index, cfg)
                w = float(S.vol_target_weight(vol, cfg["strategy"]["target_vol"]).iloc[-1])
                L.append(f"| {t} | {fmt(float(vol.iloc[-1]) * 100)} | {w:.0%} | {w * sleeve:.1%} |")
    except Exception as exc:  # optional section: report the reason rather than fail the whole report
        L += ["", f"_Strategy targets unavailable: {type(exc).__name__}: {exc}_"]
    return L


def price_chart(closes: dict[str, pd.Series], path: Path) -> Path | None:
    """One-year normalised price chart saved next to the report (descriptive only)."""
    if not closes:
        return None
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 4.5))
    for t, c in closes.items():
        c1 = c.tail(252)
        ax.plot(c1.index, c1 / c1.iloc[0], lw=0.9, label=t)
    ax.set_title("Last 252 sessions, growth of 1 (adjusted closes; not a performance comparison)")
    ax.legend(fontsize=7, ncol=6)
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)
    return path


def build_report(tickers: list[str], cfg: dict = CFG) -> str:
    """Fetch data via Aurum's validated/cache-aware data layer and create a snapshot."""
    now = datetime.now(timezone.utc)
    rows: list[tuple[str, dict]] = []
    failures: list[tuple[str, str]] = []
    closes: dict[str, pd.Series] = {}
    max_stale = int(cfg.get("data", {}).get("max_stale_days", 4))
    for ticker in dict.fromkeys(tickers):
        try:
            prices = data.completed_bars(data.daily_prices(ticker, cfg=cfg), now=now)
            s = summarise_prices(prices)
            age = data.staleness_days(prices, now=now)
            s["age_days"] = age
            s["stale"] = age > max_stale
            close = pd.to_numeric(prices["Close"], errors="coerce").dropna()
            s["drawdown_from_1y_high_pct"] = float((close.iloc[-1] / close.tail(252).max() - 1) * 100)
            closes[ticker] = close
            rows.append((ticker, s))
        except Exception as exc:
            failures.append((ticker, f"{type(exc).__name__}: {exc}"))

    lines = [
        "# Aurum Daily Market Snapshot",
        "",
        f"- Generated (UTC): {now.isoformat(timespec='seconds')}",
        "- Mode: "
        + (
            "**SYNTHETIC/OFFLINE DATA: not market prices**"
            if cfg.get("offline")
            else "end-of-day market data via Aurum's data layer (Yahoo Finance): delayed completed daily bars, not live"
        ),
        f"- A ticker is flagged STALE when its last completed bar is more than {max_stale} calendar days old.",
        "- Purpose: descriptive monitoring only; not a recommendation or evidence of predictive alpha.",
        "- Execution: no orders are created or sent.",
        "",
        "## Cross-asset dashboard",
        "",
        "| Ticker | Last bar | Close | 1d % | 21d % | 63d % | 252d % | 21d ann. vol % | "
        "RSI-14 | vs SMA50 % | vs SMA200 % | Max historical DD % |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for ticker, s in rows:
        flag = " (STALE)" if s.get("stale") else ""
        lines.append(
            f"| {ticker} | {s['last_date']}{flag} | {fmt(s['close'], 3)} | {fmt(s['return_1d_pct'])} | "
            f"{fmt(s['return_21d_pct'])} | {fmt(s['return_63d_pct'])} | {fmt(s['return_252d_pct'])} | "
            f"{fmt(s['vol_21d_ann_pct'])} | {fmt(s['rsi_14'])} | {fmt(s['sma50_gap_pct'])} | "
            f"{fmt(s['sma200_gap_pct'])} | {fmt(s['max_drawdown_history_pct'])} |"
        )
    lines += extra_sections(closes, cfg)
    lines += [
        "",
        "## Interpretation guardrails",
        "",
        "- Momentum and RSI describe the recent path; they do not establish positive expected value for a trade.",
        "- SMA gaps are descriptive trend context. Candlestick patterns and technical rules "
        "require pre-registered tests out of sample and after costs.",
        "- Historical drawdown uses available prices and excludes distributions unless reflected by the data source.",
        "- Compare assets over identical dates with identical fill, cost and risk assumptions before drawing "
        "performance conclusions.",
        "- Market data may be delayed, revised, incomplete or unavailable. Check each last-bar date before relying "
        "on this snapshot.",
        "",
        "## Data retrieval issues",
        "",
    ]
    if failures:
        lines.extend(f"- **{ticker}:** {reason}" for ticker, reason in failures)
    else:
        lines.append("No ticker retrieval failures were reported.")
    if not rows:
        raise RuntimeError("No usable ticker data was available; refusing to write an empty market report.")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tickers", nargs="*", help="tickers to include (default: Aurum universe plus SPY/QQQ/DBC/TLT)"
    )
    parser.add_argument("--offline", action="store_true", help="use synthetic data for a code-path check only")
    parser.add_argument("--output", help="explicit output path; defaults to reports/daily/YYYY-MM-DD.md")
    args = parser.parse_args()
    cfg = dict(CFG)
    if args.offline:
        cfg["offline"] = True
    tickers = args.tickers or (all_tickers(cfg) + DEFAULT_COMPARATORS)
    report = build_report(tickers, cfg=cfg)
    default_output = ROOT / "reports" / "daily" / f"{datetime.now(timezone.utc):%Y-%m-%d}.md"
    output = Path(args.output) if args.output else default_output
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    try:
        closes = {t: data.daily_prices(t, cfg=cfg)["Close"] for t in dict.fromkeys(tickers)}
        price_chart(closes, output.with_suffix(".png"))
    except Exception as exc:
        print(f"Chart skipped: {exc}")
    print(f"Saved market snapshot to {output}")
    print(report[:3500])


if __name__ == "__main__":
    main()
