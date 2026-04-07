"""System instruction: trusted harness + master + soul (claude_logic §11)."""

from __future__ import annotations

from pathlib import Path

from ada.config import Settings


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


def format_file_tools_note(settings: Settings) -> str:
    """Harness note when sandboxed file tools are enabled (roots, denylist, browser)."""
    roots = settings.file_sandbox_roots
    root_lines = "\n".join(f"- `{r}`" for r in roots)
    deny_preview = sorted({str(p.resolve()) for p in settings.file_deny_prefixes})
    deny_block = "\n".join(f"- `{d}`" for d in deny_preview[:15])
    more = ""
    if len(deny_preview) > 15:
        more = f"\n… and {len(deny_preview) - 15} more prefix rules."
    extra_base = ""
    if settings.file_deny_basenames_extra:
        extra_base = (
            f" Extra forbidden basenames (from env): "
            f"{', '.join(sorted(settings.file_deny_basenames_extra))}."
        )
    return (
        "**Workspace file tools:** `list_workspace_directory` (one level, non-recursive), "
        "`read_workspace_file`, and `write_workspace_file`. "
        "Paths must resolve inside one of these roots (symlinks resolved):\n"
        f"{root_lines}\n\n"
        "**Denied path prefixes** (read/list/write blocked):\n"
        f"{deny_block}{more}\n\n"
        "**Denied basenames** anywhere under roots: `.env`, `id_rsa`, any `*.pem`."
        f"{extra_base}\n"
        "Use `append_master_section` / `append_soul_fragment` for long-term memory; "
        "do not put secrets in workspace files the model can read. "
        "The SQLite database and `memory/` markdown files are not reachable through these file tools."
    )


def build_system_instruction(
    *,
    soul_text: str,
    master_text: str,
    state_db_display_path: str,
    allowlist_summary: str,
    file_tools_note: str | None = None,
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
    harness = harness.strip()
    if file_tools_note:
        harness = (
            f"{harness}\n\n{file_tools_note.strip()}\n\n"
            "(When workspace file tools are enabled, follow the contract above.)"
        )
    blocks: list[str] = [harness]
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
