"""Runtime skill prompt regression tests.

test_loaded_skill_reaches_next_model_message: A successful tool load updates the
actual system message after the agent receives its display identity.
test_scope_context_reaches_next_model_message: A scope update reaches the same
request message after the agent receives its display identity.
"""

import pytest

from strix.agents.StrixAgent.strix_agent import StrixAgent
from strix.tools.agents_graph import agents_graph_actions as graph
from strix.tools.load_skill.load_skill_actions import load_skill
from strix.utils.resource_paths import get_strix_resource_path


@pytest.fixture
def runtime_agent(monkeypatch) -> StrixAgent:
    monkeypatch.setenv("STRIX_LLM", "openai/claude-haiku-4-5-20251001")
    monkeypatch.setenv("LLM_API_KEY", "offline-test-key")
    monkeypatch.setenv("STRIX_OTEL_TELEMETRY", "0")
    monkeypatch.setenv("STRIX_POSTHOG_TELEMETRY", "0")
    monkeypatch.setattr(graph, "_agent_graph", {"nodes": {}, "edges": []})
    monkeypatch.setattr(graph, "_root_agent_id", None)
    monkeypatch.setattr(graph, "_agent_messages", {})
    monkeypatch.setattr(graph, "_agent_instances", {})
    monkeypatch.setattr(graph, "_agent_states", {})
    monkeypatch.setattr(graph, "_running_agents", {})

    agent = StrixAgent({})
    agent.llm.set_system_prompt_context(
        {
            "scope_source": "system_scan_config",
            "authorization_source": "strix_platform_verified_targets",
            "authorized_targets": [{"type": "url", "value": "http://host.docker.internal:9045"}],
        }
    )
    return agent


def _system_message(agent: StrixAgent) -> bytes:
    messages = agent.llm._prepare_messages([{"role": "user", "content": "test"}])
    request = agent.llm._build_completion_args(messages)
    return request["messages"][0]["content"].encode()


def test_loaded_skill_reaches_next_model_message(runtime_agent: StrixAgent) -> None:
    load_skill(runtime_agent.state, "business_logic")
    system_message = _system_message(runtime_agent)

    skill = get_strix_resource_path("skills", "vulnerabilities", "business_logic.md")
    source = skill.read_bytes()
    heading = source.index(b"## BELUGA E-Commerce Checkout Definition")
    start = source.index(b"```toml\n", heading) + 8
    end = source.index(b"\n```", start)
    definition = source[start:end] + b"\n"

    assert system_message.count(definition) == 1


def test_scope_context_reaches_next_model_message(runtime_agent: StrixAgent) -> None:
    system_message = _system_message(runtime_agent)

    assert b"- url: http://host.docker.internal:9045" in system_message
