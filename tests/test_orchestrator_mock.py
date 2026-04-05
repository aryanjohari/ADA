from __future__ import annotations

from collections.abc import AsyncIterator

import aiosqlite
import pytest

import ada.orchestrator as orch
from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_orchestrate_turn_streams_and_persists(
    tmp_path, schema_sql_path, monkeypatch
):
    async def fake_stream(
        **kwargs: object,
    ) -> AsyncIterator[str]:
        yield "He"
        yield "llo"

    monkeypatch.setattr(orch, "stream_generate_text", fake_stream)

    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        tid = await qe.insert_task("Interactive", status="executing")
        out = await orch.orchestrate_turn(
            qe,
            session_id=tid,
            user_text="hi",
            system_instruction="You are a tester.",
            api_key="dummy",
            model="gemini-test",
            on_delta=None,
            max_retries=0,
        )
        assert out == "Hello"
        chain = await qe.load_chain_for_api(tid)
        assert chain[-1]["parts"][0]["text"] == "Hello"
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_orchestrator_retry_tombstones_failed_assistant(
    tmp_path, schema_sql_path, monkeypatch
):
    calls = {"n": 0}

    async def flaky_stream(**kwargs: object) -> AsyncIterator[str]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("stream down")
        yield "ok"

    monkeypatch.setattr(orch, "stream_generate_text", flaky_stream)

    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        tid = await qe.insert_task("Interactive", status="executing")
        text = await orch.orchestrate_turn(
            qe,
            session_id=tid,
            user_text="hi",
            system_instruction="sys",
            api_key="k",
            model="m",
            max_retries=1,
        )
        assert text == "ok"
        async with aiosqlite.connect(db) as raw:
            cur = await raw.execute(
                "SELECT COUNT(*) FROM messages WHERE tombstone = 1 AND session_id = ?",
                (tid,),
            )
            row = await cur.fetchone()
        assert row[0] >= 1
    finally:
        await qe.close()
