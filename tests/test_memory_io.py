from __future__ import annotations

import pytest

from ada.memory_io import append_markdown_block


@pytest.mark.asyncio
async def test_append_creates_backup(tmp_path):
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    path = memory_dir / "master.md"
    path.write_text("# Title\n", encoding="utf-8")
    backups = memory_dir / "backups"
    await append_markdown_block(
        path,
        backups,
        "\n## Section\n\nbody\n",
        memory_dir=memory_dir,
        max_block_bytes=10_000,
        max_file_bytes=100_000,
    )
    txt = path.read_text(encoding="utf-8")
    assert "## Section" in txt
    assert list(backups.glob("*.bak"))
