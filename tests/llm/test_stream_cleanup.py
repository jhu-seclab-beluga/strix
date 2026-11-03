"""Model stream cleanup regression tests.

test_stream_closes_provider_on_early_tool_response: An early tool response
releases the unfinished provider stream before the next request.
"""

import asyncio
from types import SimpleNamespace

from strix.llm import llm as llm_module
from strix.llm.config import LLMConfig
from strix.llm.llm import LLM


class _UnfinishedProvider:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class _UnfinishedStream:
    def __init__(self) -> None:
        self.chunk_count = 0
        self.completion_stream = _UnfinishedProvider()

    def __aiter__(self):
        return self

    async def __anext__(self):
        self.chunk_count += 1
        content = "<function=think>done</function>" if self.chunk_count == 1 else ""
        return SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content=content))],
            usage=None,
        )


def test_stream_closes_provider_on_early_tool_response(monkeypatch) -> None:
    monkeypatch.setenv("STRIX_LLM", "openai/claude-haiku-4-5-20251001")
    monkeypatch.setenv("LLM_API_KEY", "offline-test-key")
    monkeypatch.setenv("STRIX_OTEL_TELEMETRY", "0")
    monkeypatch.setenv("STRIX_POSTHOG_TELEMETRY", "0")
    stream = _UnfinishedStream()

    async def fake_acompletion(**_kwargs):
        return stream

    monkeypatch.setattr(llm_module, "acompletion", fake_acompletion)
    monkeypatch.setattr(llm_module, "stream_chunk_builder", lambda _chunks: None)
    monkeypatch.setattr(llm_module, "parse_tool_invocations", lambda _content: [])
    llm = LLM(LLMConfig(), agent_name=None)
    monkeypatch.setattr(llm, "_build_completion_args", lambda _messages: {})
    monkeypatch.setattr(llm, "_update_usage_stats", lambda _response: None)

    async def consume() -> None:
        async for _ in llm._stream([]):
            pass

    asyncio.run(consume())

    assert stream.completion_stream.closed
