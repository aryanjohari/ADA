"""ada mission status / audit-scope CLI (read-only JSON)."""

from __future__ import annotations

import json

import pytest

from ada.mission_cli import async_main


@pytest.mark.asyncio
async def test_mission_status_json(tmp_path, schema_sql_path, monkeypatch) -> None:
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("GEMINI_API_KEY", "fake_test_key")
    db = tmp_path / "state.db"
    from ada.query_engine import QueryEngine

    qe = QueryEngine(db, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        await qe.create_mission(slug="ops", title="Ops")
    finally:
        await qe.close()

    import io
    import sys

    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        rc = await async_main(["status", "ops"])
    finally:
        sys.stdout = old
    assert rc == 0
    data = json.loads(buf.getvalue())
    assert data["schema_version"] == 1
    assert data["mission_slug"] == "ops"
    assert "flags" in data


@pytest.mark.asyncio
async def test_mission_audit_scope_json(tmp_path, schema_sql_path, monkeypatch) -> None:
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("GEMINI_API_KEY", "fake_test_key")
    db = tmp_path / "state.db"
    from ada.query_engine import QueryEngine

    qe = QueryEngine(db, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        await qe.create_mission(slug="a1", title="A1")
    finally:
        await qe.close()

    import io
    import sys

    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        rc = await async_main(["audit-scope", "a1"])
    finally:
        sys.stdout = old
    assert rc == 0
    data = json.loads(buf.getvalue())
    assert data["mission_slug"] == "a1"
    assert "note" in data
