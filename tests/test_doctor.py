"""ada doctor read-only health checks."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from ada.config import Settings
from ada.doctor import run_doctor


def _schema_sql() -> str:
    root = Path(__file__).resolve().parents[1]
    return (root / "src" / "ada" / "db" / "schema.sql").read_text(encoding="utf-8")


@pytest.fixture()
def doctor_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    data = tmp_path / "profile_data" / "pi-test"
    data.mkdir(parents=True)
    monkeypatch.setenv("ADA_PROFILE", "pi-test")
    monkeypatch.setenv("ADA_PROFILE_DATA_ROOT", str(tmp_path / "profile_data"))
    monkeypatch.setenv("ADA_JOB_QUEUE", "system_jobs")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    db = data / "state.db"
    conn = sqlite3.connect(db)
    try:
        conn.executescript(_schema_sql())
        conn.execute(
            "INSERT INTO state(key, value) VALUES (?, ?), (?, ?), (?, ?)",
            (
                "profile.id",
                "pi-test",
                "profile.data_root",
                str(tmp_path / "profile_data"),
                "profile.fingerprint",
                "deadbeef",
            ),
        )
        conn.commit()
    finally:
        conn.close()
    s = Settings.load()
    # Align fingerprint with DB for happy path
    conn2 = sqlite3.connect(db)
    try:
        conn2.execute(
            "UPDATE state SET value = ? WHERE key = 'profile.fingerprint'",
            (s.profile_fingerprint,),
        )
        conn2.commit()
    finally:
        conn2.close()
    return s


def test_doctor_ok_when_profile_matches(doctor_settings: Settings) -> None:
    report = run_doctor(doctor_settings)
    assert report.exit_code == 0
    codes = {f.code for f in report.findings}
    assert "job_queue_mode" in codes
    assert "profile_mismatch" not in codes


def test_doctor_error_on_profile_mismatch(
    doctor_settings: Settings, tmp_path: Path
) -> None:
    db = doctor_settings.state_db_path
    conn = sqlite3.connect(db)
    try:
        conn.execute(
            "UPDATE state SET value = 'wrong' WHERE key = 'profile.fingerprint'"
        )
        conn.commit()
    finally:
        conn.close()
    report = run_doctor(doctor_settings)
    assert report.exit_code == 1
    assert any(f.code == "profile_mismatch" for f in report.findings)
