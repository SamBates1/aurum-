"""Platform phase 10: monitoring alerts, drift alarms, pot statistics, and the whole research-to-paper-order flow
on controlled data with a fake broker (no network, no real orders)."""

import numpy as np
import pandas as pd
import pytest
from test_broker import FakeAlpaca

from aurum import assessment as AS
from aurum import broker as BR
from aurum import factorlab as FL
from aurum import investplan as IP
from aurum import monitoring as MO
from aurum import portfolio_opt as PO
from aurum import recommendations as RC
from aurum import scanner as SC
from aurum import spec as SP
from aurum import universe as U


def test_position_alerts_and_risk():
    pos = {"AAA": {"qty": 10, "cost": 1000}, "BBB": {"qty": 5, "cost": 500}, "CCC": {"qty": 1, "cost": 10}}
    plans = {"AAA": {"stop": 95.0, "targets": [("2R", 110.0, 2.0)]}, "BBB": {"stop": 90.0, "targets": [("2R", 120, 2)]}}
    al = MO.position_alerts(
        pos, {"AAA": 96.0, "BBB": 121.0}, plans, {"BBB": "REDUCE"}, {"AAA": 3.0}, {"BBB": 40.0}, ("ZZZ", 90.0)
    )
    kinds = {(a.symbol, a.kind) for a in al}
    assert ("AAA", "stop") in kinds and ("BBB", "target") in kinds and ("BBB", "thesis") in kinds
    assert ("BBB", "opportunity") in kinds and ("CCC", "data") in kinds
    assert MO.risk_alert(0.25)[0].kind == "risk" and MO.risk_alert(0.10) == []


def test_drift_alarm_and_pot_stats():
    idx = pd.bdate_range("2026-01-01", periods=120)
    calm = pd.Series(100 * np.exp(np.cumsum(np.full(120, 0.0005))), index=idx)
    assert MO.drift_check(calm.iloc[:10], 0.12, -0.25)[0].text.startswith("Only 10 days")
    assert MO.drift_check(calm, 0.12, -0.25) == []
    crash = calm.copy()
    crash.iloc[60:] *= 0.6
    kinds = {a.level for a in MO.drift_check(crash, 0.12, -0.25)}
    assert "critical" in kinds
    tr = pd.DataFrame({"pnl": [100, -50, 200, -50], "days_held": [10, 5, 20, 3], "cost": [1, 1, 1, 1]})
    st = MO.pot_stats(crash, tr, calm)
    assert st["trades"] == 4 and st["win_rate"] == 0.5 and st["profit_factor"] == pytest.approx(3.0)
    assert st["max_drawdown"] < -0.35 and st["benchmark_return"] > 0


def test_end_to_end_research_to_paper_order(tmp_path):
    # 1. universe
    raw = [
        {"symbol": f"S{i:02d}", "name": f"Stock {i} Inc", "exchange": "NYSE", "status": "active", "tradable": True}
        for i in range(40)
    ] + [{"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "exchange": "ARCA", "status": "active", "tradable": True}]
    rng = np.random.default_rng(11)
    idx = pd.bdate_range(end=pd.Timestamp.now().normalize() - pd.Timedelta(days=1), periods=320)
    drift = {f"S{i:02d}": 0.0002 + 0.00004 * i for i in range(40)} | {"SPY": 0.0004}
    close = pd.DataFrame(
        {s: 50 * np.exp(np.cumsum(rng.normal(d, 0.012, len(idx)))) for s, d in drift.items()}, index=idx
    )
    vol = pd.DataFrame(2e6, index=idx, columns=close.columns)
    bars = {
        s: pd.DataFrame(
            {
                "Open": close[s].to_numpy(),
                "High": close[s].to_numpy() * 1.01,
                "Low": close[s].to_numpy() * 0.99,
                "Close": close[s].to_numpy(),
                "Volume": vol[s].to_numpy(),
            },
            index=idx.tz_localize("UTC"),
        )
        for s in close
    }
    table = U.assess(U.from_alpaca_assets(raw), U.liquidity(bars, idx[-1].tz_localize("UTC")))
    snap = U.Snapshot(table, pd.Timestamp.now(tz="UTC"), "test")
    assert snap.counts()["eligible"] == 41
    # 2. scanner (long-term, untested weights)
    p = FL.Panels(close.shift(1).fillna(close), close * 1.01, close * 0.99, close, vol)
    keep, _ = SC.fast_filter(snap.assets, SC.SCANNERS["long-term"])
    ranking, used, status = SC.rank("long-term", p, keep, {}, min_history=252)
    assert status == "untested" and len(ranking) > 10
    top = ranking.index[0]
    daily = pd.DataFrame(
        {
            "Open": close[top],
            "High": close[top] * 1.01,
            "Low": close[top] * 0.99,
            "Close": close[top],
            "Volume": vol[top],
        }
    )
    # 3. assessment: untested signals cap BUY at WAIT
    a = AS.long_term(top, daily, float(ranking.at[top, "score"]), status, None, None)
    assert a.verdict != "BUY"
    # with evidence-backed weights the same rules may say BUY; force the evidence path for the order flow
    a2 = AS.long_term(top, daily, 95.0, "evidence", {"roic": 0.2, "revenue_growth": 0.2, "fcf_margin": 0.2}, None)
    # 4. portfolio check and plan
    rets = close.pct_change(fill_method=None)
    pv = PO.view(
        [PO.Holding("SPY", 50, float(close["SPY"].iloc[-1]), asset_class="etf")],
        {"SPY": float(close["SPY"].iloc[-1])},
        47_000,
        rets,
    )
    chk = PO.check_candidate(pv, top, rets, 0.05)
    plan = IP.build(
        top,
        daily,
        "long-term",
        a2.verdict if a2.verdict in ("BUY", "WAIT") else "BUY",
        50_000,
        1.3,
        portfolio_check=chk,
    )
    assert plan.action in ("BUY", "WAIT", "NO ADDITION")
    if plan.action != "BUY":
        plan = IP.build(top, daily, "long-term", "BUY", 50_000, 1.3)
    # 5. paper order through the fake broker (enabled only inside this test)
    fake = FakeAlpaca()
    b = BR.PaperBroker(fake, cfg={"paper_orders": {"enabled": True}}, folder=tmp_path)
    qty = round(plan.tranches[0][2], 4)
    req = BR.OrderRequest(
        top,
        "buy",
        qty,
        type="limit",
        limit_price=plan.entry_zone[1],
        pot="long-term",
        plan_id=f"{top}-{idx[-1].date()}",
    )
    b.submit(req, plan.price, pd.Timestamp.now(tz="UTC"), approved=True)
    fake.fill(0, qty, plan.price)
    pots = BR.ledgers_from_orders(fake.history, {"long-term": 50_000, "swing": 50_000})
    assert BR.reconcile(pots, b.positions()) == [] and pots["long-term"]["positions"][top]["qty"] == qty
    # 6. the recommendation is recorded and graded later without hindsight
    spec = SP.library()["spy-gld-70-30-monthly"]
    d = {
        t: pd.DataFrame({"Open": close[t], "High": close[t], "Low": close[t], "Close": close[t], "Volume": 1.0})
        for t in ("SPY",)
    }
    d["GLD"] = d["SPY"] * 0.5
    rec = RC.make_record("SPY", spec, {k: v.iloc[:-70] for k, v in d.items()}, None)
    out = RC.outcomes([rec], {"SPY": close["SPY"]})
    assert set(out["horizon_days"]) == {1, 5, 20, 60}


def test_daily_monitor_records_pots_and_reconciles(tmp_path, monkeypatch):
    import sys

    sys.path.insert(0, str(__import__("aurum.config", fromlist=["ROOT"]).ROOT / "scripts"))
    import daily_monitor as DM

    fake = FakeAlpaca()
    b = BR.PaperBroker(fake, cfg={"paper_orders": {"enabled": True}}, folder=tmp_path)
    b.submit(BR.OrderRequest("SPY", "buy", 2, pot="swing", plan_id="m"), 700.0, pd.Timestamp.now(tz="UTC"), True)
    fake.fill(0, 2, 700.0)
    monkeypatch.setattr(DM, "alpaca_keys", lambda: ("k", "s"))
    monkeypatch.setattr(DM.BR, "FOLDER", tmp_path)
    real = BR.PaperBroker
    monkeypatch.setattr(DM.BR, "PaperBroker", lambda: real(fake, cfg={}, folder=tmp_path))
    DM.main()
    eq = pd.read_csv(tmp_path / "equity.csv", index_col=0)
    assert eq["swing"].iloc[-1] == pytest.approx(50_000 - 1400 + 2 * 0)  # no current price in the fake: valued at 0
    report = (tmp_path / "monitor.md").read_text()
    assert "PAPER TRADING" in report and "match Alpaca" in report and "Paper orders OFF" in report
