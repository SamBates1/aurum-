"""Paper-trading eligibility gates and owner approvals.

A strategy may be paper-traded only if EVERY gate passes for its exact definition (spec hash):

  1 valid definition                     the file loads and validates
  2 risk limits                          nothing in it breaks the independent risk engine's limits (aurum/risk.py)
  3 evidence                             a saved Fair Test for this exact hash; for the MAIN role it must have PASSED,
                                         unless the owner approved it on the evidence of a named pre-registered
                                         experiment (recorded in the approval, e.g. EXP-045)
  4 owner approval                       an entry in research/approvals.yaml for this exact hash and role
  5 not retired

Roles: "main" = the strategy the paper account is judged on; "shadow" = run alongside in its own paper ledger for
evidence only (it may have failed or been inconclusive in the Fair Test; that is stated wherever it is shown).

Approvals are only ever written by the owner (the dashboard's approval box, which requires an explicit confirmation,
or by editing the file). Editing a strategy changes its hash, so an old approval no longer applies: nothing can
change what is paper-traded silently. Real-money trading is not supported anywhere in Aurum.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from . import risk
from . import spec as SP
from .config import CFG, ROOT

APPROVALS = ROOT / "research" / "approvals.yaml"
ROLES = ("main", "shadow")


def load_approvals(path: Path | None = None) -> list[dict]:
    p = Path(path or APPROVALS)
    if not p.exists():
        return []
    data = yaml.safe_load(p.read_text()) or {}
    return list(data.get("approvals", []))


def approval_for(spec_hash: str, path: Path | None = None) -> dict | None:
    for a in reversed(load_approvals(path)):
        if a.get("spec_hash") == spec_hash and not a.get("revoked"):
            return a
    return None


def add_approval(
    spec: dict,
    role: str,
    *,
    approved_by: str,
    evidence: str,
    based_on: str | None = None,
    note: str = "",
    path: Path | None = None,
) -> dict:
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}")
    if not approved_by.startswith("owner"):
        raise PermissionError("only the owner can approve paper trading")
    s = SP.validate(spec)
    p = Path(path or APPROVALS)
    data = yaml.safe_load(p.read_text()) if p.exists() else None
    data = data or {"approvals": []}
    entry = {
        "strategy_id": s["id"],
        "version": int(s["version"]),
        "spec_hash": SP.spec_hash(s),
        "role": role,
        "approved_by": approved_by,
        "date": str(date.today()),
        "evidence": evidence,
    }
    if based_on:
        entry["based_on"] = based_on
    if note:
        entry["note"] = note
    data.setdefault("approvals", []).append(entry)
    p.write_text(_HEADER + yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return entry


def revoke(spec_hash: str, *, by: str, path: Path | None = None) -> None:
    if not by.startswith("owner"):
        raise PermissionError("only the owner can revoke an approval")
    p = Path(path or APPROVALS)
    data = yaml.safe_load(p.read_text()) or {"approvals": []}
    for a in data.get("approvals", []):
        if a.get("spec_hash") == spec_hash:
            a["revoked"] = str(date.today())
    p.write_text(_HEADER + yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def eligibility(spec: dict, role: str, fair_tests: dict, *, cfg: dict = CFG, path: Path | None = None) -> dict:
    """Each gate with pass/fail and a reason, plus overall `eligible`."""
    gates = []

    def gate(name, ok, detail):
        gates.append({"gate": name, "passed": bool(ok), "detail": detail})

    try:
        s = SP.validate(spec)
        h = SP.spec_hash(s)
        gate("Valid definition", True, f"{s['id']} v{s['version']} (hash {h})")
    except SP.SpecError as exc:
        gate("Valid definition", False, str(exc))
        return {"eligible": False, "gates": gates, "role": role}
    probs = risk.static_check(s, cfg)
    gate("Within risk limits", not probs, "; ".join(probs) or "all assets allowed; weights within limits")
    ft = fair_tests.get(h)
    appr = approval_for(h, path)
    if ft is None:
        if role == "main" and appr and appr.get("based_on"):
            gate("Evidence", True, f"no Fair Test saved yet; owner approved on the evidence of {appr['based_on']}")
        else:
            gate("Evidence", False, "no Fair Test saved for this exact version")
    elif role == "main" and ft["status"] != "passed":
        ok = bool(appr and appr.get("based_on"))
        gate(
            "Evidence",
            ok,
            f"Fair Test verdict {ft['status'].upper()}"
            + (f"; owner approved on the evidence of {appr['based_on']}" if ok else "; the main strategy needs a pass"),
        )
    else:
        gate("Evidence", True, f"Fair Test verdict {ft['status'].upper()} ({ft.get('run_at', '')[:10]})")
    if appr is None:
        gate("Owner approval", False, "not approved by the owner for this exact version")
    elif appr.get("role") != role:
        gate("Owner approval", False, f"approved as {appr.get('role')}, not {role}")
    else:
        gate(
            "Owner approval", True, f"approved as {role} by {appr['approved_by']} on {appr['date']}: {appr['evidence']}"
        )
    retired = bool(s.get("retired"))
    gate("Not retired", not retired, "retired" if retired else "active")
    return {"eligible": all(g["passed"] for g in gates), "gates": gates, "role": role, "spec_hash": h}


_HEADER = """# Owner approvals for paper trading (aurum/gates.py). One entry per exact strategy version (spec hash).
# Only the owner adds entries (dashboard approval box with explicit confirmation, or by editing this file).
# Editing a strategy changes its hash, so its old approval stops applying. Paper trading only: no real money.
"""
