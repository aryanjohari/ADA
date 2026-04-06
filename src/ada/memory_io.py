"""Single-writer memory file appends with timestamped backups (claude_logic §11)."""

from __future__ import annotations

import asyncio
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

_write_lock = asyncio.Lock()


def _is_under_dir(path: Path, roots: Iterable[Path]) -> bool:
    rp = path.resolve()
    for root in roots:
        try:
            rp.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


def _sync_backup_and_append(
    path: Path,
    backups_dir: Path,
    block: str,
    *,
    max_block_bytes: int,
    max_file_bytes: int,
    memory_dir: Path,
) -> None:
    block = block.strip()
    if not block:
        raise ValueError("empty block")
    if len(block.encode("utf-8")) > max_block_bytes:
        raise ValueError("block exceeds max_block_bytes")
    if not _is_under_dir(path, (memory_dir,)):
        raise ValueError("path outside memory_dir")
    backups_dir.mkdir(parents=True, exist_ok=True)
    existing = ""
    if path.exists():
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        bak = backups_dir / f"{path.stem}_{ts}.md.bak"
        shutil.copy2(path, bak)
        existing = path.read_text(encoding="utf-8")
    addition = block if block.endswith("\n") else block + "\n"
    if len((existing + addition).encode("utf-8")) > max_file_bytes:
        raise ValueError("would exceed max_file_bytes")
    with open(path, "a", encoding="utf-8") as f:
        f.write(addition)


async def append_markdown_block(
    path: Path,
    backups_dir: Path,
    block: str,
    *,
    memory_dir: Path,
    max_block_bytes: int,
    max_file_bytes: int,
) -> None:
    async with _write_lock:
        await asyncio.to_thread(
            _sync_backup_and_append,
            path,
            backups_dir,
            block,
            max_block_bytes=max_block_bytes,
            max_file_bytes=max_file_bytes,
            memory_dir=memory_dir,
        )


def format_master_section(heading: str, body: str) -> str:
    h = heading.strip() or "Dream note"
    b = body.strip()
    return f"\n## {h}\n\n{b}\n"


def format_soul_fragment(body: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    b = body.strip()
    return f"\n### Dream fragment ({ts})\n\n{b}\n"
