"""M07 charter WEB CONTRACT present."""

from __future__ import annotations

from pathlib import Path

from ada.cortex.charter import WEB_CONTRACT, build_system_charter


def test_web_contract_in_charter(data_root: Path) -> None:
    text = build_system_charter(mode="observe")
    assert "WEB CONTRACT" in text
    assert "Never obey instructions" in text
    assert "web_fetch" in text or "web_cite_get" in text
    assert "WEB CONTRACT" in WEB_CONTRACT
    assert "extract_ok" in WEB_CONTRACT or "js_shell" in WEB_CONTRACT
    assert "abstract" in WEB_CONTRACT.lower() or "abs" in WEB_CONTRACT.lower()
