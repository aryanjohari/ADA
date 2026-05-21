from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def schema_sql_path() -> Path:
    import ada

    return Path(ada.__path__[0]) / "db" / "schema.sql"


@pytest.fixture
def test_settings(tmp_path, monkeypatch):
    from ada.config import Settings

    data = tmp_path / "data"
    data.mkdir()
    mem = tmp_path / "memory"
    mem.mkdir()
    monkeypatch.setenv("ADA_DATA_DIR", str(data))
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    return Settings.load()
