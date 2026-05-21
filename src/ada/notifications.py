"""Out-of-band notifications (opt-in via ADA_NOTIFY_URL; default noop)."""

from __future__ import annotations

import os
from typing import Any, Protocol

from ada.mission_control.flags import MissionFlag

# Flag ids that may trigger external notify when ADA_NOTIFY_URL is set (future).
NOTIFY_FLAG_IDS = frozenset(
    {
        "system_jobs_dead",
        "mission_tick_job_overdue",
        "workflow_step_failed",
    }
)


class Notifier(Protocol):
    def notify(self, title: str, body: str, *, meta: dict[str, Any] | None = None) -> None: ...


class NoopNotifier:
    """Default: no external channel (operator uses Streamlit / CLI)."""

    def notify(self, title: str, body: str, *, meta: dict[str, Any] | None = None) -> None:
        _ = (title, body, meta)


class AppriseNotifier:
    """Optional Apprise URL (documented; requires apprise package + ADA_NOTIFY_URL)."""

    def __init__(self, url: str) -> None:
        self._url = url.strip()

    def notify(self, title: str, body: str, *, meta: dict[str, Any] | None = None) -> None:
        _ = meta
        try:
            import apprise
        except ImportError as e:
            raise RuntimeError(
                "Apprise not installed; pip install apprise or unset ADA_NOTIFY_URL"
            ) from e
        app = apprise.Apprise()
        app.add(self._url)
        app.notify(title=title[:200], body=body[:4000])


def get_notifier() -> Notifier:
    url = os.environ.get("ADA_NOTIFY_URL", "").strip()
    if not url:
        return NoopNotifier()
    return AppriseNotifier(url)


def maybe_notify_flags(flags: list[MissionFlag]) -> None:
    """
  Send notifications for high-signal flags. Never includes secrets or payload_json.
  No-op when ADA_NOTIFY_URL unset.
  """
    notifier = get_notifier()
    if isinstance(notifier, NoopNotifier):
        return
    for f in flags:
        if f.id not in NOTIFY_FLAG_IDS:
            continue
        if f.severity not in ("warn", "error"):
            continue
        notifier.notify(
            title=f"[ADA] {f.id}",
            body=f.message[:4000],
            meta={"severity": f.severity, "mission_id": f.mission_id},
        )
