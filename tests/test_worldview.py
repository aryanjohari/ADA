"""WORLDVIEW cite validation + no FACT clobber (M04 §10.1)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ada.body.identity import create_identity
from ada.io.paths import get_paths
from ada.memory.facts import ensure_prefs, get_fact
from ada.memory.worldview import WorldviewError, search_worldview, write_digest


def test_worldview_rejects_empty_cites(data_root: Path) -> None:
    ensure_prefs(get_paths())
    with pytest.raises(WorldviewError):
        write_digest("hello", cites=[])


def test_worldview_write_does_not_mutate_identity(data_root: Path) -> None:
    paths = get_paths()
    card, _ = create_identity(paths=paths)
    born = card.born_at
    ensure_prefs(paths)
    write_digest(
        "Interpretive note about the host.",
        cites=["facts.identity.body_hostname", "lifecycle:birth"],
        paths=paths,
    )
    raw = yaml.safe_load(paths.identity_yaml.read_text(encoding="utf-8"))
    assert raw["born_at"] == born
    assert get_fact("prefs.brief_time", paths=paths)["found"]


def test_worldview_search(data_root: Path) -> None:
    paths = get_paths()
    ensure_prefs(paths)
    write_digest(
        "Running joke about USB-root risk.",
        cites=["prefs.tease_ok"],
        paths=paths,
    )
    hits = search_worldview("USB-root", paths=paths)
    assert hits["count"] >= 1
