"""Birth-once identity + mount honesty."""

from __future__ import annotations

from pathlib import Path

import pytest

from ada.body.identity import create_identity, load_identity
from ada.body.lifecycle import append_event, append_wake, read_events
from ada.io.paths import BodyFault, get_paths, require_ada_data


def test_mount_missing_refuses_writes(missing_root: Path) -> None:
    with pytest.raises(BodyFault) as ei:
        require_ada_data()
    assert ei.value.code == 3

    with pytest.raises(BodyFault):
        create_identity()

    with pytest.raises(BodyFault):
        append_event("note", summary="should fail")


def test_birth_once(data_root: Path) -> None:
    paths = get_paths()
    card1, created1 = create_identity(paths=paths)
    assert created1 is True
    born = card1.born_at
    card2, created2 = create_identity(paths=paths)
    assert created2 is False
    assert card2.born_at == born
    on_disk = load_identity(paths)
    assert on_disk.born_at == born


def test_wake_not_birth_when_identity_exists(data_root: Path) -> None:
    paths = get_paths()
    create_identity(paths=paths)
    append_wake(paths=paths)
    append_wake(paths=paths)
    types = [e.type for e in read_events(paths)]
    assert types.count("birth") == 1
    assert types.count("wake") == 2
