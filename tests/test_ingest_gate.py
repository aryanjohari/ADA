"""Unit tests for ingest LLM gate (no live API)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from ada.ingest import gate as gate_mod


@pytest.mark.asyncio
async def test_score_feed_entry_fallback_on_client_error(monkeypatch):
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(side_effect=RuntimeError("fail"))
    monkeypatch.setattr(gate_mod.genai, "Client", lambda **_: mock_client)

    rs, tags = await gate_mod.score_feed_entry(
        "key", title="a", summary="b", model="m", max_output_tokens=128
    )
    assert rs == 1.0
    assert tags == []


@pytest.mark.asyncio
async def test_score_feed_entry_parses_json(monkeypatch):
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = '{"relevance_score": 0.42, "tags": ["a", "b"]}'
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_resp)
    monkeypatch.setattr(gate_mod.genai, "Client", lambda **_: mock_client)

    rs, tags = await gate_mod.score_feed_entry("key", title="t", summary="s", model="m")
    assert abs(rs - 0.42) < 1e-6
    assert tags == ["a", "b"]
