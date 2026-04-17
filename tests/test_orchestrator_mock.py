from __future__ import annotations

import aiosqlite
import pytest

import ada.orchestrator as orch
from ada.query_engine import TASK_KIND_CHAT, QueryEngine
from ada.stream_types import CompletedFunctionCall, StreamLegResult
from ada.tool_executor import FileToolConfig


@pytest.mark.asyncio
async def test_orchestrate_turn_streams_and_persists(
    tmp_path, schema_sql_path, monkeypatch
):
    async def fake_leg(**kwargs: object) -> StreamLegResult:
        return StreamLegResult("Hello", [], {}, None)

    monkeypatch.setattr(orch, "stream_one_model_leg", fake_leg)

    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        tid = await qe.insert_task(
            "Interactive", status="executing", task_kind=TASK_KIND_CHAT
        )
        out = await orch.orchestrate_turn(
            qe,
            session_id=tid,
            user_text="hi",
            system_instruction="You are a tester.",
            api_key="dummy",
            model="gemini-test",
            on_delta=None,
            max_retries=0,
            enable_memory_tools=False,
            include_plan_tools=False,
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

    async def flaky_leg(**kwargs: object) -> StreamLegResult:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("stream down")
        return StreamLegResult("ok", [], {}, None)

    monkeypatch.setattr(orch, "stream_one_model_leg", flaky_leg)

    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        tid = await qe.insert_task(
            "Interactive", status="executing", task_kind=TASK_KIND_CHAT
        )
        text = await orch.orchestrate_turn(
            qe,
            session_id=tid,
            user_text="hi",
            system_instruction="sys",
            api_key="k",
            model="m",
            max_retries=1,
            enable_memory_tools=False,
            include_plan_tools=False,
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


@pytest.mark.asyncio
async def test_orchestrator_tool_round_persists_tool_row(
    tmp_path, schema_sql_path, monkeypatch
):
    calls = {"n": 0}

    async def two_leg(**kwargs: object) -> StreamLegResult:
        calls["n"] += 1
        if calls["n"] == 1:
            return StreamLegResult(
                "",
                [
                    CompletedFunctionCall(
                        name="run_allowlisted_shell",
                        args={"command": "uname -a"},
                        id="c1",
                    )
                ],
                {},
                None,
            )
        return StreamLegResult("Done.", [], {}, None)

    monkeypatch.setattr(orch, "stream_one_model_leg", two_leg)

    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        tid = await qe.insert_task(
            "Interactive", status="executing", task_kind=TASK_KIND_CHAT
        )
        out = await orch.orchestrate_turn(
            qe,
            session_id=tid,
            user_text="probe",
            system_instruction="sys",
            api_key="k",
            model="m",
            max_retries=0,
            shell_allowlist=frozenset({"uname -a"}),
            enable_memory_tools=False,
            include_plan_tools=False,
        )
        assert out == "Done."
        chain = await qe.load_chain_for_api(tid)
        roles = [r["role"] for r in chain]
        assert roles.count("tool") >= 1
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_orchestrator_plan_tool_round_persists_plan_json(
    tmp_path, schema_sql_path, monkeypatch
):
    calls = {"n": 0}

    async def two_leg(**kwargs: object) -> StreamLegResult:
        calls["n"] += 1
        if calls["n"] == 1:
            return StreamLegResult(
                "",
                [
                    CompletedFunctionCall(
                        name="write_task_plan",
                        args={"plan_json": '{"phase":"test"}'},
                        id="p1",
                    )
                ],
                {},
                None,
            )
        return StreamLegResult("Plan saved.", [], {}, None)

    monkeypatch.setattr(orch, "stream_one_model_leg", two_leg)

    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        tid = await qe.insert_task(
            "Interactive", status="executing", task_kind=TASK_KIND_CHAT
        )
        out = await orch.orchestrate_turn(
            qe,
            session_id=tid,
            user_text="set plan",
            system_instruction="sys",
            api_key="k",
            model="m",
            max_retries=0,
            enable_memory_tools=False,
            include_plan_tools=True,
        )
        assert out == "Plan saved."
        assert await qe.get_task_plan_json(tid) == '{"phase":"test"}'
        chain = await qe.load_chain_for_api(tid)
        tool_parts = [
            p
            for row in chain
            if row["role"] == "tool"
            for p in row["parts"]
            if p.get("type") == "function_response"
        ]
        assert any(
            p.get("name") == "write_task_plan" for p in tool_parts
        )
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_orchestrator_file_tool_round_writes_file(
    tmp_path, schema_sql_path, monkeypatch
):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    rr = workspace.resolve()
    file_cfg = FileToolConfig(
        roots=(rr,),
        primary_root=rr,
        max_read_bytes=4096,
        max_write_bytes=4096,
    )
    calls = {"n": 0}

    async def two_leg(**kwargs: object) -> StreamLegResult:
        calls["n"] += 1
        if calls["n"] == 1:
            return StreamLegResult(
                "",
                [
                    CompletedFunctionCall(
                        name="write_workspace_file",
                        args={
                            "path": "out.txt",
                            "content": "from-tool",
                            "mode": "write",
                        },
                        id="f1",
                    )
                ],
                {},
                None,
            )
        return StreamLegResult("done.", [], {}, None)

    monkeypatch.setattr(orch, "stream_one_model_leg", two_leg)

    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        tid = await qe.insert_task(
            "Interactive", status="executing", task_kind=TASK_KIND_CHAT
        )
        out = await orch.orchestrate_turn(
            qe,
            session_id=tid,
            user_text="write file",
            system_instruction="sys",
            api_key="k",
            model="m",
            max_retries=0,
            enable_memory_tools=False,
            include_plan_tools=False,
            file_config=file_cfg,
        )
        assert out == "done."
        assert (workspace / "out.txt").read_text(encoding="utf-8") == "from-tool"
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_orchestrator_session_token_limit_kill_switch(
    tmp_path, schema_sql_path, monkeypatch
):
    async def heavy_leg(**kwargs: object) -> StreamLegResult:
        return StreamLegResult(
            "partial",
            [],
            {"input_tokens": 50, "output_tokens": 51},
            None,
        )

    monkeypatch.setattr(orch, "stream_one_model_leg", heavy_leg)

    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        tid = await qe.insert_task(
            "Interactive", status="executing", task_kind=TASK_KIND_CHAT
        )
        with pytest.raises(orch.SessionTokenLimitExceeded):
            await orch.orchestrate_turn(
                qe,
                session_id=tid,
                user_text="hi",
                system_instruction="sys",
                api_key="k",
                model="m",
                max_retries=0,
                enable_memory_tools=False,
                include_plan_tools=False,
                max_session_tokens=100,
            )
        async with aiosqlite.connect(db) as raw:
            cur = await raw.execute(
                "SELECT status FROM tasks WHERE id = ?", (tid,)
            )
            row = await cur.fetchone()
        assert row[0] == "failed"
        async with aiosqlite.connect(db) as raw:
            cur = await raw.execute(
                """
                SELECT kind FROM action_log
                WHERE session_id = ? ORDER BY id DESC LIMIT 1
                """,
                (tid,),
            )
            row = await cur.fetchone()
        assert row[0] == "session_token_limit_exceeded"
    finally:
        await qe.close()
