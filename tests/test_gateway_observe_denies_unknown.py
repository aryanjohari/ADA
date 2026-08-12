"""Gateway denies unknown tools with structured observations."""

from ada.tools.gateway import Gateway


def test_gateway_unknown_tool_denied():
    gw = Gateway(mode="observe")
    result = gw.execute("shell_exec", {"cmd": "ls"})
    assert result.ok is False
    assert result.outcome == "denied"
    assert result.denied_reason
    assert "shell_exec" in result.denied_reason
    obs = result.as_observation()
    assert obs["tool"] == "shell_exec"
    assert obs["args"] == {"cmd": "ls"}


def test_observe_mode_blocks_future_write_tool():
    gw = Gateway(
        mode="observe",
        extra_handlers={"fact_append": lambda args: {"wrote": True}},
    )
    result = gw.execute("fact_append", {"text": "hi"})
    assert result.ok is False
    assert result.outcome == "denied"
    assert "Observe" in (result.denied_reason or "")
