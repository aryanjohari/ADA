"""Gemini `Tool` declarations — single source with executor (claude_logic §12)."""

from __future__ import annotations

from google.genai import types


def build_shell_tool(*, allowed_exact_commands: frozenset[str]) -> types.Tool | None:
    if not allowed_exact_commands:
        return None
    preview = "\n".join(sorted(allowed_exact_commands)[:40])
    more = ""
    if len(allowed_exact_commands) > 40:
        more = f"\n... and {len(allowed_exact_commands) - 40} more (see shell_allowlist.txt)."

    return types.Tool(
        function_declarations=[
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
    )
