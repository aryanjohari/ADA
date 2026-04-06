"""Gemini `Tool` declarations — shell + optional memory append tools."""

from __future__ import annotations

from google.genai import types


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


def _plan_function_declarations() -> list[types.FunctionDeclaration]:
    return [
        types.FunctionDeclaration(
            name="read_task_plan",
            description=(
                "Read the current task's plan_json from SQLite (session clipboard). "
                "Returns the stored JSON text for the active session only."
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
                "Replace the current task's plan_json in SQLite. "
                "Argument must be a string containing valid JSON (typically a JSON object)."
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
) -> types.Tool | None:
    decls: list[types.FunctionDeclaration] = []
    decls.extend(build_shell_declarations(allowed_exact_commands=allowed_exact_commands))
    if include_memory_tools:
        decls.extend(_memory_function_declarations())
    if include_plan_tools:
        decls.extend(_plan_function_declarations())
    if not decls:
        return None
    return types.Tool(function_declarations=decls)


def build_shell_tool(*, allowed_exact_commands: frozenset[str]) -> types.Tool | None:
    """Backward-compatible: shell-only tool."""
    return build_agent_tools(
        allowed_exact_commands=allowed_exact_commands,
        include_memory_tools=False,
        include_plan_tools=False,
    )
