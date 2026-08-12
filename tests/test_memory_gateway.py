"""Gateway memory tools — Observe denies writes; Agent appends."""

from __future__ import annotations

from pathlib import Path

from ada.io.paths import get_paths
from ada.memory.facts import ensure_prefs, get_fact
from ada.tools.gateway import Gateway
from ada.tools.schemas import TOOL_NAMES


def test_memory_tools_registered() -> None:
    assert "memory_facts_get" in TOOL_NAMES
    assert "memory_facts_append" in TOOL_NAMES
    assert "memory_worldview_write" in TOOL_NAMES
    assert "dream_status" in TOOL_NAMES


def test_observe_denies_memory_append(data_root: Path) -> None:
    ensure_prefs(get_paths())
    gw = Gateway(mode="observe")
    result = gw.execute(
        "memory_facts_append",
        {"key": "prefs.brief_time", "value": "05:30"},
    )
    assert result.ok is False
    assert result.outcome == "denied"
    assert "Observe" in (result.denied_reason or "")


def test_agent_append_and_get(data_root: Path) -> None:
    paths = get_paths()
    ensure_prefs(paths)
    gw = Gateway(mode="agent")
    appended = gw.execute(
        "memory_facts_append",
        {"key": "prefs.mute_proactivity", "value": True},
    )
    assert appended.ok is True
    assert appended.receipt_id
    got = gw.execute("memory_facts_get", {"key": "prefs.mute_proactivity"})
    assert got.ok is True
    assert got.data["value"] is True
    assert get_fact("prefs.mute_proactivity", paths=paths)["value"] is True


def test_observe_allows_search(data_root: Path) -> None:
    ensure_prefs(get_paths())
    gw = Gateway(mode="observe")
    result = gw.execute("memory_facts_search", {"query": "brief_time"})
    assert result.ok is True
    assert result.data["count"] >= 1


def test_worldview_write_requires_cites(data_root: Path) -> None:
    ensure_prefs(get_paths())
    gw = Gateway(mode="agent")
    denied = gw.execute(
        "memory_worldview_write",
        {"body": "A take with no cites", "cites": []},
    )
    assert denied.ok is False
    assert "cites" in (denied.error or denied.denied_reason or "").lower()

    ok = gw.execute(
        "memory_worldview_write",
        {
            "body": "Aryan likes 05:30 briefs.",
            "cites": ["prefs.brief_time"],
        },
    )
    assert ok.ok is True
    assert ok.data.get("path")
