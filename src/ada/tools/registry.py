"""Gemini `Tool` declarations — shell + optional memory append tools."""

from __future__ import annotations

from collections.abc import Sequence

from google.genai import types

# Subsets for Phase 3 workflow steps (capability matrix; ROADMAP §8.2).
KNOWLEDGE_TOOLS_EXTRACT = frozenset({"record_entity", "record_edge", "link_evidence"})
KNOWLEDGE_TOOLS_SYNTHESIZE = frozenset({"search_knowledge", "record_synthesis"})


def _check_token_usage_declaration() -> types.FunctionDeclaration:
    return types.FunctionDeclaration(
        name="check_token_usage",
        description=(
            "Return this session's summed token counts from the usage ledger "
            "(input_tokens, output_tokens, total). Call periodically during long "
            "multi-step work to stay within budget."
        ),
        parameters_json_schema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    )


def _mission_control_snapshot_declaration() -> types.FunctionDeclaration:
    return types.FunctionDeclaration(
        name="get_mission_control_snapshot",
        description=(
            "Read-only: return SQLite-derived mission control snapshot (flags, counts, tick state). "
            "Use for setup assist status — do not invent job or workflow state without calling this."
        ),
        parameters_json_schema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    )


def _run_skill_declaration() -> types.FunctionDeclaration:
    return types.FunctionDeclaration(
        name="run_skill",
        description=(
            "Execute a registered motor skill by id (workflow enqueue, goal add, or dry-run ada argv). "
            "Params must match the skill spec; high-risk skills need approved=true after operator confirm."
        ),
        parameters_json_schema={
            "type": "object",
            "properties": {
                "skill_id": {"type": "string", "description": "Skill id from motor registry."},
                "params_json": {
                    "type": "string",
                    "description": "JSON object of skill parameters.",
                },
                "mission_slug": {
                    "type": "string",
                    "description": "Mission slug (defaults to session mission when bound).",
                },
                "approved": {
                    "type": "boolean",
                    "description": "Operator approved high-risk / require_approval skills.",
                },
            },
            "required": ["skill_id"],
        },
    )


def _propose_programme_declaration() -> types.FunctionDeclaration:
    return types.FunctionDeclaration(
        name="propose_programme",
        description=(
            "Validate and return a canonical ProgrammePacket JSON (read-only — does not write SQLite). "
            "Use in programme design mode before operator runs apply."
        ),
        parameters_json_schema={
            "type": "object",
            "properties": {
                "packet_json": {
                    "type": "string",
                    "description": (
                        "Programme packet JSON object string, e.g. "
                        '{"mission_slug":"my-mission","title":"…","brief_md":"Operator intent…",'
                        '"skills_enabled":["ingest_rss_mission"],"defaults_json":{}}.'
                    ),
                },
            },
            "required": ["packet_json"],
        },
    )


def _apply_programme_declaration() -> types.FunctionDeclaration:
    return types.FunctionDeclaration(
        name="apply_programme",
        description=(
            "Apply a validated ProgrammePacket to SQLite (missions, sources, cron snippet). "
            "Requires approved=true after operator confirmation; approved=false performs no DB writes."
        ),
        parameters_json_schema={
            "type": "object",
            "properties": {
                "packet_json": {
                    "type": "string",
                    "description": (
                        "Full programme packet JSON including brief_md (programme intent), "
                        "skills_enabled, defaults_json, schedule_hint_json, knowledge_sources."
                    ),
                },
                "approved": {
                    "type": "boolean",
                    "description": "Operator approved apply (Y/n gate).",
                },
            },
            "required": ["packet_json", "approved"],
        },
    )


def _memory_function_declarations() -> list[types.FunctionDeclaration]:
    return [
        types.FunctionDeclaration(
            name="append_master_section",
            description=(
                "Append a section to memory/master.md (timestamped backup first). "
                "Use for durable worldview: hardware facts, operator preferences, recurring workflows. "
                "Keep body compact Markdown."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "heading": {
                        "type": "string",
                        "description": "Short section title (becomes ## heading).",
                    },
                    "body": {
                        "type": "string",
                        "description": "Markdown body (bullets welcome).",
                    },
                },
                "required": ["heading", "body"],
            },
        ),
        types.FunctionDeclaration(
            name="append_soul_fragment",
            description=(
                "Append a small persona note to memory/soul.md (backup first). "
                "Use sparingly: tone, style, or identity tweaks only—never secrets."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "1–3 short sentences max.",
                    },
                },
                "required": ["text"],
            },
        ),
    ]


def _file_function_declarations() -> list[types.FunctionDeclaration]:
    return [
        types.FunctionDeclaration(
            name="list_workspace_directory",
            description=(
                "List files and subdirectories in one workspace directory (non-recursive). "
                "Paths follow the same sandbox rules as read_workspace_file. "
                "Symlink targets are not followed; entries may show kind symlink. "
                "Result may be truncated if there are many entries; check `truncated`."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Directory path relative to primary sandbox root, or absolute under a root. "
                            "Use '.' for the primary root."
                        ),
                    },
                    "max_entries": {
                        "type": "integer",
                        "description": "Max entries to return (capped by harness).",
                    },
                },
                "required": [],
            },
        ),
        types.FunctionDeclaration(
            name="read_workspace_file",
            description=(
                "Read a text file from the configured workspace sandbox (UTF-8). "
                "Relative paths are resolved from the primary sandbox root; absolute paths must still lie under a root. "
                "Large files may be truncated; check `truncated` in the response."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path (relative to primary sandbox root, or absolute within sandbox).",
                    },
                },
                "required": ["path"],
            },
        ),
        types.FunctionDeclaration(
            name="write_workspace_file",
            description=(
                "Create or overwrite/append a UTF-8 text file inside the workspace sandbox. "
                "Same path rules as read_workspace_file. Use create_parents=true if intermediate directories should be created."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Destination file path (relative or absolute under sandbox).",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full file body to write (UTF-8).",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["write", "append"],
                        "description": "'write' truncates then writes; 'append' appends to existing file.",
                    },
                    "create_parents": {
                        "type": "boolean",
                        "description": "If true, create missing parent directories before writing.",
                    },
                },
                "required": ["path", "content"],
            },
        ),
    ]


def _goal_recall_function_declaration() -> types.FunctionDeclaration:
    return types.FunctionDeclaration(
        name="read_goal_task_view",
        description=(
            "Read-only: load one queued/completed goal task by tasks.id from SQLite. "
            "Use to recall another goal's outcome (goal text, status, current_output, plan_json) "
            "across sessions—unlike read_task_plan, which is bound to the current session task id."
        ),
        parameters_json_schema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "tasks.id for a task_kind=goal row.",
                },
            },
            "required": ["task_id"],
        },
    )


def _gsc_read_function_declaration() -> types.FunctionDeclaration:
    return types.FunctionDeclaration(
        name="get_gsc_opportunities",
        description=(
            "Read deterministic Google Search Console opportunity slices from local SQLite "
            "(top queries/pages, quick wins, content gaps, page fixes). "
            "Use for campaign planning before write_task_plan."
        ),
        parameters_json_schema={
            "type": "object",
            "properties": {
                "site": {
                    "type": "string",
                    "description": "GSC property_ref/site URL used during ingest.",
                },
                "start_date": {
                    "type": "string",
                    "description": "Inclusive YYYY-MM-DD lower bound.",
                },
                "end_date": {
                    "type": "string",
                    "description": "Inclusive YYYY-MM-DD upper bound.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Per-slice result cap (1..200).",
                },
            },
            "required": ["site", "start_date", "end_date"],
        },
    )


def _plan_function_declarations() -> list[types.FunctionDeclaration]:
    return [
        types.FunctionDeclaration(
            name="read_task_plan",
            description=(
                "Read tasks.plan_json from SQLite for this task/session id only. "
                "In interactive chat: optional scratchpad for long threads. "
                "In queued goal tasks (ada daemon): prefer calling early each worker turn "
                "to resume state—primary durable plan for multi-step work."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.FunctionDeclaration(
            name="write_task_plan",
            description=(
                "Replace tasks.plan_json for this task/session id. "
                "Must be a string of valid JSON (typically an object). "
                "Chat: optional whiteboard. Goal/daemon runs: update as steps complete or priorities change."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "plan_json": {
                        "type": "string",
                        "description": "Full JSON text to store (e.g. '{\"steps\":[]}').",
                    },
                },
                "required": ["plan_json"],
            },
        ),
    ]


def _web_function_declarations(
    *,
    include_web_search: bool,
    include_web_fetch: bool,
) -> list[types.FunctionDeclaration]:
    out: list[types.FunctionDeclaration] = []
    if include_web_search:
        out.append(
            types.FunctionDeclaration(
                name="web_search",
                description=(
                    "Search the public web via Serper and return organic results only "
                    "(title, url, snippet per hit). No full page body. Prefer this before "
                    "fetching full pages when snippets are enough."
                ),
                parameters_json_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Web search query.",
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Desired number of organic results; capped by the harness.",
                        },
                    },
                    "required": ["query"],
                },
            )
        )
    if include_web_fetch:
        out.append(
            types.FunctionDeclaration(
                name="fetch_url_text",
                description=(
                    "Fetch readable full text for HTTPS URLs (e.g. Jina Reader or direct fetch). "
                    "Use only when snippets are insufficient. Max URLs and response size are capped."
                ),
                parameters_json_schema={
                    "type": "object",
                    "properties": {
                        "urls": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "HTTPS URLs to retrieve as plain text; max per call enforced.",
                        },
                    },
                    "required": ["urls"],
                },
            )
        )
    return out


def _knowledge_function_declarations() -> list[types.FunctionDeclaration]:
    return [
        types.FunctionDeclaration(
            name="search_knowledge",
            description=(
                "Search the local knowledge base (ingested RSS items and other facts). "
                "Uses keyword search (OR of tokens, BM25-ranked) and optionally Gemini embeddings "
                "when ADA_KNOWLEDGE_EMBEDDINGS=1 (semantic/hybrid modes). "
                "Returns items with id, title, link (when present), and excerpt — cite by id. "
                "Call before claiming facts from memory when the topic may have stored evidence."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Short phrase or keywords (natural language ok; stopwords ignored).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max items to return (harness caps).",
                    },
                    "tag": {
                        "type": "string",
                        "description": "Optional: filter to items whose tags include this string.",
                    },
                    "ingested_after": {
                        "type": "string",
                        "description": "Optional ISO-like time lower bound for ingested_at.",
                    },
                    "ingested_before": {
                        "type": "string",
                        "description": "Optional ISO-like time upper bound for ingested_at.",
                    },
                    "prefer_fts": {
                        "type": "boolean",
                        "description": "Prefer FTS5 search; false uses substring fallback.",
                    },
                    "search_mode": {
                        "type": "string",
                        "description": "lexical (keywords only), semantic (vectors only, needs embeddings), "
                        "or hybrid (RRF merge; default when embeddings enabled).",
                        "enum": ["lexical", "semantic", "hybrid"],
                    },
                    "min_relevance_score": {
                        "type": "number",
                        "description": "Optional: only items with COALESCE(relevance_score,1.0) >= this (0–1).",
                    },
                    "valid_only": {
                        "type": "boolean",
                        "description": "If true (default), exclude tombstoned and expired items.",
                    },
                    "primary_triage_category": {
                        "type": "string",
                        "description": (
                            "Optional: filter to items whose triage primary category equals this "
                            "(e.g. markets_macro). Requires items to have been processed by ada triage."
                        ),
                    },
                },
                "required": ["query"],
            },
        ),
        types.FunctionDeclaration(
            name="get_entity_graph_context",
            description=(
                "Read-only: return a bounded JSON pack of the subject entity, its active outgoing "
                "graph_edges (newest first), destination entity summaries, and linked knowledge excerpts "
                "from edge_evidence (same shape as workflow EXISTING_SUBGRAPH grounding)."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "integer",
                        "description": "Subject entities.id (must match ENRICH subject when that harness is active).",
                    },
                },
                "required": ["entity_id"],
            },
        ),
        types.FunctionDeclaration(
            name="record_synthesis",
            description=(
                "Store a short synthesis or conclusion tied to knowledge item ids (citations). "
                "Use after search_knowledge when you consolidate evidence. "
                "ref_item_ids must list integer ids from search_knowledge results."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "body": {
                        "type": "string",
                        "description": "Synthesis text (Markdown ok).",
                    },
                    "ref_item_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Knowledge item ids this synthesis is grounded in.",
                    },
                    "task_id": {
                        "type": "integer",
                        "description": "Optional tasks.id; defaults to current session task when omitted.",
                    },
                },
                "required": ["body", "ref_item_ids"],
            },
        ),
        types.FunctionDeclaration(
            name="record_market_edge",
            description=(
                "Store a numeric market metric and link it to a knowledge item with causal notes. "
                "Use after search_knowledge when extracting concrete values (price, rate, index, etc.)."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "knowledge_id": {
                        "type": "integer",
                        "description": "knowledge_items.id to anchor this metric edge.",
                    },
                    "metric_name": {
                        "type": "string",
                        "description": "Short metric label, e.g. 'fuel_spend_march_nzd_m'.",
                    },
                    "metric_value": {
                        "type": "number",
                        "description": "Numeric value for the metric.",
                    },
                    "recorded_at": {
                        "type": "string",
                        "description": "Optional ISO-like timestamp for when metric applies.",
                    },
                    "api_source": {
                        "type": "string",
                        "description": "Optional source label/url for the metric row.",
                    },
                    "causality_notes": {
                        "type": "string",
                        "description": "Optional note describing why this metric links to the knowledge item.",
                    },
                },
                "required": ["knowledge_id", "metric_name", "metric_value"],
            },
        ),
        types.FunctionDeclaration(
            name="add_knowledge_source",
            description=(
                "Register a new RSS or web feed URL in SQLite (knowledge_sources). "
                "RSS feeds are fetched into knowledge_items by the operator job `ada ingest-rss` (e.g. cron). "
                "Only http(s) URLs; optional host allowlist from ADA_KNOWLEDGE_FEED_HOST_ALLOWLIST."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "description": "Source kind: 'rss', 'web', or 'brand' (bounded site truth ingest).",
                        "enum": ["rss", "web", "brand"],
                    },
                    "base_url": {
                        "type": "string",
                        "description": "Feed or site URL (https recommended).",
                    },
                    "label": {
                        "type": "string",
                        "description": "Optional human-readable label.",
                    },
                },
                "required": ["kind", "base_url"],
            },
        ),
        types.FunctionDeclaration(
            name="record_entity",
            description=(
                "Upsert a graph-lite entity by normalized name + type. "
                "Prefer types: organization, government_body, person, sector, instrument, "
                "policy_instrument, event, location, category (triage taxonomy parents)."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "aliases": {"type": "array", "items": {"type": "string"}},
                    "external_ids": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                    "payload": {"type": "object"},
                },
                "required": ["name", "type"],
            },
        ),
        types.FunctionDeclaration(
            name="record_edge",
            description=(
                "Create a graph-lite edge between two entities with confidence and evidence. "
                "Use lowercase snake edge_type (e.g. announces, funds, under_category, regulates). "
                "Non-hypothesis edges require evidence_item_ids and source_url: a canonical https URL "
                "for the page the fact came from (typically a fetched page or search result). "
                "Publishing GATE counts distinct source_url on active outgoing edges—use real, "
                "distinct URLs. Omit or set is_hypothesis true only for speculative edges (no source_url)."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "src_entity_id": {"type": "integer"},
                    "dst_entity_id": {"type": "integer"},
                    "edge_type": {"type": "string"},
                    "confidence": {"type": "number"},
                    "evidence_item_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                    },
                    "source_url": {
                        "type": "string",
                        "description": (
                            "Required for fact edges (is_hypothesis false or omitted): https URL "
                            "of the supporting web page."
                        ),
                    },
                    "status": {
                        "type": "string",
                        "enum": ["active", "superseded", "invalid"],
                    },
                    "is_hypothesis": {"type": "boolean"},
                    "superseded_by": {"type": "integer"},
                },
                "required": [
                    "src_entity_id",
                    "dst_entity_id",
                    "edge_type",
                    "confidence",
                    "evidence_item_ids",
                ],
            },
        ),
        types.FunctionDeclaration(
            name="link_evidence",
            description=(
                "Attach one knowledge item as evidence to an existing graph-lite edge."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "edge_id": {"type": "integer"},
                    "knowledge_id": {"type": "integer"},
                    "quote_span": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "integer"},
                            "end": {"type": "integer"},
                            "text": {"type": ["string", "null"]},
                        },
                        "required": ["start", "end"],
                    },
                },
                "required": ["edge_id", "knowledge_id"],
            },
        ),
    ]


def knowledge_function_declarations_subset(
    names: frozenset[str],
) -> list[types.FunctionDeclaration]:
    """Return knowledge tool declarations whose names are in ``names`` (sorted for stability)."""
    by_name = {d.name: d for d in _knowledge_function_declarations()}
    out: list[types.FunctionDeclaration] = []
    for n in sorted(names):
        d = by_name.get(n)
        if d is not None:
            out.append(d)
    return out


def frozen_tool_declaration_names(tool: types.Tool) -> frozenset[str]:
    decls: Sequence[types.FunctionDeclaration] = tool.function_declarations or []
    return frozenset(d.name for d in decls if getattr(d, "name", None))


def _workflow_status_declaration() -> types.FunctionDeclaration:
    """Read-only workflow status (H2: enqueue_workflow is not a chat tool)."""
    return types.FunctionDeclaration(
        name="get_workflow_status",
        description="Read-only: return workflow row and all workflow_steps for a workflow id.",
        parameters_json_schema={
            "type": "object",
            "properties": {
                "workflow_id": {"type": "integer", "description": "workflows.id"},
            },
            "required": ["workflow_id"],
        },
    )


def _list_session_web_sources_declaration() -> types.FunctionDeclaration:
    return types.FunctionDeclaration(
        name="list_session_web_sources",
        description=(
            "Read recent web_sources rows for the **current** task/session only (Phase B bounded logging). "
            "Read-only; no new HTTP or DB writes."
        ),
        parameters_json_schema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max rows to return (harness caps; default 50).",
                },
            },
            "required": [],
        },
    )


def build_shell_declarations(*, allowed_exact_commands: frozenset[str]) -> list[types.FunctionDeclaration]:
    if not allowed_exact_commands:
        return []
    preview = "\n".join(sorted(allowed_exact_commands)[:40])
    more = ""
    if len(allowed_exact_commands) > 40:
        more = f"\n... and {len(allowed_exact_commands) - 40} more (see shell_allowlist.txt)."
    return [
        types.FunctionDeclaration(
            name="run_allowlisted_shell",
            description=(
                "Execute one read-only shell probe. The `command` string must match "
                "EXACTLY (character-for-character after trim) one entry from the allowlist.\n"
                "Allowed commands:\n"
                f"{preview}{more}"
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Full allowlisted command line, e.g. `uname -a`.",
                    },
                },
                "required": ["command"],
            },
        )
    ]


def build_agent_tools(
    *,
    allowed_exact_commands: frozenset[str],
    include_memory_tools: bool,
    include_plan_tools: bool = False,
    include_goal_recall_tool: bool = False,
    include_gsc_read_tools: bool = False,
    include_file_tools: bool = False,
    include_web_search: bool = False,
    include_web_fetch: bool = False,
    include_list_session_web_sources: bool = False,
    include_knowledge_tools: bool = False,
    knowledge_tool_subset: frozenset[str] | None = None,
    include_workflow_tools: bool = False,
    include_mission_control_snapshot: bool = False,
    include_run_skill: bool = False,
    include_propose_programme: bool = False,
    include_apply_programme: bool = False,
) -> types.Tool:
    decls: list[types.FunctionDeclaration] = [_check_token_usage_declaration()]
    if include_mission_control_snapshot:
        decls.append(_mission_control_snapshot_declaration())
    if include_run_skill:
        decls.append(_run_skill_declaration())
    if include_propose_programme:
        decls.append(_propose_programme_declaration())
    if include_apply_programme:
        decls.append(_apply_programme_declaration())
    decls.extend(build_shell_declarations(allowed_exact_commands=allowed_exact_commands))
    if include_memory_tools:
        decls.extend(_memory_function_declarations())
    if include_plan_tools:
        decls.extend(_plan_function_declarations())
    if include_goal_recall_tool:
        decls.append(_goal_recall_function_declaration())
    if include_gsc_read_tools:
        decls.append(_gsc_read_function_declaration())
    if include_file_tools:
        decls.extend(_file_function_declarations())
    decls.extend(
        _web_function_declarations(
            include_web_search=include_web_search,
            include_web_fetch=include_web_fetch,
        )
    )
    if include_list_session_web_sources:
        decls.append(_list_session_web_sources_declaration())
    if knowledge_tool_subset is not None:
        decls.extend(knowledge_function_declarations_subset(knowledge_tool_subset))
    elif include_knowledge_tools:
        decls.extend(_knowledge_function_declarations())
    if include_workflow_tools:
        decls.append(_workflow_status_declaration())
    return types.Tool(function_declarations=decls)


def build_shell_tool(*, allowed_exact_commands: frozenset[str]) -> types.Tool:
    """Shell allowlist plus check_token_usage (always present)."""
    return build_agent_tools(
        allowed_exact_commands=allowed_exact_commands,
        include_memory_tools=False,
        include_plan_tools=False,
        include_file_tools=False,
    )
