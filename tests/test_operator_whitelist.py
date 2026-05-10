"""Whitelisted argv builder for the operator UI."""

from __future__ import annotations

import pytest

from ada.observability.operator_whitelist import build_argv, validate_mission_slug


def test_validate_mission_slug() -> None:
    assert validate_mission_slug("acme_site")
    assert not validate_mission_slug("Acme")
    assert not validate_mission_slug("")


def test_mission_init_argv() -> None:
    argv = build_argv(
        "ada",
        command_id="mission_init",
        mission_init_slug="my-site",
        mission_init_title="T",
        mission_init_defaults_json='{"a": 1}',
    )
    assert argv == [
        "ada",
        "mission",
        "init",
        "my-site",
        "--title",
        "T",
        "--defaults-json",
        '{"a": 1}',
    ]


def test_mission_init_rejects_bad_json() -> None:
    with pytest.raises(ValueError, match="defaults-json"):
        build_argv(
            "ada",
            command_id="mission_init",
            mission_init_slug="my-site",
            mission_init_title="T",
            mission_init_defaults_json="[1,2]",
        )


def test_migrate_env_dry_argv() -> None:
    argv = build_argv(
        "ada",
        command_id="mission_migrate_env_dry",
        mission_slug="my-site",
        mission_migrate_only="GSC_SITE_URL,ADA_PROJECT_ID",
    )
    assert argv[-4:] == ["migrate-env", "my-site", "--only", "GSC_SITE_URL,ADA_PROJECT_ID"]
