"""Valid workflow child step_type values (DB CHECK + application validation)."""

from __future__ import annotations

# Keep in lockstep with workflow_steps step_type CHECK in schema.sql and migrations.
WORKFLOW_VALID_STEP_TYPES: frozenset[str] = frozenset(
    {
        "FETCH",
        "EXTRACT",
        "SYNTHESIZE",
        "ENRICH",
        "GATE",
        "DRAFT",
        "DEPLOY",
    }
)

# Live ENRICH: knowledge tools passed as knowledge_tool_subset (web_search / fetch_url_text
# are enabled separately via WebToolConfig on orchestrate_turn).
KNOWLEDGE_TOOLS_ENRICH: frozenset[str] = frozenset(
    {
        "search_knowledge",
        "get_entity_graph_context",
        "record_entity",
        "record_edge",
        "link_evidence",
    }
)

# Full strict tool-name set for ENRICH (check_token_usage + these; shell empty in runner).
ENRICH_STRICT_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "check_token_usage",
        "web_search",
        "fetch_url_text",
        "search_knowledge",
        "get_entity_graph_context",
        "record_entity",
        "record_edge",
        "link_evidence",
    }
)
