"""Setup assist: mission snapshot tool registration and harness note."""

from __future__ import annotations

import pytest

from ada.chat_ingress import ChatSurfaceMode
from ada.cli import _mission_control_snapshot_fn
from ada.prompt import _SETUP_MODE_NOTE, _WORK_MODE_MISSION_NOTE, build_system_instruction
from ada.tools.registry import build_agent_tools


def test_setup_mode_note_mentions_snapshot_and_no_guess() -> None:
    assert "get_mission_control_snapshot" in _SETUP_MODE_NOTE
    assert "never guess" in _SETUP_MODE_NOTE.lower()


def test_setup_tools_include_snapshot_when_enabled() -> None:
    tool = build_agent_tools(
        allowed_exact_commands=frozenset(),
        include_memory_tools=False,
        include_mission_control_snapshot=True,
    )
    names = [d.name for d in tool.function_declarations]
    assert "get_mission_control_snapshot" in names


def test_setup_tools_exclude_snapshot_by_default() -> None:
    tool = build_agent_tools(
        allowed_exact_commands=frozenset(),
        include_memory_tools=False,
    )
    names = [d.name for d in tool.function_declarations]
    assert "get_mission_control_snapshot" not in names


def test_work_mode_snapshot_fn_when_mission_bound(test_settings) -> None:
    settings = test_settings
    fn = _mission_control_snapshot_fn(
        settings,
        surface=ChatSurfaceMode.AGENT,
        mission_id=1,
        mission_slug="ada_ops",
        effective_mission_id=1,
    )
    assert fn is not None
    fn_entity = _mission_control_snapshot_fn(
        settings,
        surface=ChatSurfaceMode.CHAT,
        mission_id=None,
        mission_slug=None,
        effective_mission_id=None,
    )
    assert fn_entity is not None


@pytest.mark.asyncio
async def test_entity_snapshot_fn_profile_overview(
    tmp_path, schema_sql_path, test_settings
) -> None:
    from ada.chat_session import mission_control_snapshot_fn
    from ada.query_engine import QueryEngine

    db = test_settings.state_db_path
    qe = QueryEngine(db, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        await qe.create_mission(slug="ent-snap", title="Ent Snap")
    finally:
        await qe.close()
    fn = mission_control_snapshot_fn(
        test_settings,
        surface=ChatSurfaceMode.CHAT,
        mission_id=None,
        mission_slug=None,
        effective_mission_id=None,
    )
    assert fn is not None
    snap = await fn()
    assert "missions_overview" in snap
    slugs = [r["slug"] for r in snap["missions_overview"]]
    assert "ent-snap" in slugs


def test_work_mode_note_requires_snapshot() -> None:
    assert "get_mission_control_snapshot" in _WORK_MODE_MISSION_NOTE
    assert "ProgrammeDigest" in _WORK_MODE_MISSION_NOTE


def test_build_system_instruction_setup_mode_includes_note() -> None:
    instr = build_system_instruction(
        soul_text="",
        master_text="",
        state_db_display_path="/tmp/state.db",
        allowlist_summary="(none)",
        setup_mode=True,
    )
    assert "get_mission_control_snapshot" in instr


@pytest.mark.asyncio
async def test_snapshot_size_cap(tmp_path, schema_sql_path) -> None:
    from ada.mission_control.snapshot import build_mission_control_snapshot
    from ada.observability.queries import open_readonly_connection
    from ada.query_engine import QueryEngine

    db = tmp_path / "cap.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        mid = await qe.create_mission(slug="cap", title="Cap")
        for i in range(40):
            await qe.insert_system_job(
                kind="noop.ping",
                mission_id=mid,
                payload_json={"i": i},
                idempotency_key=f"cap-{i}",
            )
    finally:
        await qe.close()
    conn = open_readonly_connection(db)
    try:
        snap = build_mission_control_snapshot(
            conn,
            mission_id=mid,
            mission_slug="cap",
            profile_scope=False,
            max_bytes=2000,
        )
    finally:
        conn.close()
    import json

    raw = json.dumps(snap, ensure_ascii=False)
    assert len(raw.encode("utf-8")) <= 2500


@pytest.mark.asyncio
async def test_snapshot_include_programme_block(tmp_path, schema_sql_path) -> None:
    from ada.mission_control.snapshot import build_mission_control_snapshot
    from ada.observability.queries import open_readonly_connection
    from ada.query_engine import QueryEngine

    db = tmp_path / "prog.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        schedule = {
            "version": 1,
            "jobs": [
                {
                    "id": "daily_brief",
                    "min_interval_hours": 24,
                    "action": {"type": "enqueue_goal", "goal_text": "brief"},
                }
            ],
        }
        mid = await qe.create_mission(
            slug="snap-p",
            title="Snap P",
            schedule_hint_json=schedule,
        )
    finally:
        await qe.close()
    conn = open_readonly_connection(db)
    try:
        snap = build_mission_control_snapshot(
            conn,
            mission_id=mid,
            mission_slug="snap-p",
            profile_scope=False,
            include_programme=True,
        )
    finally:
        conn.close()
    prog = snap.get("programme")
    assert isinstance(prog, dict)
    jobs = prog.get("schedule_jobs")
    assert isinstance(jobs, list) and jobs[0]["id"] == "daily_brief"
