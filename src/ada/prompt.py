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


def format_schema_digest_note(text: str) -> str | None:
    """Non-empty operator-maintained schema summary (e.g. memory/schema_digest.md)."""
    t = text.strip()
    if not t:
        return None
    return (
        "**SQLite schema digest (operator-maintained file `memory/schema_digest.md`):**\n"
        f"{t}\n\n"
        "(Use this as ground truth for `tasks`, `messages`, and `web_sources`; update the file when DDL changes.)"
    )


def format_session_web_sources_list_note(settings: Settings) -> str | None:
    """One-line harness note when read-only list_session_web_sources is enabled."""
    if not settings.enable_web_sources_tool:
        return None
    return (
        "**Session web index:** when `ADA_ENABLE_WEB_SOURCES_TOOL=1`, tool `list_session_web_sources` "
        "returns recent `web_sources` rows for the **current** task/session (read-only)."
    )


def format_knowledge_tools_note(settings: Settings) -> str | None:
    """Harness note when search_knowledge / record_synthesis / add_knowledge_source are enabled."""
    if not settings.enable_knowledge_tools:
        return None
    allow = ", ".join(sorted(settings.knowledge_feed_host_allowlist)[:12])
    more = ""
    if len(settings.knowledge_feed_host_allowlist) > 12:
        more = " …"
    allow_line = (
        f"**Feed host allowlist** (add_knowledge_source): {allow}{more}"
        if settings.knowledge_feed_host_allowlist
        else "**Feed host allowlist:** empty (any https/http host allowed for new feeds — use ADA_KNOWLEDGE_FEED_HOST_ALLOWLIST to restrict)."
    )
    return (
        "**Knowledge tools (`ADA_ENABLE_KNOWLEDGE_TOOLS=1`):** "
        "`search_knowledge` searches stored `knowledge_items` (RSS ingest, etc.); optional "
        "`min_relevance_score` and `valid_only` filter by score/TTL. "
        f"Tool responses are capped to {settings.knowledge_tool_max_results} items with excerpts "
        f"trimmed to ~{settings.knowledge_tool_excerpt_chars} chars to control token usage. "
        "`record_synthesis` saves a short conclusion with `ref_item_ids` citing item ids from search results. "
        "`record_market_edge` stores one numeric market metric and links it causally to a knowledge item "
        "(for triage/deep-dive graphing). "
        "`add_knowledge_source` registers a new RSS (or web) feed URL in SQLite; "
        "the operator or cron runs `ada ingest-rss` to fetch into `knowledge_items`. "
        f"{allow_line}"
    )


def format_web_tools_note(settings: Settings) -> str:
    """Harness note when web search / fetch tools are enabled."""
    allow = ", ".join(sorted(settings.web_fetch_host_allowlist)[:8])
    more_allow = ""
    if len(settings.web_fetch_host_allowlist) > 8:
        more_allow = " …"
    allow_line = (
        f"**Host allowlist** (fetch): {allow}{more_allow}"
        if settings.web_fetch_host_allowlist
        else "**Host allowlist:** empty (public https only; SSRF guards apply)."
    )
    search_on = bool(settings.serper_api_key.strip())
    return (
        "**Web tools (`ADA_ENABLE_WEB_TOOLS=1`):** "
        + ("`web_search` (Serper) is available. " if search_on else "`web_search` is disabled without Serper API key. ")
        + "`fetch_url_text` retrieves page text (Jina Reader or direct httpx per `ADA_WEB_FETCH_MODE`). "
        f"Caps: max {settings.web_search_max_results} search hits; "
        f"max {settings.web_fetch_max_urls} URLs per fetch; "
        f"max ~{settings.web_fetch_max_chars} chars total per fetch. "
        f"{allow_line} "
        "Prefer **search snippets first**; call `fetch_url_text` only when the task needs full-page evidence."
    )


_WORKER_MODE_NOTE = """**Worker context (`ada daemon`):** You are processing a **queued goal** task, not interactive `ada chat`.
Prefer `read_task_plan` early if this run may resume multi-step work; update with `write_task_plan` as progress is made.
For **architecture-proposal** goal tasks (Phase C in `<master>`), prefer completing `read_task_plan` → draft → `append_master_section` (or `write_workspace_file` if file tools are on) in **one** turn when possible; use a follow-up goal if you hit token or append limits.
Still follow `<master>` and soul guardrails below."""


def build_system_instruction(
    *,
    soul_text: str,
    master_text: str,
    state_db_display_path: str,
    allowlist_summary: str,
    file_tools_note: str | None = None,
    web_tools_note: str | None = None,
    schema_digest_note: str | None = None,
    session_web_sources_list_note: str | None = None,
    knowledge_tools_note: str | None = None,
    worker_mode: bool = False,
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
    if worker_mode:
        harness = f"{harness}\n\n{_WORKER_MODE_NOTE}"
    if file_tools_note:
        harness = (
            f"{harness}\n\n{file_tools_note.strip()}\n\n"
            "(When workspace file tools are enabled, follow the contract above.)"
        )
    if web_tools_note:
        harness = (
            f"{harness}\n\n{web_tools_note.strip()}\n\n"
            "(When web tools are enabled, follow snippet-first policy above.)"
        )
    if schema_digest_note:
        harness = f"{harness}\n\n{schema_digest_note.strip()}"
    if session_web_sources_list_note:
        harness = f"{harness}\n\n{session_web_sources_list_note.strip()}"
    if knowledge_tools_note:
        harness = f"{harness}\n\n{knowledge_tools_note.strip()}"
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
