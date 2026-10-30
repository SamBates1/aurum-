"""Optional AI conversation layer for Aurum's research desk.

Uses the OpenAI-compatible Chat Completions API via the standard library, so no
additional Python dependency is required. By default it targets a local Ollama
server; a hosted endpoint may incur usage charges.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
AGENTS: dict[str, str] = {
    "Quant Researcher": (
        "You are Aurum's quantitative research lead. Turn ideas into falsifiable hypotheses, specify "
        "benchmarks, costs, walk-forward splits, metrics and failure criteria. Prefer simple baselines and "
        "pre-registered tests. Never invent test results."
    ),
    "Technical Analyst": (
        "You are Aurum's technical-analysis researcher. Discuss candlesticks, trend, breakouts, RSI, MACD, "
        "moving averages, momentum and volatility. Treat each indicator as a candidate feature, not a proven "
        "edge. Propose out-of-sample tests after costs and warn about multiple testing."
    ),
    "Macro Analyst": (
        "You are Aurum's macro researcher. Analyse gold, real yields, the US dollar, inflation, rates, "
        "volatility and cross-asset relationships. Distinguish observed data from causal explanations and "
        "check that data would have been available at the decision time."
    ),
    "ML Quant": (
        "You are Aurum's machine-learning quant. Assess forecasting targets, feature leakage, time-series "
        "validation, calibration, regime shifts and whether ML adds value beyond simple trend/momentum "
        "baselines. Do not recommend complexity without measured incremental benefit."
    ),
    "Fundamental Analyst": (
        "You are Aurum's fundamental analyst. Judge company quality, growth, margins, return on capital, cash "
        "flow, debt and valuation using only the point-in-time figures supplied (SEC filings with their filing "
        "dates). Compare with the sector where the data allows. Say plainly when figures are missing."
    ),
    "Portfolio Manager": (
        "You are Aurum's portfolio manager. Decide whether an idea suits the whole portfolio: diversification, "
        "duplication of existing exposures, concentration, correlation, the risk it adds and whether cash or another "
        "opportunity is better. You may not change position limits or the rule verdict."
    ),
    "Risk Manager": (
        "You are Aurum's independent risk manager. Challenge drawdowns, concentration, correlations, turnover, "
        "liquidity, transaction costs, sizing and operational risks. Prioritise capital preservation. Do not "
        "approve real-money trades or claim a strategy is safe."
    ),
    "Independent Reviewer": (
        "You are a sceptical reviewer trying to disprove the team's conclusions. Look for overfitting, look-ahead "
        "bias, survivorship bias, unfair benchmarks, small samples, regime dependence and missing costs. "
        "State what evidence would change your mind. Never fabricate results."
    ),
}

CONTEXT_FILES = (
    "README.md",
    "research/strategy-report-2026-10-29.md",
    "research/audit-2026-10-29.md",
    "research/experiments/README.md",
    "research/decisions.md",
    "research/experiments/results/2026-10-29-1440-plab-core-real/summary.md",
)


EXP_DIR = "research/experiments"


def list_experiments() -> list[dict[str, str]]:
    """Registry rows (ID, idea, status) parsed from research/experiments/README.md. Read-only."""
    import re

    path = ROOT / EXP_DIR / "README.md"
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*\[?(EXP-\d{3})\]?(?:\([^)]*\))?\s*\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|", line)
        if m:
            rows.append(
                {
                    "id": m.group(1),
                    "idea": m.group(2).strip(),
                    "origin": m.group(3).strip(),
                    "status": m.group(4).strip(),
                }
            )
    return rows


def experiment_file(exp_id: str) -> str | None:
    """Full text of one experiment record (hypothesis, rules, results), or None. Only files inside
    research/experiments named EXP-nnn-*.md can be read, so a question cannot make the desk open other paths."""
    import re

    if not re.fullmatch(r"EXP-\d{3}", exp_id):
        return None
    hits = sorted((ROOT / EXP_DIR).glob(f"{exp_id}-*.md"))
    return hits[0].read_text(encoding="utf-8") if hits else None


def latest_results(limit: int = 8) -> list[str]:
    """Names of the most recent real-data result folders (newest first)."""
    base = ROOT / EXP_DIR / "results"
    if not base.is_dir():
        return []
    names = sorted((p.name for p in base.iterdir() if p.is_dir() and "real" in p.name), reverse=True)
    return names[:limit]


def strategy_context(max_chars: int = 3500) -> str:
    """Strategy Designer state for the desk: saved strategies in plain English, latest Fair Test verdicts, owner
    approvals and paper ledgers. Read-only; numbers are copied from saved files, never computed by the model."""
    import json as _json

    from . import designer, gates
    from . import fairtest as ft
    from . import spec as sp

    lines = ["\n--- STRATEGY DESIGNER: SAVED STRATEGIES (historical backtests; paper trading only) ---"]
    fts = ft.latest_results()
    lib = sp.library()
    # approved (paper) strategies first, so the length limit never cuts them off
    order = sorted(lib, key=lambda k: (gates.approval_for(sp.spec_hash(lib[k])) is None, k))
    for sid in order:
        s = lib[sid]
        h = sp.spec_hash(s)
        r = fts.get(h)
        appr = gates.approval_for(h)
        lines.append(
            f"{sid} v{s['version']} (hash {h}): {s['name']}. "
            + " ".join(designer.describe(s)[:3])
            + (
                f" Fair Test: {r['status'].upper()} ({r['run_at'][:10]}): {r['explanation']}"
                if r
                else " Fair Test: none saved."
            )
            + (f" Owner approval: {appr['role']} ({appr['date']})." if appr else " Not approved for paper trading.")
        )
    from .config import CFG

    for item in (CFG.get("paper", {}) or {}).get("strategies", []) or []:
        led = ROOT / item["ledger"]
        if led.is_file():
            d = _json.loads(led.read_text())
            eq = d["cash"] + sum(p["qty"] * p["last_price"] for p in d.get("positions", {}).values())
            lines.append(
                f"PAPER LEDGER {item['ledger']} ({item['role']}): equity ${eq:,.2f}, "
                f"{len(d.get('trades', []))} simulated orders."
            )
    return "\n".join(lines)[:max_chars]


def context_for(question: str, max_chars: int = 16000) -> str:
    """Research context for one question: the standard files plus any experiment the question names (e.g.
    'EXP-037'), the experiment registry and the latest result folders. Read-only and size-bounded."""
    import re

    parts = []
    ids = list(dict.fromkeys(re.findall(r"EXP-\d{3}", question.upper())))[:3]
    for i in ids:
        text = experiment_file(i)
        parts.append(f"\n--- EXPERIMENT RECORD {i} ---\n" + (text[:5000] if text else "No such experiment record."))
    reg = list_experiments()
    if reg:
        parts.append(
            "\n--- EXPERIMENT REGISTRY (id | idea | status) ---\n"
            + "\n".join(f"{r['id']} | {r['idea'][:80]} | {r['status'][:80]}" for r in reg)
        )
    res = latest_results()
    if res:
        parts.append("\n--- LATEST REAL-DATA RESULT FOLDERS ---\n" + "\n".join(res))
    try:
        parts.append(strategy_context())
    except Exception as exc:  # the desk must still answer if a strategy file is broken
        parts.append(f"\n--- STRATEGY DESIGNER --- unavailable: {exc}")
    head = "".join(parts)
    return (head + research_context(max(1000, max_chars - len(head))))[:max_chars]


def research_context(max_chars: int = 14000) -> str:
    """Return bounded, read-only excerpts from known research files."""
    sections: list[str] = []
    remaining = max_chars
    for rel in CONTEXT_FILES:
        path = ROOT / rel
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        header = f"\n--- REPOSITORY FILE: {rel} ---\n"
        if remaining <= len(header):
            break
        excerpt = content[: min(remaining - len(header), 4500)]
        sections.append(header + excerpt)
        remaining -= len(header) + len(excerpt)
        if remaining <= 0:
            break
    return "\n".join(sections) or "No repository research files were available to load."


HOW_ROLES_WORK = (
    "All specialists are the same language model given different instructions (system prompts). They are not "
    "separate models or independent services, so their 'independent' views can share the same blind spots."
)


def provider_info() -> dict[str, str | bool]:
    """Active provider settings for display and audit records. Never includes the API key itself."""
    from urllib.parse import urlparse

    base_url = os.getenv("AURUM_LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")
    host = urlparse(base_url).hostname or ""
    return {
        "base_url": base_url,
        "model": os.getenv("AURUM_LLM_MODEL", "qwen2.5:7b"),
        "api_key_set": bool(os.getenv("AURUM_LLM_API_KEY")),
        "local": host in {"localhost", "127.0.0.1", "::1"},
    }


def chat_completion(messages: list[dict[str, str]], *, timeout: int = 90) -> str:
    """Call a configured OpenAI-compatible endpoint; never logs credentials."""
    info = provider_info()
    base_url, model = str(info["base_url"]), str(info["model"])
    api_key = os.getenv("AURUM_LLM_API_KEY", "")
    payload = json.dumps({"model": model, "messages": messages, "temperature": 0.2}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(f"{base_url}/chat/completions", data=payload, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"AI provider returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(
            f"Could not reach AI endpoint at {base_url}. Start your local model server or configure "
            "AURUM_LLM_BASE_URL. For hosted APIs, set AURUM_LLM_API_KEY locally."
        ) from exc
    except (TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError(f"AI endpoint timed out or returned invalid JSON: {exc}") from exc

    try:
        content = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("AI endpoint response did not contain choices[0].message.content.") from exc
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("AI endpoint returned an empty answer.")
    return content.strip()


def agent_reply(
    agent_name: str,
    user_message: str,
    history: list[dict[str, str]] | None = None,
    context: str | None = None,
) -> str:
    """Get one specialist's response with repository evidence and bounded history."""
    if agent_name not in AGENTS:
        raise ValueError(f"Unknown agent: {agent_name}")
    system = (
        f"{AGENTS[agent_name]}\n\n"
        "You are part of Aurum, a UK user's educational quant research project. "
        "Separate facts, hypotheses and recommendations. If repository context does not support a claim, "
        "say so. Never imply you executed code or checked live markets unless supplied evidence proves it. "
        "Never claim a strategy is profitable without robust out-of-sample evidence. "
        "Do not request or expose secrets. Do not make or execute real-money trades.\n\n"
        "Label each statement as one of: HISTORICAL FACT (from the files below), ESTIMATE, or HYPOTHESIS. The "
        "files are saved research, not live market data; say so if asked about current prices.\n\n"
        f"READ-ONLY AURUM RESEARCH CONTEXT:\n{context if context is not None else context_for(user_message)}"
    )
    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(
            {"role": item["role"], "content": item["content"][:6000]}
            for item in history[-8:]
            if item.get("role") in {"user", "assistant"} and isinstance(item.get("content"), str)
        )
    messages.append({"role": "user", "content": user_message[:6000]})
    return chat_completion(messages)


def team_debate(question: str, context: str | None = None) -> list[tuple[str, str]]:
    """Ask specialists independently, then ask the reviewer to synthesise their answers."""
    shared_context = context if context is not None else context_for(question)
    selected = ("Quant Researcher", "Macro Analyst", "ML Quant", "Risk Manager")
    results: list[tuple[str, str]] = []
    for name in selected:
        prompt = (
            f"Independently assess this question: {question}\n\n"
            "Give: (1) view, (2) evidence available vs missing, (3) a test or next action. "
            "Do not assume other agents agree."
        )
        results.append((name, agent_reply(name, prompt, context=shared_context)))
    debate_notes = "\n\n".join(f"### {name}\n{reply}" for name, reply in results)
    review = agent_reply(
        "Independent Reviewer",
        f"Review and synthesise the following specialist assessments of: {question}\n\n{debate_notes}\n\n"
        "Identify agreements, disagreements, unsupported claims and the single best next experiment. "
        "Do not invent results.",
        context=shared_context,
    )
    results.append(("Independent Reviewer — synthesis", review))
    return results


def audit_record(mode: str, agent: str, question: str, answer: str) -> dict:
    """What generated a desk answer, for the optional local log (no secrets, no full context)."""
    from datetime import datetime, timezone

    return {
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": mode,
        "agent": agent,
        "provider": provider_info(),
        "roles_note": HOW_ROLES_WORK,
        "context_files": [f for f in CONTEXT_FILES if (ROOT / f).is_file()],
        "question": question[:2000],
        "answer": answer[:6000],
        "status": "model-generated hypothesis, not a verified result",
    }


def log_answer(record: dict, path: Path | None = None) -> Path:
    path = path or ROOT / "logs" / "quant_desk.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    return path


# ---------------------------------------------------------------------------------------------------------------
# investment debate (platform phase 9): AI explains and challenges; the rules decide
# ---------------------------------------------------------------------------------------------------------------
DEBATE_TEAM = ("Technical Analyst", "Fundamental Analyst", "Macro Analyst", "Portfolio Manager", "Risk Manager")
PROPOSALS = ROOT / "research" / "desk" / "proposals.jsonl"


def investment_debate(symbol: str, rule_verdict: dict, facts: str) -> dict:
    """Each specialist assesses `facts` (numbers computed by Aurum, never by the model) independently; the
    Independent Reviewer then writes one synthesis that names agreements, disagreements and why they matter, unsupported
    claims and proposed experiments. The rule verdict is returned unchanged: AI text can never alter it, approve an
    order or change a limit."""
    shared = (
        f"FACTS COMPUTED BY AURUM FOR {symbol} (use only these numbers):\n{facts[:8000]}\n\n"
        f"RULE VERDICTS (binding, decided by fixed rules): {json.dumps(rule_verdict)}"
    )
    views = []
    for name in DEBATE_TEAM:
        q = (
            f"Assess {symbol} for both long-term investing and swing trading from your specialism. Give: (1) your view "
            "in two sentences, (2) the strongest evidence for and against from the facts, (3) what is missing. "
            "Do not repeat the other specialists; do not assume they agree."
        )
        views.append((name, agent_reply(name, q, context=shared)))
    notes = "\n\n".join(f"### {n}\n{v}" for n, v in views)
    synthesis = agent_reply(
        "Independent Reviewer",
        f"Synthesise these assessments of {symbol} into ONE answer with these headings exactly:\n"
        "AGREEMENT: where the specialists agree.\n"
        "DISAGREEMENTS: each disagreement, who holds which side, and why it matters for the decision.\n"
        "UNSUPPORTED: claims not backed by the facts.\n"
        "VERDICT CHECK: does the evidence support the rule verdicts? You cannot change them.\n"
        "PROPOSED EXPERIMENT: at most one testable idea (it will need pre-registration and the owner's approval).\n\n"
        + notes,
        context=shared,
    )
    proposal = _proposal(synthesis)
    if proposal:
        PROPOSALS.parent.mkdir(parents=True, exist_ok=True)
        with open(PROPOSALS, "a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "symbol": symbol,
                        "proposal": proposal,
                        "status": "proposed: needs pre-registration and owner approval",
                    }
                )
                + "\n"
            )
    return {
        "symbol": symbol,
        "rule_verdict": dict(rule_verdict),  # unchanged, whatever the text says
        "views": views,
        "synthesis": synthesis,
        "proposal": proposal,
        "label": "AI opinion: explains and challenges; not binding, places no orders, changes no limits",
    }


def _proposal(text: str) -> str | None:
    import re

    m = re.search(r"PROPOSED EXPERIMENT:\s*(.+?)(?:\n[A-Z ]{4,}:|\Z)", text, re.S)
    if not m:
        return None
    p = m.group(1).strip()
    return None if not p or p.lower().startswith(("none", "n/a", "no ")) else p[:1000]
