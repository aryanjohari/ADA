from __future__ import annotations

import io
from contextlib import redirect_stderr

import pytest

from ada.config import Settings
from ada.config_deprecation import DEPRECATED_ENVS, reset_deprecation_state_for_tests


@pytest.fixture(autouse=True)
def _reset_deprecation():
    reset_deprecation_state_for_tests()
    yield
    reset_deprecation_state_for_tests()


@pytest.mark.parametrize("entry", list(DEPRECATED_ENVS))
def test_deprecated_registry_settings_field_or_none(entry):
    """Every entry with settings_field must match a ``Settings`` attribute."""
    if entry.settings_field is None:
        return
    assert hasattr(Settings, "__dataclass_fields__")
    assert entry.settings_field in Settings.__dataclass_fields__


def test_settings_load_warns_once_per_process(monkeypatch, tmp_path):
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))
    # Use a real deprecated env that Settings also reads
    monkeypatch.setenv("ADA_TRIAGE_LEAD_DAILY_CAP", "7")
    buf = io.StringIO()
    with redirect_stderr(buf):
        Settings.load()
        Settings.load()
    err = buf.getvalue()
    assert err.count("ada: deprecated env ADA_TRIAGE_LEAD_DAILY_CAP") == 1
    assert "mission.defaults_json.triage_lead_daily_cap" in err
    assert "ada mission migrate-env" in err


def test_suppress_disables_stderr(monkeypatch, tmp_path):
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ADA_DEPRECATED_ENV_SUPPRESS", "1")
    monkeypatch.setenv("ADA_PROJECT_ID", "proj-x")
    buf = io.StringIO()
    with redirect_stderr(buf):
        Settings.load()
    assert "deprecated env" not in buf.getvalue()
