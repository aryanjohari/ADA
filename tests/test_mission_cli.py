from __future__ import annotations

import io
import json
from contextlib import redirect_stdout

import pytest

from ada.goal_cli import async_main as goal_async_main
from ada.mission_cli import async_main as mission_async_main
from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_mission_cli_init_list_show_roundtrip(
    tmp_path, schema_sql_path, monkeypatch
):
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))
    rc = await mission_async_main(["init", "my-mission", "--title", "My Title"])
    assert rc == 0
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc2 = await mission_async_main(["list", "--limit", "10"])
    assert rc2 == 0
    assert "my-mission" in buf.getvalue()

    buf2 = io.StringIO()
    with redirect_stdout(buf2):
        rc3 = await mission_async_main(["show", "my-mission"])
    assert rc3 == 0
    assert "My Title" in buf2.getvalue()
    assert "slug:" in buf2.getvalue()


@pytest.mark.asyncio
async def test_mission_init_duplicate_slug_exit_code(
    tmp_path, schema_sql_path, monkeypatch
):
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))
    assert await mission_async_main(["init", "dup", "--title", "One"]) == 0
    assert await mission_async_main(["init", "dup", "--title", "Two"]) == 2


@pytest.mark.asyncio
async def test_goal_add_with_mission_sets_mission_id(
    tmp_path, schema_sql_path, monkeypatch
):
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))
    assert await mission_async_main(["init", "g1", "--title", "G1"]) == 0

    rc = await goal_async_main(["add", "do", "work", "--mission", "g1"])
    assert rc == 0

    qe = QueryEngine(tmp_path / "state.db", schema_sql_path)
    await qe.connect()
    try:
        rows = await qe.list_goal_tasks(limit=5, mission_slug="g1")
        assert len(rows) == 1
        assert rows[0]["goal"] == "do work"
        assert rows[0]["mission_slug"] == "g1"
        tid = rows[0]["id"]
        body = await qe.get_goal_task(tid)
        assert body["mission_id"] is not None
        assert body["mission_slug"] == "g1"

        p = await qe.fetch_pending_task()
        assert p is not None
        assert p.task_id == tid
        assert p.mission_slug == "g1"
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_goal_add_unknown_mission_exits_2(
    tmp_path, schema_sql_path, monkeypatch
):
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))
    rc = await goal_async_main(["add", "x", "--mission", "nope"])
    assert rc == 2


@pytest.mark.asyncio
async def test_goal_list_mission_filter(tmp_path, schema_sql_path, monkeypatch):
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))
    assert await mission_async_main(["init", "track-a", "--title", "A"]) == 0
    assert await mission_async_main(["init", "track-b", "--title", "B"]) == 0
    assert await goal_async_main(["add", "only-a", "--mission", "track-a"]) == 0
    assert await goal_async_main(["add", "only-b", "--mission", "track-b"]) == 0

    buf = io.StringIO()
    with redirect_stdout(buf):
        assert await goal_async_main(
            ["list", "--mission", "track-a", "--limit", "20"]
        ) == 0
    out = buf.getvalue()
    assert "only-a" in out
    assert "only-b" not in out


@pytest.mark.asyncio
async def test_mission_migrate_env_dry_run_no_db_write(
    tmp_path, schema_sql_path, monkeypatch
):
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))
    assert await mission_async_main(["init", "m1", "--title", "M1"]) == 0
    monkeypatch.setenv("ADA_PROJECT_ID", "from-env")
    monkeypatch.setenv("ADA_CAMPAIGN_ID", "camp-env")

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = await mission_async_main(["migrate-env", "m1"])
    assert rc == 0
    payload = json.loads(buf.getvalue().strip())
    assert payload["env_patch"]["project_id"] == "from-env"
    assert payload["would_apply"]["project_id"] == "from-env"

    qe = QueryEngine(tmp_path / "state.db", schema_sql_path)
    await qe.connect()
    try:
        row = await qe.get_mission_by_slug("m1")
        assert row is not None
        dj = row.get("defaults_json")
        assert isinstance(dj, dict)
        assert "project_id" not in dj
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_mission_migrate_env_apply_merge_only_missing(
    tmp_path, schema_sql_path, monkeypatch
):
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))
    assert (
        await mission_async_main(
            [
                "init",
                "m2",
                "--title",
                "M2",
                "--defaults-json",
                '{"project_id": "already"}',
            ]
        )
        == 0
    )
    monkeypatch.setenv("ADA_PROJECT_ID", "from-env")
    monkeypatch.setenv("ADA_CAMPAIGN_ID", "new-camp")

    buf = io.StringIO()
    with redirect_stdout(buf):
        assert await mission_async_main(["migrate-env", "m2", "--apply"]) == 0
    out = json.loads(buf.getvalue().strip())
    merged = out["merged_defaults_json"]
    assert merged["project_id"] == "already"
    assert merged["campaign_id"] == "new-camp"


@pytest.mark.asyncio
async def test_mission_migrate_env_apply_force_overwrites(
    tmp_path, schema_sql_path, monkeypatch
):
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))
    assert (
        await mission_async_main(
            [
                "init",
                "m3",
                "--title",
                "M3",
                "--defaults-json",
                '{"project_id": "old"}',
            ]
        )
        == 0
    )
    monkeypatch.setenv("ADA_PROJECT_ID", "new-proj")

    buf = io.StringIO()
    with redirect_stdout(buf):
        assert await mission_async_main(["migrate-env", "m3", "--apply", "--force"]) == 0
    merged = json.loads(buf.getvalue().strip())["merged_defaults_json"]
    assert merged["project_id"] == "new-proj"


@pytest.mark.asyncio
async def test_mission_migrate_env_unknown_slug(tmp_path, schema_sql_path, monkeypatch):
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ADA_PROJECT_ID", "x")
    rc = await mission_async_main(["migrate-env", "no-such-mission"])
    assert rc == 2
