"""Tests for Gemini stream parsing (text + function calls)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import types as gtypes

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
