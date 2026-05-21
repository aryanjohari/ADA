"""Greenfield profile gate: mission init + doctor + chat mission binding."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from ada.config import Settings
from ada.doctor import run_doctor
from ada.query_engine import TASK_KIND_CHAT, QueryEngine


@pytest.mark.asyncio
async def test_greenfield_mission_and_chat_binding(
    tmp_path, schema_sql_path, monkeypatch
) -> None:
    profile_root = tmp_path / "profiles"
    jarvis_dir = profile_root / "jarvis"
    jarvis_dir.mkdir(parents=True)
    policy_dir = jarvis_dir / "policies"
    policy_dir.mkdir()
    (policy_dir / "default.yaml").write_text("version: 1\n", encoding="utf-8")
    for name in ("master.md", "soul.md", "wakeup.md", "shell_allowlist.txt"):
        (jarvis_dir / name).write_text("", encoding="utf-8")

    monkeypatch.setenv("ADA_PROFILE", "jarvis")
    monkeypatch.setenv("ADA_PROFILE_DATA_ROOT", str(profile_root))
    monkeypatch.setenv("ADA_REQUIRE_PROFILE_ISOLATION", "1")
    monkeypatch.setenv("ADA_JOB_QUEUE", "system_jobs")
    monkeypatch.setenv("ADA_CHAT_DEFAULT_MISSION", "jarvis-ops")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-test-key-not-real")

    settings = Settings.load()
    settings.ensure_data_dir()

    defaults_path = Path(__file__).resolve().parents[1] / "templates" / "mission_defaults.json"
    defaults = json.loads(defaults_path.read_text(encoding="utf-8"))

    qe = QueryEngine(settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        from ada.profile_runtime import enforce_profile_identity

        await enforce_profile_identity(qe, settings)
        mid = await qe.create_mission(
            slug="jarvis-ops",
            title="Jarvis ops",
            defaults_json=defaults,
        )
        tid = await qe.insert_task(
            "Interactive session",
            status="executing",
            task_kind=TASK_KIND_CHAT,
            mission_id=mid,
        )
        assert await qe.get_task_mission_id(tid) == mid

        report = run_doctor(settings)
        assert report.exit_code == 0
        flag_ids = {f.code for f in report.findings if f.level != "ok"}
        assert "profile_mismatch" not in flag_ids
    finally:
        await qe.close()


def test_jarvis_env_example_documents_chat_default() -> None:
    example = (
        Path(__file__).resolve().parents[1] / "profiles" / "jarvis.env.example"
    )
    text = example.read_text(encoding="utf-8")
    assert "ADA_CHAT_DEFAULT_MISSION=jarvis-ops" in text
    assert "ADA_JOB_QUEUE=system_jobs" in text
    assert "GSC_SITE_URL=" not in text
