"""Setup assist orchestration profile caps."""

from __future__ import annotations

from ada.orchestration_profile import SETUP_ASSIST, orchestrate_turn_kwargs


def test_setup_assist_caps_tool_rounds_and_web() -> None:
    kw = orchestrate_turn_kwargs(
        SETUP_ASSIST,
        base_max_tool_rounds=12,
        include_gsc_read_tools=True,
        web_config=object(),
    )
    assert kw["max_tool_rounds"] == 6
    assert kw["web_config"] is None
    assert kw["include_gsc_read_tools"] is False
