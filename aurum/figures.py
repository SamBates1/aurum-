"""Standard graph pack (master brief Part F). Every figure is drawn from experiment outputs passed in, saved under
<result folder>/figures/, and carries a footer with the experiment ID, period, universe, return convention and
cost assumption, so charts can be compared across experiments. Nothing here invents data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def _plt():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


class FigurePack:
    def __init__(self, out_dir: Path, exp_id: str, universe: str, costs: str, split: str, note: str = ""):
        self.dir = Path(out_dir) / "figures"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.exp, self.universe, self.costs, self.split, self.note = exp_id, universe, costs, split, note
        self.index: list[tuple[str, str]] = []

    def _save(self, fig, name: str, title: str, period: str, convention: str = "net of costs"):
        footer = f"{self.exp} | {period} | {self.universe} | {convention} | costs: {self.costs} | {self.split}" + (
            f" | {self.note}" if self.note else ""
        )
        fig.text(0.01, 0.005, footer, fontsize=6.5, color="#555", ha="left", va="bottom", wrap=True)
        fig.tight_layout(rect=(0, 0.03, 1, 1))
        path = self.dir / f"{name}.png"
        fig.savefig(path, dpi=110)
        _plt().close(fig)
        self.index.append((title, f"figures/{name}.png"))
        return path

    @staticmethod
    def _period(rets: dict[str, pd.Series]) -> str:
        idx = pd.concat(rets.values(), axis=1).dropna(how="all").index
        return f"{idx[0].date()} to {idx[-1].date()}" if len(idx) else "no data"

    # ---------------- performance ----------------
    def equity_drawdown(self, rets: dict[str, pd.Series], name="equity_drawdown"):
        plt = _plt()
        fig, ax = plt.subplots(2, 1, figsize=(10, 7), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
        for k, r in rets.items():
            eq = (1 + r.fillna(0)).cumprod()
            ax[0].plot(eq.index, eq, label=k, lw=1.1)
            ax[1].plot(eq.index, eq / eq.cummax() - 1, lw=0.9)
        ax[0].set_yscale("log")
        ax[0].set_ylabel("Growth of 1 (log scale)")
        ax[0].legend(fontsize=8)
        ax[1].set_ylabel("Drawdown (underwater)")
        ax[0].set_title("Cumulative return and drawdown (historical simulation)")
        return self._save(fig, name, "Equity curves and drawdowns", self._period(rets))

    def rolling(self, rets: dict[str, pd.Series], bench: pd.Series | None = None, name="rolling"):
        plt = _plt()
        n = 4 if bench is not None else 3
        fig, ax = plt.subplots(n, 1, figsize=(10, 2.4 * n), sharex=True)
        for k, r in rets.items():
            ax[0].plot((1 + r).rolling(252).apply(np.prod, raw=True) - 1, label=k, lw=0.9)
            ax[1].plot(r.rolling(63).std() * np.sqrt(TRADING_DAYS), lw=0.9)
            ax[2].plot(r.rolling(252).mean() / r.rolling(252).std() * np.sqrt(TRADING_DAYS), lw=0.9)
            if bench is not None:
                ax[3].plot(r.rolling(252).corr(bench), lw=0.9)
        ax[0].set_ylabel("252-day return")
        ax[1].set_ylabel("63-day vol (ann.)")
        ax[2].set_ylabel("252-day Sharpe*")
        if bench is not None:
            ax[3].set_ylabel("252-day corr. vs SPY")
        ax[0].legend(fontsize=7)
        ax[0].set_title("Rolling statistics (*Sharpe on raw returns, risk-free not deducted)")
        return self._save(fig, name, "Rolling return, volatility, Sharpe and correlation", self._period(rets))

    def exposure(self, weights: pd.DataFrame, name="exposure_weights", label="strategy"):
        plt = _plt()
        fig, ax = plt.subplots(figsize=(10, 4))
        w = weights.fillna(0)
        ax.stackplot(w.index, w.T.to_numpy(), labels=w.columns, alpha=0.85)
        ax.plot(w.index, 1 - w.sum(axis=1), color="k", lw=0.6, label="cash")
        ax.set_ylim(0, max(1.05, float(w.sum(axis=1).max()) + 0.05))
        ax.legend(fontsize=7, ncol=6, loc="upper left")
        ax.set_ylabel("Share of equity")
        ax.set_title(f"Position weights and cash over time: {label}")
        return self._save(fig, name, f"Exposure and weights ({label})", f"{w.index[0].date()} to {w.index[-1].date()}")

    def turnover_costs(self, daily: dict[str, pd.DataFrame], name="turnover_costs"):
        plt = _plt()
        fig, ax = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
        for k, d in daily.items():
            to = (d["traded"] / d["value"]).groupby(d.index.year).sum()
            co = (d["cost"] / d["value"]).groupby(d.index.year).sum()
            ax[0].plot(to.index, to, marker="o", ms=3, label=k)
            ax[1].plot(co.index, co * 1e4, marker="o", ms=3)
        ax[0].set_ylabel("Turnover per year (x equity)")
        ax[1].set_ylabel("Costs per year (bps of equity)")
        ax[0].legend(fontsize=7)
        return self._save(fig, name, "Turnover and transaction costs by year", "by calendar year")

    def gross_vs_net(self, gross: pd.Series, net: pd.Series, name="gross_vs_net"):
        plt = _plt()
        fig, ax = plt.subplots(figsize=(10, 4))
        for k, r in (("gross", gross), ("net", net)):
            ax.plot((1 + r.fillna(0)).cumprod(), label=k)
        ax.set_yscale("log")
        ax.legend()
        ax.set_title("Gross vs net of transaction costs")
        return self._save(fig, name, "Gross vs net returns", self._period({"n": net}), "gross and net")

    def annual(self, rets: dict[str, pd.Series], name="annual_returns"):
        plt = _plt()
        yr = pd.DataFrame({k: (1 + r).groupby(r.index.year).prod() - 1 for k, r in rets.items()})
        fig, ax = plt.subplots(figsize=(11, 4))
        yr.plot.bar(ax=ax, width=0.8)
        ax.axhline(0, color="k", lw=0.5)
        ax.set_ylabel("Calendar-year return")
        ax.legend(fontsize=7)
        return self._save(fig, name, "Calendar-year returns", self._period(rets))

    def distribution(self, rets: dict[str, pd.Series], name="return_distribution"):
        plt = _plt()
        fig, ax = plt.subplots(1, 2, figsize=(11, 4))
        for k, r in rets.items():
            m = (1 + r).groupby([r.index.year, r.index.month]).prod() - 1
            ax[0].hist(r.dropna(), bins=80, alpha=0.45, label=k, density=True)
            ax[1].hist(m, bins=40, alpha=0.45, label=k, density=True)
        ax[0].set_title("Daily returns")
        ax[1].set_title("Monthly returns")
        ax[0].legend(fontsize=7)
        ax[0].set_yscale("log")
        return self._save(fig, name, "Return distributions (daily and monthly)", self._period(rets))

    def tails(self, rets: dict[str, pd.Series], name="tail_risk"):
        plt = _plt()
        rows = []
        for k, r in rets.items():
            r = r.dropna()
            q = r.quantile(0.05)
            eq = (1 + r).cumprod()
            rows.append((k, r.min(), r[r <= q].mean(), (eq / eq.cummax() - 1).min()))
        t = pd.DataFrame(rows, columns=["", "worst day", "CVaR 5% (day)", "max drawdown"]).set_index("")
        fig, ax = plt.subplots(figsize=(9, 3.5))
        t.plot.barh(ax=ax)
        ax.set_title("Tail losses")
        return self._save(fig, name, "Tail-loss comparison", self._period(rets))

    def regimes(self, table: pd.DataFrame, name="regimes"):
        plt = _plt()
        fig, ax = plt.subplots(figsize=(9, 4))
        table.plot.bar(ax=ax)
        ax.axhline(0, color="k", lw=0.5)
        ax.set_ylabel("Annualised mean return")
        ax.set_title("Performance by market regime")
        return self._save(fig, name, "Performance by regime", "whole sample")

    # ---------------- robustness ----------------
    def heatmap(self, grid: pd.DataFrame, title: str, name: str, fmt: str = "{:.2f}", period: str = "whole sample"):
        plt = _plt()
        fig, ax = plt.subplots(figsize=(1.1 * grid.shape[1] + 3, 0.5 * grid.shape[0] + 2))
        im = ax.imshow(grid.to_numpy(float), cmap="RdYlGn", aspect="auto")
        ax.set_xticks(range(grid.shape[1]), [str(c) for c in grid.columns], rotation=45, ha="right", fontsize=7)
        ax.set_yticks(range(grid.shape[0]), [str(i) for i in grid.index], fontsize=7)
        for i in range(grid.shape[0]):
            for j in range(grid.shape[1]):
                v = grid.iat[i, j]
                if np.isfinite(v):
                    ax.text(j, i, fmt.format(v), ha="center", va="center", fontsize=6)
        fig.colorbar(im, ax=ax, fraction=0.03)
        ax.set_title(title, fontsize=9)
        return self._save(fig, name, title, period)

    def lines(self, df: pd.DataFrame, title: str, name: str, xlabel: str, ylabel: str, period="whole sample"):
        plt = _plt()
        fig, ax = plt.subplots(figsize=(8, 4))
        df.plot(ax=ax, marker="o", ms=3)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=9)
        ax.axhline(0, color="k", lw=0.4)
        return self._save(fig, name, title, period)

    def by_period(self, table: pd.DataFrame, title: str, name: str):
        """Bars: one group per period (pre / dev / holdout or walk-forward fold), one bar per strategy."""
        plt = _plt()
        fig, ax = plt.subplots(figsize=(10, 4))
        table.plot.bar(ax=ax)
        ax.axhline(0, color="k", lw=0.5)
        ax.set_title(title, fontsize=9)
        ax.legend(fontsize=7)
        return self._save(fig, name, title, "by period")

    # ---------------- prediction ----------------
    def calibration_roc(self, probs: pd.Series, labels: pd.Series, name: str, label: str):
        from sklearn.metrics import roc_curve

        plt = _plt()
        p, y = probs.align(labels, join="inner")
        m = p.notna() & y.notna()
        p, y = p[m], y[m]
        fig, ax = plt.subplots(1, 3, figsize=(12, 3.8))
        if len(p) > 50 and y.nunique() == 2:
            bins = pd.qcut(p, 10, duplicates="drop")
            cal = pd.DataFrame({"p": p, "y": y}).groupby(bins, observed=True).mean()
            ax[0].plot(cal["p"], cal["y"], marker="o")
            ax[0].plot([0, 1], [0, 1], "k--", lw=0.6)
            ax[0].set_xlim(min(cal["p"].min(), 0.3), max(cal["p"].max(), 0.7))
            ax[0].set_ylim(0.2, 0.8)
            fpr, tpr, _ = roc_curve(y, p)
            ax[1].plot(fpr, tpr)
            ax[1].plot([0, 1], [0, 1], "k--", lw=0.6)
            ax[2].hist(p, bins=40)
        ax[0].set_title("Calibration (predicted vs actual)")
        ax[1].set_title("ROC (out of sample)")
        ax[2].set_title("Prediction distribution")
        return self._save(
            fig,
            name,
            f"Calibration, ROC and predictions: {label}",
            self._period({"p": p}),
            "out-of-sample walk-forward predictions",
        )

    def bars(self, s: pd.Series, title: str, name: str, ylabel: str, period="whole sample"):
        plt = _plt()
        fig, ax = plt.subplots(figsize=(9, max(3, 0.25 * len(s) + 1)))
        s.sort_values().plot.barh(ax=ax)
        ax.set_xlabel(ylabel)
        ax.set_title(title, fontsize=9)
        ax.axvline(0, color="k", lw=0.5)
        return self._save(fig, name, title, period)

    def candles(self, p: pd.DataFrame, marks: dict[str, pd.Series], name: str, label: str, days: int = 120):
        """Candlestick chart of the last `days` sessions with SMA/EMA, Bollinger bands, volume and pattern markers."""
        plt = _plt()
        d = p.iloc[-days:]
        c = p["Close"]
        fig, ax = plt.subplots(3, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1, 1]})
        x = np.arange(len(d))
        up = d["Close"] >= d["Open"]
        ax[0].vlines(x, d["Low"], d["High"], color=np.where(up, "#2E9E6A", "#D1495B"), lw=0.8)
        ax[0].bar(
            x,
            (d["Close"] - d["Open"]).abs(),
            bottom=np.minimum(d["Open"], d["Close"]),
            color=np.where(up, "#2E9E6A", "#D1495B"),
            width=0.6,
        )
        for n, col in ((50, "#C9A227"), (200, "#555")):
            ax[0].plot(x, c.rolling(n).mean().iloc[-days:].to_numpy(), lw=0.9, color=col, label=f"SMA{n}")
        ax[0].plot(x, c.ewm(span=20, adjust=False).mean().iloc[-days:].to_numpy(), lw=0.8, ls="--", label="EMA20")
        mid, sd = c.rolling(20).mean().iloc[-days:], c.rolling(20).std().iloc[-days:]
        ax[0].fill_between(x, (mid - 2 * sd).to_numpy(), (mid + 2 * sd).to_numpy(), alpha=0.1, label="Bollinger 20/2")
        hi, lo = c.shift().rolling(50).max().iloc[-days:], c.shift().rolling(20).min().iloc[-days:]
        ax[0].plot(x, hi.to_numpy(), lw=0.5, ls=":", color="b", label="Donchian 50 high")
        ax[0].plot(x, lo.to_numpy(), lw=0.5, ls=":", color="r", label="Donchian 20 low")
        for i, (k, m) in enumerate(marks.items()):
            mm = m.reindex(d.index).fillna(False).to_numpy(bool)
            ax[0].scatter(x[mm], d["Low"].to_numpy()[mm] * (0.985 - 0.006 * i), marker="^", s=14, label=k)
        ax[0].legend(fontsize=6, ncol=4)
        ax[1].bar(x, d["Volume"], color="#888")
        ax[1].set_ylabel("Volume")
        from .features import rsi

        ax[2].plot(x, rsi(c).iloc[-days:].to_numpy(), lw=0.9)
        ax[2].axhline(70, ls="--", lw=0.5)
        ax[2].axhline(30, ls="--", lw=0.5)
        ax[2].set_ylabel("RSI 14")
        ax[2].set_xticks(x[:: max(1, days // 8)], [str(t.date()) for t in d.index[:: max(1, days // 8)]], fontsize=7)
        ax[0].set_title(f"{label}: last {days} sessions with indicators and pattern markers")
        return self._save(
            fig,
            name,
            f"Candlestick chart with indicators: {label}",
            f"{d.index[0].date()} to {d.index[-1].date()}",
            "prices (adjusted)",
        )

    def corr_heatmap(self, rets: pd.DataFrame, name="correlation", title="Correlation of daily returns"):
        return self.heatmap(rets.corr(), title, name, period=f"{rets.index[0].date()} to {rets.index[-1].date()}")

    def markdown_index(self) -> list[str]:
        return ["## Figures", ""] + [f"- [{t}]({p})" for t, p in self.index]
