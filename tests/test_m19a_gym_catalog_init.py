"""M19a gym catalog auto-init on first life DB open."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from ada.io.paths import get_paths
from ada.logs.connection import open_life_db
from ada.logs.gym import _lookup_exercise
from ada.logs.gym_import import (
    _normalize_external_item,
    ensure_exercise_catalog,
    names_fold_match,
)
from ada.logs.migrations import migrate_life_db

BUNDLED_SEED_COUNT = 20


def _catalog_count(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM exercise_catalog").fetchone()[0])


def _open_migrated(data_root: Path) -> tuple[sqlite3.Connection, Path]:
    paths = get_paths(data_root)
    paths.ensure_logs_dirs()
    conn = sqlite3.connect(paths.life_logs_db)
    conn.row_factory = sqlite3.Row
    migrate_life_db(conn)
    return conn, paths


def _remote_fixture() -> list[dict]:
    return [
        {
            "id": "remote-1",
            "name": "Remote bench press",
            "primaryMuscles": ["chest"],
            "equipment": "barbell",
            "category": "push",
        },
        {
            "id": "remote-2",
            "name": "Remote pull-up",
            "primaryMuscles": ["back"],
            "equipment": "bodyweight",
            "category": "pull",
        },
    ]


@pytest.mark.tier_a
def test_open_life_db_auto_init_bundled_seed(
    data_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty catalog → first open_life_db imports bundled seed (no HTTP)."""
    monkeypatch.setenv("ADA_GYM_CATALOG_FETCH", "off")
    with open_life_db(paths=get_paths(data_root)) as conn:
        count = _catalog_count(conn)
        row = conn.execute(
            "SELECT canonical_name FROM exercise_catalog WHERE lower(canonical_name) = ?",
            ("pull-up",),
        ).fetchone()
    assert count == BUNDLED_SEED_COUNT
    assert row is not None


@pytest.mark.tier_a
def test_ensure_remote_fetch_imports_and_cleans_tmp(
    data_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mock HTTP success → remote JSON imported; tmp file removed."""
    monkeypatch.setenv("ADA_GYM_CATALOG_FETCH", "full")
    remote = _remote_fixture()

    def fake_get(url: str, **kwargs) -> httpx.Response:
        assert "free-exercise-db" in url
        return httpx.Response(200, json=remote)

    conn, paths = _open_migrated(data_root)
    try:
        result = ensure_exercise_catalog(conn, paths=paths, http_get=fake_get)
        assert result is not None
        assert result["source"] == "remote"
        assert result["imported"] == len(remote)
        assert _catalog_count(conn) >= len(remote)
        names = {
            r[0]
            for r in conn.execute(
                "SELECT canonical_name FROM exercise_catalog"
            ).fetchall()
        }
        assert "Remote pull-up" in names
        assert "Flat bench press" in names or any(
            names_fold_match("flat bench", n) for n in names
        )
    finally:
        conn.close()

    assert not list(paths.logs.glob("free-exercise-db-*.json"))


@pytest.mark.tier_a
def test_ensure_fetch_failure_falls_back_to_bundled(
    data_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mock HTTP failure → bundled seed still imported; DB non-empty."""
    monkeypatch.setenv("ADA_GYM_CATALOG_FETCH", "full")

    def fail_get(url: str, **kwargs) -> httpx.Response:
        return httpx.Response(503, text="unavailable")

    conn, paths = _open_migrated(data_root)
    try:
        result = ensure_exercise_catalog(conn, paths=paths, http_get=fail_get)
        assert result is not None
        assert result["source"] == "bundled"
        assert _catalog_count(conn) == BUNDLED_SEED_COUNT
    finally:
        conn.close()


@pytest.mark.tier_a
def test_ensure_second_call_is_noop(
    data_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Second ensure_exercise_catalog call does not fetch again."""
    monkeypatch.setenv("ADA_GYM_CATALOG_FETCH", "full")
    mock_get = MagicMock(
        return_value=httpx.Response(200, json=_remote_fixture())
    )

    conn, paths = _open_migrated(data_root)
    try:
        first = ensure_exercise_catalog(conn, paths=paths, http_get=mock_get)
        assert first is not None
        count_after_first = _catalog_count(conn)
        second = ensure_exercise_catalog(conn, paths=paths, http_get=mock_get)
        assert second is None
        assert _catalog_count(conn) == count_after_first
        assert mock_get.call_count == 1
    finally:
        conn.close()


@pytest.mark.tier_a
def test_ensure_existing_catalog_noop(data_root: Path) -> None:
    """Pre-populated catalog → ensure is no-op (count unchanged)."""
    conn, paths = _open_migrated(data_root)
    try:
        conn.execute(
            """
            INSERT INTO exercise_catalog (
              exercise_id, canonical_name, aliases_json, body_parts_json,
              equipment_json, movement, source, external_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "seed-only",
                "Operator custom",
                "[]",
                "[]",
                "[]",
                "other",
                "custom",
                None,
            ),
        )
        conn.commit()
        before = _catalog_count(conn)
        result = ensure_exercise_catalog(conn, paths=paths)
        assert result is None
        assert _catalog_count(conn) == before
    finally:
        conn.close()


@pytest.mark.tier_a
def test_gym_init_cli_json(data_root: Path) -> None:
    from typer.testing import CliRunner

    from ada.cli.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["life", "gym-init", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["catalog_count"] == BUNDLED_SEED_COUNT


@pytest.mark.tier_a
def test_default_fetch_enabled_uses_http(
    data_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unset env (production default) tries remote fetch."""
    monkeypatch.delenv("ADA_GYM_CATALOG_FETCH", raising=False)
    remote = _remote_fixture()
    mock_get = MagicMock(return_value=httpx.Response(200, json=remote))
    conn, paths = _open_migrated(data_root)
    try:
        result = ensure_exercise_catalog(conn, paths=paths, http_get=mock_get)
        assert result is not None
        assert result["source"] == "remote"
        assert mock_get.call_count == 1
    finally:
        conn.close()


@pytest.mark.tier_a
def test_normalize_free_exercise_db_tags() -> None:
    """force/muscles/equipment map into movement + body_parts + aliases."""
    norm = _normalize_external_item(
        {
            "id": "Pullups",
            "name": "Pullups",
            "force": "pull",
            "category": "strength",
            "primaryMuscles": ["lats"],
            "secondaryMuscles": ["biceps", "middle back"],
            "equipment": "body only",
        }
    )
    assert norm is not None
    assert norm["movement"] == "pull"
    assert "lats" in norm["body_parts"]
    assert "biceps" in norm["body_parts"]
    assert "bodyweight" in norm["equipment"]
    alias_l = {a.lower() for a in norm["aliases"]}
    assert "pull-ups" in alias_l or "pull-up" in alias_l
    assert names_fold_match("pull-ups", "Pullups")


@pytest.mark.tier_a
def test_nl_pullups_hits_remote_catalog_not_facts(
    data_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """pull-ups NL resolves to imported Pullups row (catalog, not FACTS)."""
    monkeypatch.setenv("ADA_GYM_CATALOG_FETCH", "full")
    remote = [
        {
            "id": "Pullups",
            "name": "Pullups",
            "force": "pull",
            "category": "strength",
            "primaryMuscles": ["lats"],
            "secondaryMuscles": ["biceps"],
            "equipment": "body only",
        }
    ]

    def fake_get(url: str, **kwargs) -> httpx.Response:
        return httpx.Response(200, json=remote)

    conn, paths = _open_migrated(data_root)
    try:
        ensure_exercise_catalog(conn, paths=paths, http_get=fake_get)
        hit = _lookup_exercise(conn, "pull-ups", paths=paths)
        assert hit["source"] == "catalog"
        assert names_fold_match(hit["canonical_name"], "pull-ups")
        assert hit.get("movement") == "pull"
        assert "lats" in (hit.get("body_parts") or [])
        bench = _lookup_exercise(conn, "flat bench", paths=paths)
        assert bench["source"] == "catalog"
    finally:
        conn.close()
