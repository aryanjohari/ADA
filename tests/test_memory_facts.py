"""M04 FACTS organ — append / get / search + mount honesty."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ada.io.paths import BodyFault, get_paths
from ada.memory.facts import append_fact, ensure_prefs, get_fact, search_facts


@pytest.mark.tier_a
def test_prefs_defaults_and_append_retrieve(data_root: Path) -> None:
    paths = get_paths()
    prefs = ensure_prefs(paths)
    assert prefs["brief_time"] == "05:30"
    assert prefs["quiet_hours_end"] == "05:30"
    assert paths.prefs_yaml.is_file()
    assert paths.aryan_yaml.is_file()

    result = append_fact("prefs.brief_time", "05:30", paths=paths)
    assert result["ok"] is True
    hit = get_fact("prefs.brief_time", paths=paths)
    assert hit["found"] is True
    assert hit["value"] == "05:30"

    search = search_facts("brief_time", paths=paths)
    assert search["count"] >= 1
    assert any(
        h.get("key") in {"brief_time", "prefs.brief_time"} or "brief_time" in str(h)
        for h in search["hits"]
    )


@pytest.mark.tier_a
def test_append_conflict_needs_confirm_when_disallowed(data_root: Path) -> None:
    paths = get_paths()
    ensure_prefs(paths)
    append_fact("prefs.tease_ok", True, paths=paths)
    conflict = append_fact(
        "prefs.tease_ok", False, paths=paths, allow_prefs_update=False
    )
    assert conflict["needs_confirm"] is True
    assert conflict["existing"] is True
    # Disk unchanged.
    assert get_fact("prefs.tease_ok", paths=paths)["value"] is True


@pytest.mark.tier_a
def test_operator_append_may_update_pref(data_root: Path) -> None:
    paths = get_paths()
    ensure_prefs(paths)
    result = append_fact("prefs.tease_ok", False, paths=paths)
    assert result["ok"] is True
    assert get_fact("prefs.tease_ok", paths=paths)["value"] is False


def test_search_grep_hits_value(data_root: Path) -> None:
    paths = get_paths()
    ensure_prefs(paths)
    append_fact("prefs.preferred_tz", "Pacific/Auckland", paths=paths)
    hits = search_facts("Pacific/Auckland", paths=paths)
    assert hits["count"] >= 1


def test_missing_mount_refuses_write(missing_root: Path) -> None:
    with pytest.raises(BodyFault):
        ensure_prefs()


@pytest.mark.tier_a
def test_append_survives_reread(data_root: Path) -> None:
    paths = get_paths()
    ensure_prefs(paths)
    append_fact("prefs.brief_enabled", False, paths=paths)
    raw = yaml.safe_load(paths.prefs_yaml.read_text(encoding="utf-8"))
    assert raw["brief_enabled"] is False
