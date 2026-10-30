"""Linked decision charts for the Strategy Designer.

One Plotly figure, every panel on the SAME time axis (one x-axis, several y-axis bands), so zooming or panning any
panel moves them all and hovering a date shows, across every panel at once, what the strategy knew at that close
and what it did:

    1  price      candles of the chosen asset, the price-type indicators the rules use (SMA, EMA, Bollinger,
                  Donchian), and buy/sell markers sized by amount, hover = amount, % of account, fill date, reason
    2  indicator  one panel per other indicator a rule uses (RSI, momentum, volatility, ...) with the rule's threshold
                  line and the periods when the condition was met shaded
    3  signals    one strip per rule (met / not met / not yet known) plus the rebalance days
    4  decision   what was decided at each close, as text on hover
    5  holdings   actual share of the account in each asset (stacked) and in cash, with the targets dashed
    6  growth     value of the account against the benchmarks (log scale)
    7  drawdown   fall from the previous peak, strategy and benchmarks

Colours: categorical slots from the dataviz reference palette in fixed order; buy and sell differ by marker shape
(triangle up / down) as well as colour, so identity never relies on colour alone.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from . import spec as SP
from .engine import StrategyRun
from .indicators import INDICATORS

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
STRATEGY, BENCH = SERIES[0], SERIES[1:3]
ASSET_COLOURS = {"SPY": "#6250d6", "GLD": "#eda100"}
OTHER_ASSET = ["#e87ba4", "#1baf7a", "#eb6834", "#2a78d6", "#008300", "#e34948"]
CASH = "#9a9a94"
BUY, SELL = "#008300", "#e34948"
SHADE = "rgba(42,120,214,0.13)"
MUTED = "#8a8f98"
OVERLAY = ["#e87ba4", "#52514e", "#c98500", "#199e70"]  # indicator lines: never a benchmark, asset or buy/sell colour


def asset_colour(t: str, universe: list[str]) -> str:
    if t in ASSET_COLOURS:
        return ASSET_COLOURS[t]
    others = [u for u in universe if u not in ASSET_COLOURS]
    return OTHER_ASSET[others.index(t) % len(OTHER_ASSET)] if t in others else MUTED


def _runs(mask: pd.Series):
    """Start/end dates of each stretch where mask is True."""
    m = mask.fillna(False).astype(bool).to_numpy()
    idx = mask.index
    if not m.any():
        return []
    edges = np.diff(np.r_[0, m.astype(int), 0])
    starts, ends = np.where(edges == 1)[0], np.where(edges == -1)[0] - 1
    return [(idx[a], idx[b]) for a, b in zip(starts, ends)]


def _shade_trace(mask: pd.Series, lo: float, hi: float, yaxis: str, name: str, show_legend: bool):
    xs, ys = [], []
    for a, b in _runs(mask):
        xs += [a, a, b, b, a, None]
        ys += [lo, hi, hi, lo, lo, None]
    return go.Scatter(
        x=xs or [None],
        y=ys or [None],
        fill="toself",
        fillcolor=SHADE,
        line={"width": 0},
        mode="lines",
        name=name,
        hoverinfo="skip",
        yaxis=yaxis,
        showlegend=show_legend,
        legendgroup="shade",
    )


def money(x: float, cur: str) -> str:
    sym = "£" if cur == "GBP" else "$"
    return f"{sym}{x:,.0f}"


def decision_chart(
    run: StrategyRun,
    focus: str,
    benchmarks: dict[str, StrategyRun] | None = None,
    *,
    currency: str = "USD",
    fx: pd.Series | None = None,
    start=None,
    end=None,
    data_label: str = "",
) -> go.Figure:
    """fx: USD per GBP on each date (used only when currency = 'GBP')."""
    s, comp = run.spec, run.compiled
    idx = comp.index
    lo = pd.Timestamp(start) if start is not None else idx[0]
    hi = pd.Timestamp(end) if end is not None else idx[-1]
    view = idx[(idx >= lo) & (idx <= hi)]
    benchmarks = benchmarks or {}
    conv = pd.Series(1.0, index=idx)
    if currency == "GBP" and fx is not None:
        conv = fx.reindex(idx).ffill().bfill()
    prices = _prices_of(run)

    # which indicators to draw where
    price_ops, panel_ops = [], []
    for g in s["signals"]:
        for j, c in enumerate(g["conditions"]):
            for o in (c["left"], c["right"]):
                if not isinstance(o, dict):
                    continue
                lab = SP.operand_label(o)
                kind = INDICATORS[o["ind"]].kind
                if kind == "price" and o["asset"] == focus and o["ind"] != "close":
                    if lab not in [x[0] for x in price_ops]:
                        price_ops.append((lab, o))
                elif kind == "panel":
                    if lab not in [x[0] for x in panel_ops]:
                        panel_ops.append((lab, o, [(g, j, c)]))
                    else:
                        for x in panel_ops:
                            if x[0] == lab:
                                x[2].append((g, j, c))
                elif kind == "price" and o["asset"] != focus and o["ind"] != "close":
                    # a price-type indicator of another asset: draw it with that asset's close in its own panel
                    lab2 = f"{o['asset']} price vs {INDICATORS[o['ind']].describe(o)}"
                    if lab2 not in [x[0] for x in panel_ops]:
                        panel_ops.append((lab2, o, [(g, j, c)]))
    vol_panel = s["sizing"]["method"] in ("vol_cap", "inverse_vol")

    # layout: heights of each band (top to bottom)
    bands = [("price", 3.2)]
    bands += [(f"ind{i}", 1.3) for i in range(len(panel_ops))]
    if vol_panel:
        bands.append(("vol", 1.3))
    n_strips = len(s["signals"]) + 1
    bands += [("signals", 0.35 * n_strips + 0.4), ("hold", 1.6), ("growth", 2.0), ("dd", 1.1)]
    gap = 0.018
    total = sum(h for _, h in bands)
    usable = 1 - gap * (len(bands) - 1)
    domains, top = {}, 1.0
    for name, h in bands:
        size = usable * h / total
        domains[name] = (max(0.0, top - size), top)
        top = top - size - gap
    axis_of = {name: ("y" if i == 0 else f"y{i + 1}") for i, (name, _) in enumerate(bands)}

    fig = go.Figure()
    px = prices[focus].reindex(view)
    ya = axis_of["price"]
    fig.add_trace(
        go.Candlestick(
            x=view,
            open=px["Open"],
            high=px["High"],
            low=px["Low"],
            close=px["Close"],
            name=f"{focus} price",
            yaxis=ya,
            increasing_line_color="#1baf7a",
            decreasing_line_color="#e34948",
            increasing_line_width=1,
            decreasing_line_width=1,
            showlegend=True,
        )
    )
    for k, (lab, _o) in enumerate(price_ops):
        fig.add_trace(
            go.Scatter(
                x=view,
                y=comp.operands[lab].reindex(view),
                name=lab,
                yaxis=ya,
                line={"width": 2, "color": OVERLAY[k % len(OVERLAY)]},
                hovertemplate="%{y:,.2f}",
            )
        )
    tr = run.trades
    if len(tr):
        t = tr[(tr["ticker"] == focus) & (tr["date"] >= view[0]) & (tr["date"] <= view[-1])]
        fill_col = "Open" if s["execution"]["fill"] == "open" else "Close"
        for side, colour, sym in (("BUY", BUY, "triangle-up"), ("SELL", SELL, "triangle-down")):
            q = t[t["side"] == side]
            if not len(q):
                continue
            fx_ = conv.reindex(pd.DatetimeIndex(q["date"])).to_numpy()
            amt = q["notional"].to_numpy() / fx_
            fp = prices[focus][fill_col].reindex(pd.DatetimeIndex(q["date"])).to_numpy()
            size = 8 + 10 * np.sqrt(np.clip(q["pct_of_account"].to_numpy(), 0, 1))
            text = [
                f"<b>{side} {focus} {money(a, currency)}</b> ({pc:.1%} of account)<br>"
                f"filled {pd.Timestamp(fd).date()} at {fpx:,.2f}<br>decided at close of "
                f"{pd.Timestamp(dd).date()}<br>{why}"
                for a, pc, fd, fpx, dd, why in zip(amt, q["pct_of_account"], q["date"], fp, q["decided"], q["reason"])
            ]
            fig.add_trace(
                go.Scatter(
                    x=q["date"],
                    y=fp * (0.985 if side == "BUY" else 1.015),
                    mode="markers",
                    marker={"symbol": sym, "size": size, "color": colour, "line": {"width": 1, "color": "white"}},
                    name=f"{side.title()} orders ({focus})",
                    text=text,
                    hovertemplate="%{text}<extra></extra>",
                    yaxis=ya,
                )
            )

    # indicator panels
    shade_legend = True
    for i, (lab, o, uses) in enumerate(panel_ops):
        ya = axis_of[f"ind{i}"]
        ind = INDICATORS[o["ind"]]
        if ind.kind == "price":  # another asset's price vs its average
            cser = prices[o["asset"]]["Close"].reindex(view)
            iser = comp.operands[SP.operand_label(o)].reindex(view)
            fig.add_trace(
                go.Scatter(x=view, y=cser, name=f"{o['asset']} close", yaxis=ya, line={"width": 1.5, "color": MUTED})
            )
            fig.add_trace(
                go.Scatter(x=view, y=iser, name=SP.operand_label(o), yaxis=ya, line={"width": 2, "color": OVERLAY[0]})
            )
            vals = pd.concat([cser, iser])
        else:
            ser = comp.operands[lab].reindex(view)
            pct = ind.unit == "%"
            fig.add_trace(
                go.Scatter(
                    x=view,
                    y=ser * (100 if pct else 1),
                    name=lab + (" (%)" if pct else ""),
                    yaxis=ya,
                    line={"width": 2, "color": OVERLAY[i % len(OVERLAY)]},
                    hovertemplate="%{y:,.2f}",
                )
            )
            vals = ser * (100 if pct else 1)
            for _g, _j, c in uses:
                other = c["right"] if c["left"] == o else c["left"]
                if isinstance(other, float):
                    yv = other * (100 if pct else 1)
                    fig.add_trace(
                        go.Scatter(
                            x=[view[0], view[-1]],
                            y=[yv, yv],
                            mode="lines",
                            line={"width": 1, "dash": "dash", "color": MUTED},
                            name=f"threshold {yv:g}",
                            yaxis=ya,
                            hoverinfo="skip",
                            showlegend=False,
                        )
                    )
        vmin, vmax = (
            float(np.nanmin(vals)) if len(vals.dropna()) else 0,
            float(np.nanmax(vals)) if len(vals.dropna()) else 1,
        )
        for g, j, _c in uses:
            mask = comp.conditions[f"{g['id']}:{j + 1}"].reindex(view) == 1
            fig.add_trace(_shade_trace(mask, vmin, vmax, ya, "condition met (shaded)", shade_legend))
            shade_legend = False
    if vol_panel:
        ya = axis_of["vol"]
        for t in s["universe"]:
            fig.add_trace(
                go.Scatter(
                    x=view,
                    y=comp.vol[t].reindex(view) * 100,
                    name=f"{t} {s['sizing']['vol_window']}-day volatility (%)",
                    yaxis=ya,
                    line={"width": 1.5, "color": asset_colour(t, s["universe"])},
                    hovertemplate="%{y:.1f}%",
                )
            )
        tv = s["sizing"]["target_vol"] * 100
        fig.add_trace(
            go.Scatter(
                x=[view[0], view[-1]],
                y=[tv, tv],
                mode="lines",
                line={"width": 1, "dash": "dash", "color": MUTED},
                name=f"risk cap {tv:g}%",
                yaxis=ya,
                hoverinfo="skip",
            )
        )
        capped = (comp.sizing.reindex(view) < 0.999).any(axis=1)
        vmax = (
            float(np.nanmax(comp.vol.reindex(view).to_numpy()) * 100)
            if comp.vol.reindex(view).notna().any().any()
            else 1
        )
        fig.add_trace(_shade_trace(capped, 0, vmax, ya, "risk cap cutting a position (shaded)", True))

    # signal strips + decision text
    ya = axis_of["signals"]
    rows = [("Rebalance day", comp.rebalance.reindex(view).astype(float))]
    for g in s["signals"]:
        rows.append((g["label"], comp.signal_state[g["id"]].reindex(view)))
    z = np.vstack([r.to_numpy(float) for _, r in rows])
    fig.add_trace(
        go.Heatmap(
            x=view,
            y=[r[0] for r in rows],
            z=z,
            zmin=0,
            zmax=1,
            colorscale=[[0, "#e6e6e1"], [1, "#2a78d6"]],
            showscale=False,
            yaxis=ya,
            name="rules",
            hovertemplate="%{y}: %{z:.0f} (1 = yes / met)<extra></extra>",
            xgap=0,
            ygap=2,
        )
    )
    ya_h = axis_of["hold"]
    actual = run.result.weights.reindex(view)
    tgt = comp.raw_target.reindex(view)
    orders = _orders_by_decision_day(run, conv, currency)
    dtext = []
    for d in view:
        parts = [f"<b>Close of {d.date()}</b> (completed bars only)"]
        parts.append(
            "Targets: "
            + ", ".join(f"{t} {tgt.at[d, t]:.0%}" for t in s["universe"])
            + f", cash {max(0.0, 1 - tgt.loc[d].sum()):.0%}"
        )
        parts.append("Held: " + ", ".join(f"{t} {actual.at[d, t]:.0%}" for t in s["universe"]))
        if comp.rebalance.at[d]:
            parts.append(orders.get(d, "Rebalance day: within band, no order"))
        else:
            parts.append("No order allowed today (not a rebalance day)")
        dtext.append("<br>".join(parts))
    for t in s["universe"]:
        fig.add_trace(
            go.Scatter(
                x=view,
                y=actual[t] * 100,
                name=f"{t} held (%)",
                stackgroup="held",
                yaxis=ya_h,
                line={"width": 0.5, "color": asset_colour(t, s["universe"])},
                hovertemplate="%{y:.1f}%",
            )
        )
    cash_w = (1 - actual.sum(axis=1)).clip(lower=0) * 100
    fig.add_trace(
        go.Scatter(
            x=view,
            y=cash_w,
            name="cash (%)",
            stackgroup="held",
            yaxis=ya_h,
            line={"width": 0.5, "color": CASH},
            hovertemplate="%{y:.1f}%",
        )
    )
    cum = 0
    for t in s["universe"]:
        cum = cum + tgt[t]
        fig.add_trace(
            go.Scatter(
                x=view,
                y=cum * 100,
                name=f"target up to {t} (%)",
                yaxis=ya_h,
                line={"width": 1.2, "dash": "dot", "color": "#3b3b38"},
                hovertemplate="%{y:.1f}%",
                legendgroup="targets",
            )
        )
    fig.add_trace(
        go.Scatter(
            x=view,
            y=np.full(len(view), 102),
            mode="markers",
            marker={"size": 1, "color": "rgba(0,0,0,0)"},
            text=dtext,
            hovertemplate="%{text}<extra></extra>",
            name="decision",
            yaxis=ya_h,
            showlegend=False,
        )
    )

    # growth and drawdown
    ya_g, ya_d = axis_of["growth"], axis_of["dd"]
    curves = {s["name"]: (run, STRATEGY)}
    for k, (n, b) in enumerate(benchmarks.items()):
        curves[n] = (b, BENCH[k % len(BENCH)])
    for n, (r, col) in curves.items():
        v = r.daily["value"].reindex(view)
        v = v / v.iloc[0] * run.capital / conv.reindex(view)  # dollars, or pounds at each day's exchange rate
        fig.add_trace(
            go.Scatter(
                x=view,
                y=v,
                name=f"{n}: value",
                yaxis=ya_g,
                line={"width": 2 if r is run else 1.5, "color": col},
                hovertemplate=("£" if currency == "GBP" else "$") + "%{y:,.0f}",
                legendgroup=n,
            )
        )
        rr = r.daily["ret"].reindex(view).fillna(0)
        eq = (1 + rr.iloc[1:]).cumprod()
        eq = pd.concat([pd.Series([1.0], index=view[:1]), eq])
        dd = (eq / eq.cummax() - 1) * 100
        fig.add_trace(
            go.Scatter(
                x=view,
                y=dd,
                name=f"{n}: drawdown (%)",
                yaxis=ya_d,
                line={"width": 2 if r is run else 1.2, "color": col},
                fill="tozeroy" if r is run else None,
                fillcolor="rgba(42,120,214,0.10)" if r is run else None,
                hovertemplate="%{y:.1f}%",
                legendgroup=n,
                showlegend=False,
            )
        )

    # axes
    titles = {
        "price": f"{focus} price ($)",
        "vol": "Volatility (%)",
        "signals": "Rules",
        "hold": "Holdings (% of account)",
        "growth": f"Account value ({'£' if currency == 'GBP' else '$'}, log)",
        "dd": "Drawdown (%)",
    }
    for i, (lab, _o, _) in enumerate(panel_ops):
        titles[f"ind{i}"] = lab
    layout = {}
    for name, ax in axis_of.items():
        key = "yaxis" if ax == "y" else f"yaxis{ax[1:]}"
        layout[key] = {
            "domain": list(domains[name]),
            "title": {"text": titles.get(name, name), "font": {"size": 11}},
            "anchor": "x",
            "showgrid": True,
            "gridcolor": "rgba(128,128,128,0.15)",
            "zeroline": False,
            "fixedrange": False,
        }
    layout[("yaxis" if axis_of["growth"] == "y" else f"yaxis{axis_of['growth'][1:]}")]["type"] = "log"
    layout[("yaxis" if axis_of["hold"] == "y" else f"yaxis{axis_of['hold'][1:]}")]["range"] = [0, 104]
    sig_key = f"yaxis{axis_of['signals'][1:]}"
    layout[sig_key]["showgrid"] = False
    layout[sig_key]["tickfont"] = {"size": 10}
    fig.update_layout(
        **layout,
        xaxis={
            "domain": [0, 1],
            "rangeslider": {"visible": False},
            "showspikes": True,
            "spikemode": "across",
            "spikesnap": "cursor",
            "spikethickness": 1,
            "spikecolor": MUTED,
            "type": "date",
            "anchor": "free",
            "position": 0,
            "rangeselector": {
                "buttons": [
                    {"count": 6, "label": "6M", "step": "month", "stepmode": "backward"},
                    {"count": 1, "label": "1Y", "step": "year", "stepmode": "backward"},
                    {"count": 5, "label": "5Y", "step": "year", "stepmode": "backward"},
                    {"step": "all", "label": "All"},
                ],
                "y": 1.0,
                "yanchor": "bottom",
                "x": 1,
                "xanchor": "right",
            },
        },
        hovermode="x unified",
        hoversubplots="axis",
        height=260 + 130 * sum(h for _, h in bands),
        margin={"l": 70, "r": 20, "t": 60, "b": 40},
        legend={"orientation": "h", "y": -0.03, "yanchor": "top", "font": {"size": 10}},
        title={
            "text": f"{s['name']}: every decision, linked panels"
            + (f"<br><sup>{data_label}</sup>" if data_label else ""),
            "font": {"size": 14},
        },
        dragmode="zoom",
        template="plotly_white",
    )
    return fig


def _prices_of(run: StrategyRun) -> dict[str, pd.DataFrame]:
    return run.meta["prices"]


def _orders_by_decision_day(run: StrategyRun, conv: pd.Series, currency: str) -> dict:
    out = {}
    if not len(run.trades):
        return out
    for d, g in run.trades.groupby("decided"):
        items = []
        for _, r in g.iterrows():
            amt = r["notional"] / conv.get(pd.Timestamp(r["date"]), 1.0)
            items.append(
                f"{r['side']} {r['ticker']} {money(amt, currency)} ({r['pct_of_account']:.1%}) at next "
                f"{run.spec['execution']['fill']}"
            )
        out[pd.Timestamp(d)] = "Orders: " + "; ".join(items)
    return out


def comparison_chart(runs: dict[str, StrategyRun], currency: str = "USD", fx: pd.Series | None = None) -> go.Figure:
    """Growth of the same starting money and drawdowns for several strategies on their common dates."""
    idx = None
    for r in runs.values():
        idx = r.daily.index if idx is None else idx.intersection(r.daily.index)
    fig = go.Figure()
    for k, (n, r) in enumerate(runs.items()):
        ret = r.daily["ret"].reindex(idx).fillna(0)
        ret.iloc[0] = 0.0
        eq = (1 + ret).cumprod() * r.capital
        if currency == "GBP" and fx is not None:
            eq = eq / fx.reindex(idx).ffill().bfill()
        col = SERIES[k % len(SERIES)]
        fig.add_trace(go.Scatter(x=idx, y=eq, name=n, line={"width": 2, "color": col}, yaxis="y"))
        dd = (eq / eq.cummax() - 1) * 100
        fig.add_trace(go.Scatter(x=idx, y=dd, name=n, line={"width": 1.5, "color": col}, yaxis="y2", showlegend=False))
    fig.update_layout(
        yaxis={"domain": [0.38, 1], "type": "log", "title": f"Value ({'£' if currency == 'GBP' else '$'}, log)"},
        yaxis2={"domain": [0, 0.32], "title": "Drawdown (%)", "anchor": "x"},
        xaxis={"showspikes": True, "spikemode": "across"},
        hovermode="x unified",
        hoversubplots="axis",
        height=560,
        margin={"l": 70, "r": 20, "t": 30, "b": 30},
        legend={"orientation": "h", "y": 1.08},
        template="plotly_white",
    )
    return fig


def mini_chart(
    p: pd.DataFrame,
    ticker: str,
    *,
    overlays: dict[str, pd.Series] | None = None,
    live: float | None = None,
    months: int = 9,
    title: str = "",
) -> go.Figure:
    """Small indicator chart for the Decision Board: candles with 50- and 200-day averages, any price-type indicator
    the strategy uses, the latest (delayed) price as a dashed line, and RSI 14 underneath. One shared time axis."""
    from .indicators import compute

    full = p.copy()
    start = full.index[-1] - pd.DateOffset(months=months)
    view = full.loc[start:]
    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=view.index,
            open=view["Open"],
            high=view["High"],
            low=view["Low"],
            close=view["Close"],
            name=ticker,
            increasing_line_color="#1baf7a",
            decreasing_line_color="#e34948",
            increasing_line_width=1,
            decreasing_line_width=1,
            showlegend=False,
        )
    )
    lines = {"SMA 50": compute("sma", full, {"n": 50}), "SMA 200": compute("sma", full, {"n": 200})}
    lines.update(overlays or {})
    for k, (name, ser) in enumerate(lines.items()):
        fig.add_trace(
            go.Scatter(
                x=view.index,
                y=ser.reindex(view.index),
                name=name,
                line={"width": 1.6, "color": (["#c98500", "#52514e"] + OVERLAY)[k % (2 + len(OVERLAY))]},
                hovertemplate="%{y:,.2f}",
            )
        )
    if live is not None and np.isfinite(live):
        fig.add_trace(
            go.Scatter(
                x=[view.index[0], view.index[-1]],
                y=[live, live],
                mode="lines",
                line={"width": 1, "dash": "dash", "color": STRATEGY},
                name=f"latest {live:,.2f} (delayed)",
                hoverinfo="skip",
            )
        )
    rsi = compute("rsi", full, {"n": 14}).reindex(view.index)
    fig.add_trace(go.Scatter(x=view.index, y=rsi, name="RSI 14", yaxis="y2", line={"width": 1.4, "color": OVERLAY[0]}))
    for lvl in (30, 70):
        fig.add_trace(
            go.Scatter(
                x=[view.index[0], view.index[-1]],
                y=[lvl, lvl],
                mode="lines",
                yaxis="y2",
                line={"width": 1, "dash": "dot", "color": MUTED},
                hoverinfo="skip",
                showlegend=False,
            )
        )
    fig.update_layout(
        title={"text": title or ticker, "font": {"size": 13}},
        yaxis={"domain": [0.32, 1], "title": "price"},
        yaxis2={"domain": [0, 0.24], "range": [0, 100], "title": "RSI"},
        xaxis={"rangeslider": {"visible": False}, "showspikes": True, "spikemode": "across"},
        hovermode="x unified",
        hoversubplots="axis",
        height=380,
        margin={"l": 50, "r": 10, "t": 40, "b": 20},
        legend={"orientation": "h", "y": 1.12, "font": {"size": 9}},
        template="plotly_white",
    )
    return fig
