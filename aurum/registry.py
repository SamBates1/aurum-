"""Experiment registry (SQLite): every strategy version tried, every backtest run, every status change.

Why it exists: the more versions of a strategy you try, the more likely the best one looks good by luck. The registry
counts the tries so the designer can warn about it and the Fair Test can deflate the Sharpe ratio for them (DSR). It
also keeps the status of each exact strategy definition (by spec hash) and its history, so nothing changes status
silently.

The database is local (default logs/registry.sqlite, git-ignored). Durable evidence lives in files that are committed:
Fair Test reports (research/fairtests/) and owner approvals (research/approvals.yaml).

Statuses and allowed moves:
    draft -> testing -> passed | failed | inconclusive          (Fair Test, automatic)
    any tested status -> testing                                  (re-test)
    passed -> approved_paper                                      (owner only, aurum/gates.py)
    passed | failed | inconclusive -> shadow                      (owner only: paper-tracked for evidence)
    approved_paper | shadow -> paper_trading -> retired           (paper trader / owner)
    any -> retired                                                (owner)
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import spec as SP
from .config import CFG, ROOT

STATUSES = (
    "draft",
    "testing",
    "passed",
    "failed",
    "inconclusive",
    "approved_paper",
    "shadow",
    "paper_trading",
    "retired",
)
TESTED = ("passed", "failed", "inconclusive")
ALLOWED = {
    "draft": {"testing", "retired"},
    "testing": {"passed", "failed", "inconclusive", "draft"},
    "passed": {"testing", "approved_paper", "shadow", "retired"},
    "failed": {"testing", "shadow", "retired"},
    "inconclusive": {"testing", "shadow", "retired"},
    "approved_paper": {"paper_trading", "testing", "retired"},
    "shadow": {"paper_trading", "testing", "retired"},
    "paper_trading": {"retired", "testing"},
    "retired": {"draft"},
}
OWNER_ONLY = {"approved_paper", "shadow", "retired"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS strategies (
    spec_hash TEXT PRIMARY KEY, id TEXT, version INTEGER, name TEXT, spec_json TEXT, parent_hash TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT, spec_hash TEXT, kind TEXT, created_at TEXT, period TEXT,
    data_label TEXT, data_fp TEXT, code_fp TEXT, git_commit TEXT, sharpe_daily REAL, metrics_json TEXT
);
CREATE TABLE IF NOT EXISTS status (spec_hash TEXT PRIMARY KEY, status TEXT, updated_at TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT, spec_hash TEXT, from_status TEXT, to_status TEXT, at TEXT, by TEXT, note TEXT
);
CREATE TABLE IF NOT EXISTS holdout_views (id INTEGER PRIMARY KEY AUTOINCREMENT, spec_hash TEXT, at TEXT, why TEXT);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class StatusError(ValueError):
    pass


class Registry:
    def __init__(self, path: str | Path | None = None, cfg: dict = CFG):
        rc = cfg.get("registry", {}) or {}
        self.path = Path(path or ROOT / rc.get("path", "logs/registry.sqlite"))
        self.prior_trials = int(rc.get("prior_trials", 100))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.executescript(SCHEMA)

    @contextmanager
    def _db(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        finally:
            con.close()

    # --- strategies -----------------------------------------------------------------------------------------------
    def register(self, spec: dict, parent_hash: str | None = None) -> str:
        s = SP.validate(spec)
        h = SP.spec_hash(s)
        with self._db() as db:
            db.execute(
                "INSERT OR IGNORE INTO strategies VALUES (?,?,?,?,?,?,?)",
                (h, s["id"], int(s["version"]), s["name"], json.dumps(s, default=str), parent_hash, _now()),
            )
            db.execute("INSERT OR IGNORE INTO status VALUES (?,?,?,?)", (h, "draft", _now(), "registered"))
        return h

    def strategies(self) -> list[dict]:
        with self._db() as db:
            rows = db.execute(
                "SELECT s.*, st.status, st.updated_at AS status_at FROM strategies s "
                "LEFT JOIN status st USING(spec_hash) ORDER BY s.created_at"
            ).fetchall()
        return [dict(r) for r in rows]

    def spec_of(self, spec_hash: str) -> dict | None:
        with self._db() as db:
            r = db.execute("SELECT spec_json FROM strategies WHERE spec_hash=?", (spec_hash,)).fetchone()
        return json.loads(r["spec_json"]) if r else None

    # --- status ---------------------------------------------------------------------------------------------------
    def status(self, spec_hash: str) -> str:
        with self._db() as db:
            r = db.execute("SELECT status FROM status WHERE spec_hash=?", (spec_hash,)).fetchone()
        return r["status"] if r else "unregistered"

    def set_status(self, spec_hash: str, new: str, *, by: str = "system", note: str = "") -> None:
        if new not in STATUSES:
            raise StatusError(f"unknown status {new!r}")
        old = self.status(spec_hash)
        if old == "unregistered":
            raise StatusError("register the strategy first")
        if old != new and new not in ALLOWED[old]:
            raise StatusError(f"cannot move from {old} to {new}")
        if new in OWNER_ONLY and by != "owner":
            raise StatusError(f"only the owner can set status {new}")
        with self._db() as db:
            db.execute(
                "UPDATE status SET status=?, updated_at=?, note=? WHERE spec_hash=?", (new, _now(), note, spec_hash)
            )
            db.execute(
                "INSERT INTO status_history (spec_hash, from_status, to_status, at, by, note) VALUES (?,?,?,?,?,?)",
                (spec_hash, old, new, _now(), by, note),
            )

    def history(self, spec_hash: str) -> list[dict]:
        with self._db() as db:
            rows = db.execute("SELECT * FROM status_history WHERE spec_hash=? ORDER BY id", (spec_hash,)).fetchall()
        return [dict(r) for r in rows]

    # --- runs and trials -----------------------------------------------------------------------------------------
    def log_run(
        self,
        spec_hash: str,
        kind: str,
        *,
        period: str = "",
        data_label: str = "",
        data_fp: dict | None = None,
        code_fp: str = "",
        git_commit: str = "",
        sharpe_daily: float | None = None,
        metrics: dict | None = None,
    ) -> int:
        with self._db() as db:
            cur = db.execute(
                "INSERT INTO runs (spec_hash, kind, created_at, period, data_label, data_fp, code_fp, git_commit, "
                "sharpe_daily, metrics_json) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    spec_hash,
                    kind,
                    _now(),
                    period,
                    data_label,
                    json.dumps(data_fp or {}, default=str),
                    code_fp,
                    git_commit,
                    None if sharpe_daily is None or not np.isfinite(sharpe_daily) else float(sharpe_daily),
                    json.dumps(metrics or {}, default=str),
                ),
            )
            return int(cur.lastrowid)

    def runs(self, spec_hash: str | None = None, kind: str | None = None) -> list[dict]:
        q, args = "SELECT * FROM runs WHERE 1=1", []
        if spec_hash:
            q += " AND spec_hash=?"
            args.append(spec_hash)
        if kind:
            q += " AND kind=?"
            args.append(kind)
        with self._db() as db:
            rows = db.execute(q + " ORDER BY run_id", args).fetchall()
        return [dict(r) for r in rows]

    def trial_sharpes(self) -> list[float]:
        """Daily Sharpe of every distinct strategy version backtested (latest run of each), the input to the DSR."""
        with self._db() as db:
            rows = db.execute(
                "SELECT spec_hash, sharpe_daily FROM runs WHERE sharpe_daily IS NOT NULL AND kind IN "
                "('designer','lab','fair_test') ORDER BY run_id"
            ).fetchall()
        last = {}
        for r in rows:
            last[r["spec_hash"]] = r["sharpe_daily"]
        return list(last.values())

    def n_trials(self) -> int:
        """Distinct versions tried here plus the variants already tested in earlier experiments (prior_trials)."""
        return len(self.trial_sharpes()) + self.prior_trials

    # --- holdout --------------------------------------------------------------------------------------------------
    def view_holdout(self, spec_hash: str, why: str) -> None:
        with self._db() as db:
            db.execute("INSERT INTO holdout_views (spec_hash, at, why) VALUES (?,?,?)", (spec_hash, _now(), why))

    def holdout_views(self, spec_hash: str | None = None) -> int:
        with self._db() as db:
            if spec_hash:
                r = db.execute("SELECT COUNT(*) AS n FROM holdout_views WHERE spec_hash=?", (spec_hash,)).fetchone()
            else:
                r = db.execute("SELECT COUNT(*) AS n FROM holdout_views").fetchone()
        return int(r["n"])


def luck_benchmark(n_trials: int, var_daily_sharpe: float | None = None) -> float:
    """Annual Sharpe the best of n_trials strategies with NO real edge would show by luck alone (False Strategy
    Theorem). With fewer than five recorded trials the spread of Sharpe ratios is unknown, so a typical value for
    daily strategies is assumed: annual Sharpe standard deviation 0.32 (documented assumption)."""
    from .stats import expected_max_sharpe

    v = var_daily_sharpe if var_daily_sharpe and var_daily_sharpe > 0 else (0.32 / np.sqrt(252)) ** 2
    return float(expected_max_sharpe(max(n_trials, 2), v) * np.sqrt(252))


def overfitting_warnings(reg: Registry, spec_hash: str, lineage_edits: int = 0) -> list[str]:
    sh = reg.trial_sharpes()
    var = float(np.var(sh, ddof=1)) if len(sh) >= 5 else None
    n = reg.n_trials()
    out = [
        f"{len(sh)} strategy versions backtested here, plus about {reg.prior_trials} variants in earlier experiments. "
        f"With {n} tries, the best strategy with no real edge would still show an annual Sharpe of about "
        f"{luck_benchmark(n, var):.2f} by luck alone. Judge results against that, not against zero."
    ]
    hv = reg.holdout_views()
    if hv:
        out.append(
            f"The 2024+ holdout period has been looked at {hv} time(s) in this registry (and many times in earlier "
            "experiments). It is no longer an untouched test; only data after 2026-10-29 is genuinely new."
        )
    if lineage_edits >= 10:
        out.append(
            f"You have changed this strategy {lineage_edits} times in this session. Tuning a rule until "
            "the chart looks "
            "good is the most common way to fool yourself; use the Fair Test before trusting it."
        )
    return out
