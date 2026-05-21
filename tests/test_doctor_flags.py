"""Doctor integrates mission_control flags."""

from __future__ import annotations

from pathlib import Path

import pytest

from ada.config import Settings
from ada.doctor import run_doctor
from ada.persistent.store import PersistentState
from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_doctor_reports_dead_system_job(tmp_path, schema_sql_path, monkeypatch) -> None:
    db = tmp_path / "state.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        jid = await qe.insert_system_job(
            kind="noop.ping",
            payload_json={},
            idempotency_key="doctor-dead-1",
        )
        store = qe._store
        assert isinstance(store, PersistentState)
        await store._conn.execute(  # noqa: SLF001
            "UPDATE system_jobs SET status='dead' WHERE id=?",
            (jid,),
        )
        await store._conn.commit()  # noqa: SLF001
    finally:
        await qe.close()

    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("GEMINI_API_KEY", "fake_test_key_not_real")
    monkeypatch.setenv("ADA_JOB_QUEUE", "system_jobs")
    settings = Settings.load()
    report = run_doctor(settings)
    codes = {f.code for f in report.findings}
    assert "system_jobs_dead" in codes or any(
        "dead" in f.message.lower() for f in report.findings
    )
