"""Smoke: Streamlit chat panel and HUD modules import."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock


def test_render_chat_tab_importable() -> None:
    st_mock = MagicMock()
    st_mock.session_state = {}
    sys.modules["streamlit"] = st_mock
    try:
        from ada.observability.chat_panel import render_chat_tab

        assert callable(render_chat_tab)
    finally:
        sys.modules.pop("streamlit", None)


def test_hud_actions_importable() -> None:
    from ada.observability.hud_actions import (
        hud_apply_programme,
        hud_run_skill,
        skills_for_mission_defaults,
    )

    assert callable(hud_apply_programme)
    assert callable(hud_run_skill)
    assert callable(skills_for_mission_defaults)


def test_load_mission_template_public() -> None:
    from ada.mission_cli import load_mission_template, list_mission_template_names

    names = list_mission_template_names()
    if names:
        data = load_mission_template(names[0])
        assert "mission_slug" in data
