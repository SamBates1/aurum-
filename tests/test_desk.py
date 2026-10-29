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
