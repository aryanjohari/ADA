"""Gemini FunctionDeclaration schemas — not raw AFC callables (M02 §5.1)."""

from __future__ import annotations

from typing import Any

TOOL_NAMES = frozenset(
    {
        "body_vitals",
        "body_whoami",
        "body_story",
        "body_doctor",
    }
)

# Future write tools — denied in Observe when registered later.
WRITE_TOOL_NAMES = frozenset(
    {
        "fact_append",  # stub name for mode tests only
    }
)


def function_declarations() -> list[dict[str, Any]]:
    """Return JSON-serializable function declaration dicts for the adapter."""
    return [
        {
            "name": "body_vitals",
            "description": (
                "Read host vitals from body organs (temp, disks, mounts, memory). "
                "Use section=summary for a compact view, full for complete snapshot."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "enum": ["summary", "full"],
                        "description": "summary (default) or full VitalsSnapshot",
                    }
                },
            },
        },
        {
            "name": "body_whoami",
            "description": (
                "Load identity.yaml birth card (name, born_at, host). "
                "born_at is sacred and read-only."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "body_story",
            "description": (
                "Autobiography from the lifecycle ledger only — last N events as sentences."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "n": {
                        "type": "integer",
                        "description": "Number of recent ledger events (default 20)",
                    }
                },
            },
        },
        {
            "name": "body_doctor",
            "description": (
                "Mount honesty + probe_errors + urgent fault flags "
                "(same spirit as `ada body doctor`)."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    ]
