"""Soul load + trusted harness → system_instruction (claude_logic §11)."""

from __future__ import annotations

from pathlib import Path


def read_soul_text(soul_path: Path) -> str:
    if not soul_path.is_file():
        return ""
    return soul_path.read_text(encoding="utf-8")


def build_system_instruction(
    *,
    soul_text: str,
    state_db_display_path: str,
) -> str:
    """
    Trusted harness (not from soul) + <user_soul> wrapper for untrusted prose.
    """
    harness = f"""You are ADA, a concise autonomous assistant running on a local device.
Conversation turns are persisted to a local SQLite database at: {state_db_display_path}
Use the stored history for continuity across turns. Answer helpfully and naturally.
Do not claim you can run SQL or access files unless a tool explicitly allows it (none in this build)."""
    soul_block = soul_text.strip()
    if soul_block:
        return f"""{harness}

<user_soul>
{soul_block}
</user_soul>"""
    return harness
