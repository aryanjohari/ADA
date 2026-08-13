"""Gemini FunctionDeclaration schemas — not raw AFC callables (M02/M04)."""

from __future__ import annotations

from typing import Any

TOOL_NAMES = frozenset(
    {
        "body_vitals",
        "body_whoami",
        "body_story",
        "body_doctor",
        "memory_facts_get",
        "memory_facts_search",
        "memory_facts_append",
        "memory_facts_propose_edit",
        "memory_open_loops_list",
        "memory_open_loops_upsert",
        "memory_worldview_search",
        "memory_worldview_write",
        "dream_status",
    }
)

# Write tools — denied in Observe/Plan; allowed in Agent.
WRITE_TOOL_NAMES = frozenset(
    {
        "fact_append",  # stub name kept for legacy mode tests
        "memory_facts_append",
        "memory_facts_propose_edit",
        "memory_open_loops_upsert",
        "memory_worldview_write",
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
        {
            "name": "memory_facts_get",
            "description": (
                "Get a FACT by key (e.g. prefs.brief_time) or doc name (prefs). "
                "FACTS are dry standing truth — not WORLDVIEW digests."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Dotted key or doc name",
                    }
                },
                "required": ["key"],
            },
        },
        {
            "name": "memory_facts_search",
            "description": (
                "Search FACTS by key lookup + grep across facts/*.yaml. No embeddings."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_hits": {"type": "integer"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "memory_facts_append",
            "description": (
                "Append/set a FACT (Agent mode). Use prefs.brief_time etc. "
                "Overwrite of existing different value returns needs_confirm."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "e.g. prefs.brief_time",
                    },
                    "value": {
                        "description": "Value to store (string/bool/number)",
                    },
                    "note": {"type": "string"},
                },
                "required": ["key", "value"],
            },
        },
        {
            "name": "memory_facts_propose_edit",
            "description": (
                "Propose FACT overwrite. Without confirmed=true returns needs_confirm."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "value": {},
                    "confirmed": {"type": "boolean"},
                },
                "required": ["key", "value"],
            },
        },
        {
            "name": "memory_open_loops_list",
            "description": (
                "List open loops / campaigns (projects, TODOs, long-horizon STATUS). "
                "Filter by status and kind (todo|campaign)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": (
                            "Filter status (default open for todos). "
                            "Campaigns use active|blocked|waiting_on_aryan|paused|done|failed."
                        ),
                    },
                    "kind": {
                        "type": "string",
                        "description": "todo | campaign (omit for both)",
                    },
                    "limit": {"type": "integer"},
                },
            },
        },
        {
            "name": "memory_open_loops_upsert",
            "description": (
                "Create/update a todo or campaign (Agent). "
                "Delete and gated stage/campaign done require confirmed=true "
                "(or last_receipt for gated completion)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "id": {"type": "string"},
                    "status": {"type": "string"},
                    "kind": {
                        "type": "string",
                        "description": "todo (default) | campaign",
                    },
                    "title": {"type": "string"},
                    "stages": {
                        "type": "array",
                        "description": (
                            "Campaign stages: [{id, state, gate?}]. "
                            "state=pending|active|done|skipped; gate=confirm for side effects."
                        ),
                        "items": {"type": "object"},
                    },
                    "current_stage": {"type": "string"},
                    "blocked_reason": {"type": "string"},
                    "next_wake_at": {
                        "type": "string",
                        "description": "ISO8601 wake time",
                    },
                    "last_progress_at": {"type": "string"},
                    "last_receipt": {
                        "type": "string",
                        "description": "runs/ receipt pointer for claimed progress",
                    },
                    "cadence": {
                        "type": "string",
                        "description": "on_open_only | daily",
                    },
                    "nudge_attribution": {"type": "object"},
                    "delete": {"type": "boolean"},
                    "confirmed": {"type": "boolean"},
                },
            },
        },
        {
            "name": "memory_worldview_search",
            "description": (
                "Search WORLDVIEW digests (interpretive). Digests ≠ metal FACTS."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_hits": {"type": "integer"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "memory_worldview_write",
            "description": (
                "Write a WORLDVIEW digest (Agent). cites[] required and non-empty. "
                "Never overwrites FACTS."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "body": {"type": "string"},
                    "cites": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "FACT keys and/or run/lifecycle receipts",
                    },
                    "title": {"type": "string"},
                },
                "required": ["body", "cites"],
            },
        },
        {
            "name": "dream_status",
            "description": (
                "Last dream_ok/fail, outbox pending, staging count. "
                "Dream runs primarily via `ada dream run`, not chat."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    ]
