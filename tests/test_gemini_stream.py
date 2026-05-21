"""Tests for Gemini stream parsing (text + function calls)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import types as gtypes
from google.genai.errors import ClientError, ServerError

from ada.adapters import gemini_stream as gs


def test_fc_from_part_prefers_function_call_attribute() -> None:
    fc = gtypes.FunctionCall(name="web_search", args={"q": "weather"})
    part = gtypes.Part(function_call=fc)
    assert gs._fc_from_part(part) is not None
    assert gs._fc_from_part(part).name == "web_search"


def test_fc_from_part_dict_function_call_key() -> None:
    part = {"functionCall": {"name": "web_search", "args": {}}}
    out = gs._fc_from_part(part)
    assert out is not None
    assert out.name == "web_search"


def test_fc_from_part_args_json_string() -> None:
    """Wire JSON sometimes sends args as a stringified object."""
    part = {"functionCall": {"name": "web_search", "args": '{"q": "hello"}'}}
    out = gs._fc_from_part(part)
    assert out is not None
    assert out.args.get("q") == "hello"


def test_function_calls_from_response_dump_finds_nested() -> None:
    class Blob:
        def model_dump(self, *args: object, **kwargs: object) -> dict:
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "functionCall": {
                                        "name": "record_edge",
                                        "args": {"edge_type": "cites", "confidence": 0.5},
                                    }
                                }
                            ]
                        }
                    }
                ]
            }

    fcs = gs._function_calls_from_response_dump(Blob())
    assert any(c.name == "record_edge" for c in fcs)


def test_fc_from_part_tool_call_google_search_web() -> None:
    """genai 1.7+ may emit ``tool_call`` (server ToolCall) instead of ``function_call``."""
    if not hasattr(gtypes, "ToolCall") or not hasattr(gtypes, "ToolType"):
        pytest.skip("ToolCall/ToolType require google-genai 1.7+")
    tc = gtypes.ToolCall(
        tool_type=gtypes.ToolType.GOOGLE_SEARCH_WEB,
        args={"query": "London weather"},
        id="t1",
    )
    part = gtypes.Part(tool_call=tc)
    out = gs._fc_from_part(part)
    assert out is not None
    assert out.name == "web_search"
    assert out.args.get("query") == "London weather"


def test_fc_from_part_model_dump_fallback() -> None:
    """Simulate a part where the wire shape is visible only via model_dump."""

    class LoosePart:
        function_call = None

        def model_dump(self, *args: object, **kwargs: object) -> dict:
            return {"functionCall": {"name": "fetch_url_text", "args": {"url": "https://x"}}}

    out = gs._fc_from_part(LoosePart())
    assert out is not None
    assert out.name == "fetch_url_text"


@pytest.mark.asyncio
async def test_stream_one_model_leg_function_only_no_error_from_empty_text() -> None:
    """Tool-only chunk: no text, one function call — result must list the call."""

    fc = gtypes.FunctionCall(name="web_search", args={"q": "x"})
    part = gtypes.Part(function_call=fc)
    content = gtypes.Content(role="model", parts=[part])
    cand = gtypes.Candidate(content=content, finish_reason="STOP")
    chunk = gtypes.GenerateContentResponse(candidates=[cand])

    async def fake_chunks():
        yield chunk

    mock_client = MagicMock()
    mock_client.aio.models.generate_content_stream = AsyncMock(return_value=fake_chunks())

    with patch.object(gs.genai, "Client", return_value=mock_client):
        leg = await gs.stream_one_model_leg(
            api_key="k",
            model="m",
            system_instruction="",
            contents=[],
            tool=gtypes.Tool(function_declarations=[]),
        )

    assert leg.text == ""
    assert len(leg.function_calls) == 1
    assert leg.function_calls[0].name == "web_search"


def test_transient_gemini_detects_high_demand_strings() -> None:
    assert gs.transient_gemini_stream_error(RuntimeError('model is busy: "high demand"'), retry_429=False)


def test_transient_gemini_skip_invalid_argument_http() -> None:
    exc = ClientError(
        400,
        {"error": {"status": "INVALID_ARGUMENT", "message": "bad"}},
        None,
    )
    assert gs.transient_gemini_stream_error(exc, retry_429=False) is False


def test_transient_gemini_optional_429(monkeypatch) -> None:
    exc = ClientError(429, {"error": {"status": "", "message": "rate"}}, None)
    assert gs.transient_gemini_stream_error(exc, retry_429=False) is False
    assert gs.transient_gemini_stream_error(exc, retry_429=True) is True


@pytest.mark.asyncio
async def test_stream_one_model_leg_retries_503_exponential(monkeypatch) -> None:
    """503 on stream open then succeeds: multiple API tries, deltas flush once after success."""
    sleeps: list[float] = []

    async def record_sleep(s: float) -> None:
        sleeps.append(s)

    monkeypatch.setattr(asyncio, "sleep", record_sleep)

    r_env = gs.GeminiStreamRetryEnv(
        max_retries=4,
        base_ms=1000,
        cap_ms=10_000,
        jitter_ratio=0.0,
        retry_429=False,
    )

    class Chunk:
        text = "hi"
        candidates: list = []
        usage_metadata = None

        function_calls = None

    attempts = {"n": 0}

    async def stream_side_effect(*_a: object, **_k: object):
        attempts["n"] += 1
        if attempts["n"] <= 2:
            raise ServerError(
                503,
                {"error": {"status": "UNAVAILABLE", "message": "slow"}},
                None,
            )

        async def ok_chunks():
            yield Chunk()

        return ok_chunks()

    mock_client = MagicMock()
    mock_client.aio.models.generate_content_stream = AsyncMock(
        side_effect=stream_side_effect
    )

    deltas: list[str] = []

    async def on_delta(t: str) -> None:
        deltas.append(t)

    retry_logged: list[dict] = []

    async def on_retry(pl: dict) -> None:
        retry_logged.append(pl)

    with patch.object(gs.genai, "Client", return_value=mock_client):
        leg = await gs.stream_one_model_leg(
            api_key="k",
            model="m",
            system_instruction="",
            contents=[],
            tool=gtypes.Tool(function_declarations=[]),
            on_text_delta=on_delta,
            gemini_retry_env=r_env,
            on_transient_gemini_retry=on_retry,
        )

    assert leg.text == "hi"
    assert deltas == ["hi"]
    assert mock_client.aio.models.generate_content_stream.await_count == 3
    assert len(retry_logged) == 2
    assert retry_logged[0]["sleep_ms"] == 1000
    assert retry_logged[1]["sleep_ms"] == 2000
    assert sleeps == [1.0, 2.0]


@pytest.mark.asyncio
async def test_stream_one_model_leg_non_transient_no_retry() -> None:
    async def boom(*_a: object, **_k: object) -> None:
        raise ClientError(
            400,
            {"error": {"status": "INVALID_ARGUMENT", "message": "bad"}},
            None,
        )

    mock_client = MagicMock()
    mock_client.aio.models.generate_content_stream = AsyncMock(side_effect=boom)

    r_env = gs.GeminiStreamRetryEnv(
        max_retries=4,
        base_ms=1,
        cap_ms=100,
        jitter_ratio=0.0,
        retry_429=False,
    )

    with patch.object(gs.genai, "Client", return_value=mock_client):
        with pytest.raises(ClientError):
            await gs.stream_one_model_leg(
                api_key="k",
                model="m",
                system_instruction="",
                contents=[],
                tool=gtypes.Tool(function_declarations=[]),
                gemini_retry_env=r_env,
            )

    assert mock_client.aio.models.generate_content_stream.await_count == 1
