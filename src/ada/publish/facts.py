"""Fact counting for the GATE (publish) step — single normative rule for tests and runner."""

from __future__ import annotations

from ada.query_engine import QueryEngine


async def count_unique_local_facts(qe: QueryEngine, entity_id: int) -> int:
    """
    `unique_local_facts` for `workflows` / GATE:

    The count is the number of **distinct non-empty** `source_url` values on
    **active** outgoing `graph_edges` for `src_entity_id == entity_id`.

    Same semantics as `PersistentState.count_unique_local_facts` (see SQL there).
    """
    return await qe.count_unique_local_facts(int(entity_id))
