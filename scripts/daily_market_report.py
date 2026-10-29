"""Create a scheduled, read-only market snapshot for Aurum.

Examples:
    python scripts/daily_market_report.py
    python scripts/daily_market_report.py --tickers GLD SLV GDX SPY
    AURUM_OFFLINE=1 python scripts/daily_market_report.py --offline

This is descriptive monitoring, not a trading signal or backtest. No orders are placed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from aurum import data
from aurum.config import CFG, ROOT, all_tickers
from aurum.features import technical_features

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


def build_report(tickers: list[str], cfg: dict = CFG) -> str:
    """Fetch data via Aurum's validated/cache-aware data layer and create a snapshot."""
    now = datetime.now(timezone.utc)
    rows: list[tuple[str, dict]] = []
    failures: list[tuple[str, str]] = []
    for ticker in dict.fromkeys(tickers):
        try:
            prices = data.daily_prices(ticker, cfg=cfg)
            rows.append((ticker, summarise_prices(prices)))
        except Exception as exc:
            failures.append((ticker, f"{type(exc).__name__}: {exc}"))

    lines = [
        "# Aurum Daily Market Snapshot",
        "",
        f"- Generated (UTC): {now.isoformat(timespec='seconds')}",
        f"- Mode: {'synthetic/offline' if cfg.get('offline') else 'market data via Aurum data layer'}",
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
        lines.append(
            f"| {ticker} | {s['last_date']} | {fmt(s['close'], 3)} | {fmt(s['return_1d_pct'])} | "
            f"{fmt(s['return_21d_pct'])} | {fmt(s['return_63d_pct'])} | {fmt(s['return_252d_pct'])} | "
            f"{fmt(s['vol_21d_ann_pct'])} | {fmt(s['rsi_14'])} | {fmt(s['sma50_gap_pct'])} | "
            f"{fmt(s['sma200_gap_pct'])} | {fmt(s['max_drawdown_history_pct'])} |"
        )
    lines += [
        "",
        "## Interpretation guardrails",
        "",
        "- Momentum and RSI describe the recent path; they do not establish positive expected value for a trade.",
        "- SMA gaps are descriptive trend context. Candlestick patterns and technical rules require pre-registered tests "
        "out of sample and after costs.",
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
    print(f"Saved market snapshot to {output}")
    print(report[:3500])


if __name__ == "__main__":
    main()
