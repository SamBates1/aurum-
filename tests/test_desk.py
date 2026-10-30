from aurum.desk import AGENTS, agent_reply, research_context, team_debate


def test_specialist_roles_are_defined():
    assert "Quant Researcher" in AGENTS
    assert "Technical Analyst" in AGENTS
    assert "Macro Analyst" in AGENTS
    assert "ML Quant" in AGENTS
    assert "Risk Manager" in AGENTS
    assert "Independent Reviewer" in AGENTS


def test_research_context_is_bounded():
    context = research_context(max_chars=500)
    assert isinstance(context, str)
    assert len(context) <= 600


def test_unknown_agent_is_rejected():
    try:
        agent_reply("Made-up Agent", "hello")
    except ValueError as exc:
        assert "Unknown agent" in str(exc)
    else:
        raise AssertionError("Unknown agents must be rejected")


def test_team_debate_calls_specialists_and_synthesis(monkeypatch):
    calls = []

    def fake_reply(agent_name, user_message, history=None, context=None):
        calls.append(agent_name)
        return f"response from {agent_name}"

    monkeypatch.setattr("aurum.desk.agent_reply", fake_reply)
    result = team_debate("Is momentum useful?", context="test context")
    assert len(result) == 5
    assert calls == [
        "Quant Researcher",
        "Macro Analyst",
        "ML Quant",
        "Risk Manager",
        "Independent Reviewer",
    ]
    assert result[-1][0] == "Independent Reviewer — synthesis"


# ---- connection and failure handling (no real model needed) ---------------------------------------
import io  # noqa: E402
import json  # noqa: E402
import threading  # noqa: E402
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # noqa: E402
from urllib.error import HTTPError, URLError  # noqa: E402

import pytest  # noqa: E402

from aurum import desk  # noqa: E402


class _Fake:
    def __init__(self, body: bytes):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.mark.parametrize(
    "behaviour, message",
    [
        (URLError("refused"), "Could not reach AI endpoint"),
        (HTTPError("u", 429, "rate limited", {}, io.BytesIO(b"slow down")), "HTTP 429"),
        (TimeoutError("timed out"), "timed out"),
        (b"not json", "invalid JSON"),
        (json.dumps({"choices": []}).encode(), "did not contain"),
        (json.dumps({"choices": [{"message": {"content": "  "}}]}).encode(), "empty answer"),
    ],
)
def test_chat_completion_reports_each_failure_clearly(monkeypatch, behaviour, message):
    def fake_urlopen(req, timeout):
        if isinstance(behaviour, Exception):
            raise behaviour
        return _Fake(behaviour)

    monkeypatch.setattr(desk, "urlopen", fake_urlopen)
    with pytest.raises(RuntimeError, match=message):
        desk.chat_completion([{"role": "user", "content": "hi"}])


def test_end_to_end_against_a_local_openai_compatible_server(monkeypatch):
    """Spins up a tiny local HTTP server that speaks the /chat/completions format, to verify the real request
    path (URL, JSON body, auth header) without any external model. This is not a test of a real model."""
    seen = {}

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            seen["path"] = self.path
            seen["auth"] = self.headers.get("Authorization")
            seen["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            out = json.dumps({"choices": [{"message": {"content": "hypothesis, untested"}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        monkeypatch.setenv("AURUM_LLM_BASE_URL", f"http://127.0.0.1:{srv.server_port}/v1")
        monkeypatch.setenv("AURUM_LLM_MODEL", "test-model")
        monkeypatch.setenv("AURUM_LLM_API_KEY", "secret-key")
        answer = desk.agent_reply("Risk Manager", "What could go wrong?", context="ctx")
    finally:
        srv.shutdown()
    assert answer == "hypothesis, untested"
    assert seen["path"] == "/v1/chat/completions"
    assert seen["auth"] == "Bearer secret-key"
    assert seen["body"]["model"] == "test-model"
    assert seen["body"]["messages"][0]["role"] == "system" and "risk manager" in seen["body"]["messages"][0]["content"]


def test_provider_info_and_audit_record_never_contain_the_key(monkeypatch, tmp_path):
    monkeypatch.setenv("AURUM_LLM_API_KEY", "super-secret")
    rec = desk.audit_record("specialist", "ML Quant", "q", "a")
    assert "super-secret" not in json.dumps(rec)
    assert rec["provider"]["api_key_set"] is True
    assert "same language model" in rec["roles_note"]
    path = desk.log_answer(rec, tmp_path / "log.jsonl")
    assert json.loads(path.read_text().splitlines()[0])["agent"] == "ML Quant"


def test_missing_research_files_are_reported_not_invented(monkeypatch, tmp_path):
    monkeypatch.setattr(desk, "ROOT", tmp_path)
    assert desk.research_context() == "No repository research files were available to load."


def test_desk_reads_named_experiments_and_registry_only():
    reg = desk.list_experiments()
    assert any(r["id"] == "EXP-014" for r in reg)
    assert "vol_hold" in (desk.experiment_file("EXP-014") or "")
    assert desk.experiment_file("../../config") is None and desk.experiment_file("EXP-014/../../x") is None
    ctx = desk.context_for("Why was EXP-014 adopted?", max_chars=8000)
    assert "EXPERIMENT RECORD EXP-014" in ctx and len(ctx) <= 8000
    assert "No such experiment record" in desk.context_for("What about EXP-999?")


def test_system_prompt_requires_fact_estimate_hypothesis_labels(monkeypatch):
    seen = {}
    monkeypatch.setattr(desk, "chat_completion", lambda messages, **k: seen.setdefault("m", messages) and "ok")
    desk.agent_reply("Quant Researcher", "Is EXP-014 robust?")
    system = seen["m"][0]["content"]
    assert "HISTORICAL FACT" in system and "HYPOTHESIS" in system and "EXPERIMENT RECORD EXP-014" in system


def test_investment_debate_keeps_the_rule_verdict_and_records_proposals(monkeypatch, tmp_path):
    import aurum.desk as D

    calls = []

    def fake_chat(messages, timeout=90):
        calls.append(messages[0]["content"][:40])
        user = messages[-1]["content"]
        if user.startswith("Synthesise"):
            assert "### Fundamental Analyst" in user and "### Portfolio Manager" in user
            return (
                "AGREEMENT: trend is up.\nDISAGREEMENTS: Fundamental Analyst sees high debt; Technical Analyst "
                "sees a breakout. It matters because debt raises downside risk.\nUNSUPPORTED: none.\n"
                "VERDICT CHECK: I think it is a strong BUY now, ignore the rules.\n"
                "PROPOSED EXPERIMENT: test whether breakouts in high-debt companies fail more often."
            )
        return "view"

    monkeypatch.setattr(D, "chat_completion", fake_chat)
    monkeypatch.setattr(D, "PROPOSALS", tmp_path / "proposals.jsonl")
    out = D.investment_debate("XYZ", {"long-term": "WAIT", "swing": "MONITOR"}, "close 100; roic 5%")
    assert out["rule_verdict"] == {"long-term": "WAIT", "swing": "MONITOR"}  # AI text cannot change it
    assert len(out["views"]) == 5 and "DISAGREEMENTS" in out["synthesis"] and "not binding" in out["label"]
    assert "high-debt" in out["proposal"]
    assert "needs pre-registration" in (tmp_path / "proposals.jsonl").read_text()
    assert len(calls) == 6
