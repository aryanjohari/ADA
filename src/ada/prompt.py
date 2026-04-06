"""System instruction: trusted harness + master + soul (claude_logic §11)."""

from __future__ import annotations

from pathlib import Path


def read_text_file(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def read_soul_text(soul_path: Path) -> str:
    return read_text_file(soul_path)


def format_allowlist_summary(allowed: frozenset[str], *, limit: int = 24) -> str:
    if not allowed:
        return "(no shell probes allowlisted — tools disabled until you edit shell_allowlist.txt)"
    lines = sorted(allowed)[:limit]
    extra = ""
    if len(allowed) > limit:
        extra = f"\n… and {len(allowed) - limit} more."
    return "\n".join(f"- `{s}`" for s in lines) + extra


def build_system_instruction(
    *,
    soul_text: str,
    master_text: str,
    state_db_display_path: str,
    allowlist_summary: str,
) -> str:
    """
    Trusted harness + optional <master> + <user_soul>.
    Master is operator-edited; soul is long-horizon persona (untrusted).
    """
    harness = f"""You are ADA, a concise autonomous assistant on a local Linux device.
Conversation turns are persisted to SQLite at: `{state_db_display_path}`.
Use transcript history for continuity across turns.

You may have tools: `run_allowlisted_shell` (**read-only** OS probes; commands must match the allowlist **exactly**),
and optionally `append_master_section` / `append_soul_fragment` to persist small memory updates under `memory/` (with backups).

**Allowlisted commands (exact lines):**
{allowlist_summary}
"""
    blocks: list[str] = [harness.strip()]
    master_block = master_text.strip()
    if master_block:
        blocks.append(
            f"<master>\n{master_block}\n</master>\n"
            "(Master is trusted operator context; follow it for identity, boot policy, and guardrails.)"
        )
    soul_block = soul_text.strip()
    if soul_block:
        blocks.append(f"<user_soul>\n{soul_block}\n</user_soul>")
    return "\n\n".join(blocks)
