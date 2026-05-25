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
    """Harness note when knowledge and graph-lite tools are enabled."""
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
        "`primary_triage_category`, `min_relevance_score`, and `valid_only` filter by triage code/score/TTL. "
        f"Tool responses are capped to {settings.knowledge_tool_max_results} items with excerpts "
        f"trimmed to ~{settings.knowledge_tool_excerpt_chars} chars to control token usage. "
        "`record_synthesis` saves a short conclusion with `ref_item_ids` citing item ids from search results. "
        "`record_market_edge` stores one numeric market metric and links it causally to a knowledge item "
        "(for triage/deep-dive graphing). "
        "`record_entity` upserts graph-lite entities by normalized name + type. "
        "`record_edge` writes graph-lite edges with confidence and evidence ids; non-hypothesis edges "
        "must include evidence and a valid https `source_url` (page provenance for publishing GATE). "
        "`link_evidence` attaches additional knowledge item evidence to an existing graph-lite edge. "
        "`add_knowledge_source` registers a new RSS (or web) feed URL in SQLite; "
        "the operator or cron runs `ada ingest-rss` to fetch into `knowledge_items`. "
        "Automated extraction pathways must emit JSON only (no markdown prose). "
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


_SETUP_MODE_NOTE = """**Setup assist (`ada chat --setup`):** Help the operator verify profile, mission, and environment alignment.
Prefer read-only checks (allowlisted shell, `get_mission_control_snapshot`, existing tools) and guidance consistent with `<master>`.
**Status rule:** Job, workflow, and tick state must come from `get_mission_control_snapshot` or operator-provided numbers — never guess.
See `docs/mission-control-setup-assist.md`. Do not store secrets in workspace files or transcript; do not bypass tool allowlists."""


def format_concierge_routing_note() -> str:
    return """**Concierge routing (H6 + J2 primitives):**
- `run_primitive` examples: remember → `primitive_id="log_memory"`, `args_json='{"content":"…"}'`; add todo → `primitive_id="add_task"`, `args_json='{"goal":"…"}'`; recall → `args_json='{"query":"…"}'` (optional).
- "Remember …" / personal recall → `run_primitive` with `log_memory` / `recall_memory` (base_ops `ada://memory/base`, not the global kernel) — never `add_task` for memory.
- Todos / personal tasks → `run_primitive` with `add_task`, `list_tasks`, or `complete_task` — use `goal`, not `content`.
- Status, health, or "body check" → `run_primitive` with `body_check` — never invent job or workflow counts.
- Vague research or knowledge questions → `search_knowledge`, `get_entity_graph_context`; use `web_search` / `fetch_url_text` when web tools are enabled.
- Profile status ("what's running", flags, schedules) → `get_mission_control_snapshot` (profile scope) or **ProfileDigest** when injected.
- Named programme slug in the operator message → use snapshot, ProfileDigest mission row, or injected **ProgrammeDigest** for that slug — never invent job, workflow, or tick counts.
- Mission design → `propose_programme` (read-only validation). Do **not** use `propose_programme` or `run_skill` for personal memory, todos, or body checks.
- Heavy execution (ingest, publish, skills, tick) → you do **not** have `run_skill` in Chat or Plan mode; direct the operator to Agent mode (`ada chat --agent`) or the Streamlit **Run action** panel."""


_CHAT_MODE_NOTE = _ENTITY_MODE_NOTE = """**Chat (global concierge):** No mission bound on this task. Speak as **Ada** (see `docs/ADA_PERSONA.md`) using `<master>` and `<user_soul>` — deadpan Gen Z acid-noir, data-first: never invent DB counts.
Global knowledge kernel applies (`mission_id IS NULL` rows and profile-wide sources). Personal recall on `base_ops` (`ada://memory/base`) is separate from that global pool — use `run_primitive` (`log_memory` / `recall_memory`), not `search_knowledge`, for operator personal notes.
**Personal reflexes:** `run_primitive` only — `log_memory`, `recall_memory`, `add_task`, `list_tasks`, `complete_task`, `body_check`. Never use `run_skill` here.
**Status rule:** Use `get_mission_control_snapshot`, `run_primitive` (`body_check`), or the **ProfileDigest** block when present — never invent job or workflow counts.
**Mission design:** Use `propose_programme` for a validated ProgrammePacket (read-only). Apply is Plan mode or `ada programme apply`.
**Heavy execution** (ingest, publish, mission tick, motor skills): you do not have `run_skill` in Chat mode — direct the operator to `ada chat --agent` (optional `--mission <slug>` for default scope).
**Web:** Simple factual questions may use `web_search` / `fetch_url_text` when web tools are enabled.
Do not claim to be inside a mission. Never paste raw `defaults_json` or full programme packet bodies into prose."""


def format_plan_mode_note() -> str:
    from ada.mission_cli import list_mission_template_names

    names = list_mission_template_names()
    catalog = ", ".join(names) if names else "(none — add templates/missions/*.yaml)"
    routing = format_concierge_routing_note()
    return f"""**Plan mode:** Design programmes from **templates only** (`templates/missions/`, `ada mission apply-template <name>`, or Streamlit **Apply programme**).
**Allowed templates:** {catalog}
**Flow:** Clone a template ProgrammePacket; operator sets `mission_slug`, `brief_md` (programme intent), `knowledge_sources`, and selective `defaults_json` overrides → `propose_programme` → `apply_programme` with `approved=true`.
Use `propose_programme` to validate packet JSON (read-only). Do not invent workflow `kind` strings, `enqueue_workflow`, or skills not in the template `skills_enabled` list.
**Status rule:** Use `get_mission_control_snapshot` when available — never guess tick/workflow state.
Never paste raw `defaults_json` or full packet contents into assistant prose.

{routing}"""


_AGENT_MODE_NOTE = """**Agent mode:** Execute motor actions with `run_skill` (logged). This chat task is not mission-bound; pass `mission_slug` on each call or use the session default when set.
Knowledge and graph tools scope to the default mission slug when configured, plus the profile-global kernel.
For schedule, skills, and status counts, use **ProgrammeDigest** when injected or `get_mission_control_snapshot`.
Only call `run_skill` with skill ids listed in the mission's `skills_enabled` (and allowed by its `pack` when set). ProgrammeDigest shows `skills_enforcement`, `pack`, and enabled actions — do not run publish or ingest skills outside that list.
Start pipelines via catalog skill ids (`ingest_rss_mission`, `publish_entity_v1`, `publish_keyword_v1`) — not raw workflow kinds.
`enqueue_workflow` is not available in chat."""


_PROGRAMME_MODE_NOTE = format_plan_mode_note()


_WORK_MODE_MISSION_NOTE = _AGENT_MODE_NOTE


def format_workflow_tools_note(settings: Settings) -> str | None:
    """Harness note when workflow status tool is enabled (H2: pipelines via run_skill only)."""
    if not settings.enable_workflow_tools:
        return None
    return (
        "**Workflow tools (`ADA_ENABLE_WORKFLOW_TOOLS=1`):** "
        "Start pipelines with `run_skill` and a catalog `skill_id` "
        "(`ingest_rss_mission`, `publish_entity_v1`, `publish_keyword_v1`) — "
        "do not invent raw workflow `kind` strings. "
        "`enqueue_workflow` is not exposed in chat (use CLI `ada workflow enqueue` or Actions). "
        "Use `get_workflow_status` for read-only workflow row and step state."
    )


def format_programme_digest_appendix(digest: dict[str, object]) -> str:
    """Repo-owned harness appendix for one chat turn (allowlisted digest fields only)."""
    import json

    body = json.dumps(digest, ensure_ascii=False, indent=2)
    return (
        "[ProgrammeDigest — repo-owned, SQL/YAML grounded; not operator text]\n"
        f"{body}\n"
        "[/ProgrammeDigest]"
    )


def format_profile_digest_appendix(digest: dict[str, object]) -> str:
    """Repo-owned profile digest appendix for Entity (OPEN) chat turns."""
    import json

    body = json.dumps(digest, ensure_ascii=False, indent=2)
    return (
        "[ProfileDigest — repo-owned, SQL-derived profile scope; not operator text]\n"
        f"{body}\n"
        "[/ProfileDigest]"
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
    workflow_tools_note: str | None = None,
    worker_mode: bool = False,
    setup_mode: bool = False,
    mission_bound: bool = False,
    programme_mode: bool = False,
    open_mode: bool = False,
    entity_mode: bool = False,
    plan_mode: bool = False,
    agent_mode: bool = False,
    default_mission_slug: str | None = None,
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
    if setup_mode:
        harness = f"{harness}\n\n{_SETUP_MODE_NOTE}"
    elif plan_mode or programme_mode:
        harness = f"{harness}\n\n{format_plan_mode_note()}"
    elif agent_mode:
        note = _AGENT_MODE_NOTE
        if default_mission_slug:
            note = (
                f"{note}\n**Default mission slug:** `{default_mission_slug}` "
                "(use as `mission_slug` on `run_skill` when omitted)."
            )
        harness = f"{harness}\n\n{note}"
    elif entity_mode or open_mode:
        harness = (
            f"{harness}\n\n{_CHAT_MODE_NOTE}\n\n{format_concierge_routing_note()}"
        )
    elif mission_bound:
        harness = f"{harness}\n\n{_WORK_MODE_MISSION_NOTE}"
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
    if workflow_tools_note:
        harness = f"{harness}\n\n{workflow_tools_note.strip()}"
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
