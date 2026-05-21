"""Notifications stay noop without ADA_NOTIFY_URL."""

from __future__ import annotations

from ada.mission_control.flags import MissionFlag
from ada.notifications import NoopNotifier, NOTIFY_FLAG_IDS, get_notifier, maybe_notify_flags


def test_notify_flag_ids_defined() -> None:
    assert "system_jobs_dead" in NOTIFY_FLAG_IDS


def test_maybe_notify_noop(monkeypatch) -> None:
    monkeypatch.delenv("ADA_NOTIFY_URL", raising=False)
    assert isinstance(get_notifier(), NoopNotifier)
    flags = [
        MissionFlag(
            id="system_jobs_dead",
            severity="warn",
            message="dead jobs present",
            observed_at="2026-01-01T00:00:00Z",
        )
    ]
    maybe_notify_flags(flags)
