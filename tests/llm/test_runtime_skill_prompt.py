"""Runtime skill prompt regression tests.

test_loaded_skill_reaches_next_model_message: A successful tool load updates the
actual system message after the agent receives its display identity.
"""

from strix.agents.StrixAgent.strix_agent import StrixAgent
from strix.tools.agents_graph.agents_graph_actions import _agent_instances
from strix.tools.load_skill.load_skill_actions import load_skill
from strix.utils.resource_paths import get_strix_resource_path


def test_loaded_skill_reaches_next_model_message(monkeypatch) -> None:
    monkeypatch.setenv("STRIX_LLM", "openai/claude-haiku-4-5-20251001")
    monkeypatch.setenv("LLM_API_KEY", "offline-test-key")
    monkeypatch.setenv("STRIX_OTEL_TELEMETRY", "0")
    monkeypatch.setenv("STRIX_POSTHOG_TELEMETRY", "0")

    agent = StrixAgent({})
    try:
        agent.llm.set_system_prompt_context(
            {
                "scope_source": "system_scan_config",
                "authorization_source": "strix_platform_verified_targets",
                "authorized_targets": [
                    {"type": "url", "value": "http://host.docker.internal:9045"}
                ],
            }
        )
        load_skill(agent.state, "business_logic")
        messages = agent.llm._prepare_messages([{"role": "user", "content": "test"}])
        request = agent.llm._build_completion_args(messages)
        system_message = request["messages"][0]["content"].encode()

        skill = get_strix_resource_path("skills", "vulnerabilities", "business_logic.md")
        source = skill.read_bytes()
        heading = source.index(b"## BELUGA E-Commerce Checkout Definition")
        start = source.index(b"```toml\n", heading) + 8
        end = source.index(b"\n```", start)
        definition = source[start:end] + b"\n"

        assert system_message.count(definition) == 1
    finally:
        _agent_instances.pop(agent.state.agent_id, None)
