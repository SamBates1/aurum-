"""UK-investor and long-history studies (EXP-046, EXP-047, EXP-048; pre-registered 2026-10-30).

EXP-046  daily 2006-2026: the 70/30 strategies accounted in pounds through UK-listed funds (VUSA, SGLN) with their
         fees, dividend withholding, a platform fee and the UK cash rate; decisions still come from the US prices.
EXP-047  monthly 1972-2026: S&P 500 total return (Shiller), gold (World Bank), pounds per dollar; 70/30 vs 100% S&P.
EXP-048  outcome ranges for the owner's money by stationary block bootstrap of EXP-047's monthly pound returns.

Long-history files come from github.com/datasets (open data mirrors of Shiller's S&P data, the World Bank Pink Sheet
gold price and Federal Reserve exchange rates). They are MONTHLY AVERAGES: falls within a month are smoothed, so worst
falls look smaller than with daily data. EXP-047 measures that effect on 2006-2026 against the daily results.
"""

from __future__ import annotations

import io

import numpy as np
import pandas as pd

from . import data
from . import engine as E
from . import spec as SP
from .portfolio import simulate_portfolio
from .stats import stationary_bootstrap_indices

TRADING_DAYS = 252
SPX_URL = "https://raw.githubusercontent.com/datasets/s-and-p-500/main/data/data.csv"
GOLD_URL = "https://raw.githubusercontent.com/datasets/gold-prices/main/data/monthly.csv"
FX_URL = "https://raw.githubusercontent.com/datasets/exchange-rates/main/data/monthly.csv"

# EXP-046 cost assumptions (fixed before running; annual, as decimals)
UK_FUND_DRAG = {"SPY": 0.0022, "GLD": -0.0028}  # UK fund cost minus the US ETF cost already in its price
PLATFORM_FEE = 0.0025
UK_TRADE_BPS = 5.0
UK_FUNDS_YAHOO = {"SPY": "VUSA.L", "GLD": "SGLN.L"}
# EXP-047 assumptions
LONG_TRADE_COST = 0.0010
LONG_FUND_FEE = {"spx": 0.0020, "gold": 0.0025}

BEAR_MARKETS = {
    "1973-74 oil shock": ("1973-01", "1974-12"),
    "1980-82 recession": ("1980-12", "1982-08"),
    "1987 crash": ("1987-08", "1987-12"),
    "2000-02 dot-com": ("2000-08", "2002-10"),
    "2007-09 financial crisis": ("2007-10", "2009-03"),
    "2020 Covid": ("2020-02", "2020-04"),
    "2022 rate rises": ("2022-01", "2022-10"),
}
SUBPERIODS = {"1972-1989": ("1972-01", "1989-12"), "1990-2007": ("1990-01", "2007-12"), "2008-2026": ("2008-01", None)}


# ---------------------------------------------------------------------------------------------------------------
# long monthly data
# ---------------------------------------------------------------------------------------------------------------
def _csv(name: str, url: str, cfg) -> pd.DataFrame:
    def fetch():
        df = pd.read_csv(io.BytesIO(data._http_bytes(url)))
        df.index = pd.to_datetime(df["Date"])  # the cache expects a date index; "Date" is kept as a column too
        df.index.name = "idx"
        return df

    return data._cached(name, f"github:{url}", fetch, cfg["data"]["cache_hours"])


def spx_total_return(raw: pd.DataFrame) -> tuple[pd.Series, dict]:
    """Monthly S&P 500 total return from Shiller data: (P_t + D_t / 12) / P_{t-1} - 1, D = annual dividend.
    Months after the last reported dividend use the last known dividend yield (stated in the report)."""
    df = raw.copy()
    df.index = pd.to_datetime(df["Date"]).dt.to_period("M").dt.to_timestamp()
    p, d = df["SP500"].astype(float), df["Dividend"].astype(float)
    known = d > 0
    last = d[known].index[-1]
    yld = float(d[known].iloc[-1] / p[known].iloc[-1])
    d = d.where(known | (d.index <= last), p * yld)
    r = (p + d / 12) / p.shift(1) - 1
    return r.dropna(), {"dividends_known_until": str(last.date())[:7], "filled_yield": yld}


def gold_monthly(raw: pd.DataFrame) -> pd.Series:
    df = raw.copy()
    s = pd.Series(
        df["Price"].astype(float).to_numpy(), index=pd.to_datetime(df["Date"]).dt.to_period("M").dt.to_timestamp()
    )
    return s.pct_change(fill_method=None).dropna()


def gbp_per_usd(raw: pd.DataFrame) -> pd.Series:
    df = raw[raw["Country"] == "United Kingdom"].copy()
    s = pd.Series(
        df.iloc[:, -1].astype(float).to_numpy(), index=pd.to_datetime(df["Date"]).dt.to_period("M").dt.to_timestamp()
    )
    return s.sort_index()


def long_data(cfg=None) -> dict:
    """Monthly returns (USD), pounds per dollar and cash rates. Cash rates come from FRED where reachable."""
    from .config import CFG

    cfg = cfg or CFG
    spx, info = spx_total_return(_csv("LONG_SPX", SPX_URL, cfg))
    gold = gold_monthly(_csv("LONG_GOLD", GOLD_URL, cfg))
    fx = gbp_per_usd(_csv("LONG_FX", FX_URL, cfg))
    cash = {}
    for k, sid in (("usd", "TB3MS"), ("gbp", "IR3TIB01GBM156N")):
        try:
            s = data.fred(sid, cfg) / 100
            s.index = s.index.to_period("M").to_timestamp()
            cash[k] = s.groupby(level=0).last()
        except Exception as exc:
            cash[k] = None
            info[f"cash_{k}_error"] = str(exc)[:120]
    return {"spx": spx, "gold": gold, "fx": fx, "cash": cash, "info": info}


def to_gbp(r_usd: pd.Series, gbp_per_usd_: pd.Series) -> pd.Series:
    """Pound return of a dollar asset: (1 + r) x (pounds per dollar now / pounds per dollar a month ago) - 1."""
    fx = gbp_per_usd_.reindex(r_usd.index.union(gbp_per_usd_.index)).ffill()
    ch = fx / fx.shift(1)
    return ((1 + r_usd) * ch.reindex(r_usd.index) - 1).dropna()


def monthly_mix(
    rets: pd.DataFrame, weights: dict, trade_cost: float, fees: dict, platform_fee: float = 0.0
) -> pd.Series:
    """Monthly portfolio rebalanced to `weights` at the start of every month, drifting within the month; trading
    cost on the value traded at each rebalance, annual fund and platform fees charged monthly."""
    cols = list(weights)
    w = np.array([weights[c] for c in cols], float)
    R = rets[cols].to_numpy(float)
    fee = np.array([fees.get(c, 0.0) for c in cols]) / 12
    out = np.empty(len(R))
    held = w.copy()
    for i, r in enumerate(R):
        turnover = np.abs(w - held).sum() if i else w.sum()
        gross = float(np.dot(w, 1 + r - fee))
        out[i] = gross - 1 - trade_cost * turnover - platform_fee / 12
        held = w * (1 + r) / gross if gross > 0 else w
    return pd.Series(out, index=rets.index)


def mstats(r: pd.Series, cash_annual: pd.Series | None = None) -> dict:
    r = r.dropna()
    if len(r) < 2:
        return {}
    eq = (1 + r).cumprod()
    years = len(r) / 12
    rf = (cash_annual.reindex(r.index).ffill().bfill().fillna(0) / 12) if cash_annual is not None else 0.0
    ex = r - rf
    dd = eq / eq.cummax() - 1
    return {
        "start": str(r.index[0].date())[:7],
        "end": str(r.index[-1].date())[:7],
        "cagr": float(eq.iloc[-1] ** (1 / years) - 1),
        "volatility": float(r.std(ddof=1) * np.sqrt(12)),
        "sharpe": float(ex.mean() / ex.std(ddof=1) * np.sqrt(12)) if ex.std(ddof=1) > 0 else np.nan,
        "max_drawdown": float(dd.min()),
        "worst_year": float(((1 + r).groupby(r.index.year).prod() - 1).min()),
    }


def window(r: pd.Series, lo: str, hi: str | None) -> float:
    s = r.loc[lo:hi]
    return float((1 + s).prod() - 1) if len(s) else np.nan


def rolling_cagr(r: pd.Series, months: int = 120) -> pd.Series:
    g = np.log1p(r).rolling(months).sum()
    return np.expm1(g * 12 / months).dropna()


def long_study(ld: dict, start: str = "1972-01") -> dict:
    """EXP-047: monthly 70/30 vs 100% S&P vs 100% gold, in dollars and pounds."""
    rets = pd.concat({"spx": ld["spx"], "gold": ld["gold"]}, axis=1).dropna().loc[start:]
    gbp = pd.concat({"spx": to_gbp(rets["spx"], ld["fx"]), "gold": to_gbp(rets["gold"], ld["fx"])}, axis=1).dropna()
    out = {}
    for cur, R, cash in (("USD", rets, ld["cash"].get("usd")), ("GBP", gbp, ld["cash"].get("gbp"))):
        series = {
            "S&P 500": monthly_mix(R, {"spx": 1.0}, LONG_TRADE_COST, LONG_FUND_FEE),
            "70/30 S&P/gold": monthly_mix(R, {"spx": 0.7, "gold": 0.3}, LONG_TRADE_COST, LONG_FUND_FEE),
            "Gold": monthly_mix(R, {"gold": 1.0}, LONG_TRADE_COST, LONG_FUND_FEE),
        }
        out[cur] = {"returns": series, "cash": cash}
    return out


def long_tests(study: dict) -> dict:
    res = {}
    for cur, v in study.items():
        s, m = v["returns"]["S&P 500"], v["returns"]["70/30 S&P/gold"]
        bears = {k: (window(s, a, b), window(m, a, b)) for k, (a, b) in BEAR_MARKETS.items()}
        subs = {
            k: (mstats(s.loc[a:b], v["cash"]).get("sharpe"), mstats(m.loc[a:b], v["cash"]).get("sharpe"))
            for k, (a, b) in SUBPERIODS.items()
        }
        full = (mstats(s, v["cash"]), mstats(m, v["cash"]))
        rs, rm = rolling_cagr(s), rolling_cagr(m)
        common = rs.index.intersection(rm.index)
        res[cur] = {
            "test1_all_bears_smaller_fall": all(b[1] > b[0] for b in bears.values() if np.isfinite(b[0])),
            "test2_sharpe": bool(
                full[1]["sharpe"] > full[0]["sharpe"] and sum(sm > ss for ss, sm in subs.values()) >= 2
            ),
            "test3_worst_decade": bool(rm.min() > rs.min()),
            "bears": bears,
            "subperiods": subs,
            "full": full,
            "worst_10y": (float(rs.min()), float(rm.min())),
            "share_10y_7030_better": float((rm.loc[common] > rs.loc[common]).mean()),
            "decades": {
                f"{d}s": (window(s, f"{d}-01", f"{d + 9}-12"), window(m, f"{d}-01", f"{d + 9}-12"))
                for d in (1970, 1980, 1990, 2000, 2010, 2020)
            },
        }
    return res


# ---------------------------------------------------------------------------------------------------------------
# EXP-046: daily, in pounds
# ---------------------------------------------------------------------------------------------------------------
def gbp_frame(p_usd: pd.DataFrame, usd_per_gbp: pd.Series, drag_annual: float) -> pd.DataFrame:
    """OHLC of a US ETF converted to pounds at each day's rate, with a daily cost drag for the UK fund."""
    fx = usd_per_gbp.reindex(p_usd.index.union(usd_per_gbp.index)).ffill().reindex(p_usd.index)
    k = np.exp(-drag_annual * np.arange(len(p_usd)) / TRADING_DAYS)
    out = p_usd[["Open", "High", "Low", "Close"]].div(fx, axis=0).mul(k, axis=0)
    out["Volume"] = p_usd.get("Volume", np.nan)
    return out.dropna(subset=["Close"])


def uk_cash_daily(index: pd.DatetimeIndex, cfg) -> pd.Series | float:
    """UK 3-month rate (monthly, FRED), assumed known one month after the month it describes."""
    try:
        s = data.fred("IR3TIB01GBM156N", cfg) / 100
        s.index = s.index + pd.offsets.MonthBegin(1)
        return s.reindex(index.union(s.index)).ffill().reindex(index).fillna(0.0)
    except Exception:
        return 0.0


def run_in_gbp(
    spec: dict, usd: dict, gbp: dict, rf_gbp, *, platform_fee: float = PLATFORM_FEE, trade_bps: float = UK_TRADE_BPS
) -> E.StrategyRun:
    """Decisions from the US prices (as the bot makes them); accounting in pounds with UK fund costs."""
    s = SP.validate(spec)
    idx = None
    for t in s["universe"]:
        idx = gbp[t].index if idx is None else idx.intersection(gbp[t].index)
    comp = E.compile_targets(s, usd, idx)
    res = simulate_portfolio(
        {t: gbp[t].reindex(idx) for t in s["universe"]},
        comp.target,
        cost_bps={t: trade_bps for t in s["universe"]},
        cash_rate=rf_gbp,
        band=s["schedule"]["band"],
        fill=s["execution"]["fill"],
        initial=1.0,
    )
    d = res.daily.copy()
    d["ret"] = d["ret"] - platform_fee / TRADING_DAYS
    d["value"] = (1 + d["ret"]).cumprod()
    res.daily = d
    return E.StrategyRun(
        s, comp, res, res.trades.assign(decided=pd.NaT, pct_of_account=np.nan, reason=""), 1.0, rf_gbp, {}
    )


def tracking_check(model: pd.Series, actual: pd.Series) -> dict:
    """Annualised return of modelled vs actual UK fund prices over their common dates; days with a >40% move in the
    actual series are treated as unit changes (pence/pounds) and excluded."""
    a = actual.dropna()
    ra = a.pct_change(fill_method=None)
    bad = ra.abs() > 0.4
    ra = ra[~bad]
    rm = model.pct_change(fill_method=None)
    common = ra.index.intersection(rm.index)
    common = common[common >= max(a.index[0], model.index[0]) + pd.Timedelta(days=5)]
    if len(common) < 250:
        return {"years": len(common) / TRADING_DAYS, "diff": np.nan}
    years = len(common) / TRADING_DAYS
    ga = float(np.prod(1 + ra.loc[common]) ** (1 / years) - 1)
    gm = float(np.prod(1 + rm.loc[common]) ** (1 / years) - 1)
    return {
        "start": str(common[0].date()),
        "end": str(common[-1].date()),
        "years": years,
        "actual_cagr": ga,
        "model_cagr": gm,
        "diff": gm - ga,
        "excluded_days": int(bad.sum()),
        "correlation": float(ra.loc[common].corr(rm.loc[common])),
    }


# ---------------------------------------------------------------------------------------------------------------
# EXP-048: outcome ranges
# ---------------------------------------------------------------------------------------------------------------
def outcomes(
    r: pd.Series,
    *,
    lump: float,
    monthly: float,
    horizons=(12, 36, 60, 120),
    reps: int = 10_000,
    block: float = 12,
    seed: int = 42,
) -> pd.DataFrame:
    x = r.dropna().to_numpy(float)
    rng = np.random.default_rng(seed)
    idx = stationary_bootstrap_indices(len(x), block, reps, rng)
    rows = []
    for h in horizons:
        R = x[idx[:, :h]]
        value = np.full(reps, float(lump))
        paid = float(lump)
        twr = np.ones(reps)
        peak = np.ones(reps)
        worst = np.zeros(reps)
        for m in range(h):
            if m > 0 and monthly:
                value += monthly
                paid += monthly
            value *= 1 + R[:, m]
            twr *= 1 + R[:, m]
            peak = np.maximum(peak, twr)
            worst = np.minimum(worst, twr / peak - 1)
        pct = np.percentile(value, [5, 25, 50, 75, 95])
        rows.append(
            {
                "years": h / 12,
                "paid_in": paid,
                "p5": pct[0],
                "p25": pct[1],
                "median": pct[2],
                "p75": pct[3],
                "p95": pct[4],
                "chance_below_paid_in": float(np.mean(value < paid)),
                "chance_fall_20pct": float(np.mean(worst <= -0.20)),
                "median_worst_fall": float(np.median(worst)),
            }
        )
    return pd.DataFrame(rows)
