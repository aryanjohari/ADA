"""Gemini `Tool` declarations — shell + optional memory append tools."""

from __future__ import annotations

from google.genai import types


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
    include_file_tools: bool = False,
    include_web_search: bool = False,
    include_web_fetch: bool = False,
    include_list_session_web_sources: bool = False,
) -> types.Tool:
    decls: list[types.FunctionDeclaration] = [_check_token_usage_declaration()]
    decls.extend(build_shell_declarations(allowed_exact_commands=allowed_exact_commands))
    if include_memory_tools:
        decls.extend(_memory_function_declarations())
    if include_plan_tools:
        decls.extend(_plan_function_declarations())
    if include_goal_recall_tool:
        decls.append(_goal_recall_function_declaration())
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
    return types.Tool(function_declarations=decls)


def build_shell_tool(*, allowed_exact_commands: frozenset[str]) -> types.Tool:
    """Shell allowlist plus check_token_usage (always present)."""
    return build_agent_tools(
        allowed_exact_commands=allowed_exact_commands,
        include_memory_tools=False,
        include_plan_tools=False,
        include_file_tools=False,
    )
