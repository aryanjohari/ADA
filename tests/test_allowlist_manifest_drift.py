"""Manifest drift: code allowlist ids vs docs/ALLOWLIST_MANIFEST.md."""

from __future__ import annotations

from pathlib import Path

import pytest

from ada.config import _find_project_root
from ada.motor.manifest_sync import (
    collect_code_ids,
    parse_manifest_ids,
)


@pytest.fixture
def manifest_path() -> Path:
    return _find_project_root() / "docs" / "ALLOWLIST_MANIFEST.md"


def test_manifest_drift_chat_tools_and_ops(manifest_path: Path, tmp_path) -> None:
    mem = tmp_path / "memory"
    mem.mkdir()
    (mem / "shell_allowlist.txt").write_text("echo test\n", encoding="utf-8")
    code_ids = collect_code_ids(memory_dir=mem)
    manifest_ids = parse_manifest_ids(manifest_path)
    only_code = sorted(code_ids - manifest_ids)
    only_manifest = sorted(manifest_ids - code_ids - frozenset(
        {"host.web_fetch", "host.knowledge_feed", "host.gov_api", "streamlit.sql_select"}
    ))
    assert not only_code, f"ids in code but not manifest: {only_code[:20]}"
    assert not only_manifest, f"ids in manifest but not code: {only_manifest[:20]}"
