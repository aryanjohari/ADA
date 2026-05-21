"""Propose-time skills_enabled validation (Hands H5)."""

from __future__ import annotations

from ada.programme.propose import propose_packet


def test_propose_unknown_skill_returns_error() -> None:
    out = propose_packet(
        {
            "mission_slug": "x",
            "title": "X",
            "defaults_json": {"pack": "core-ops"},
            "skills_enabled": ["nonexistent_skill_xyz"],
        }
    )
    assert "error" in out
    assert "unknown skill" in out["error"].lower() or "nonexistent" in out["error"]


def test_propose_pack_without_skills_returns_error() -> None:
    out = propose_packet(
        {
            "mission_slug": "x",
            "title": "X",
            "defaults_json": {"pack": "core-ops"},
            "skills_enabled": [],
        }
    )
    assert "error" in out
    assert "requires explicit skills_enabled" in out["error"]
