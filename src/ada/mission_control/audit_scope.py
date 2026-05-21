"""Read-only mission scope audit (legacy NULL rows vs mission-owned entities)."""

from __future__ import annotations

import sqlite3
from typing import Any

from ada.observability.queries import _column_exists, _table_exists


def audit_mission_scope(
    conn: sqlite3.Connection,
    *,
    mission_id: int,
    mission_slug: str,
) -> dict[str, Any]:
    """
    Count graph/knowledge rows that may be visible to this mission but lack mission_id.

  Legacy NULL mission_id rows are intentionally allowed in subgraph packs; this report
  helps operators plan backfill — it does not mutate data.

  Ops-only CLI: ``ada mission audit-scope <slug>`` — not exposed as a chat tool.
  See docs/GRAPH_MISSION_SCOPE.md.
    """
    report: dict[str, Any] = {
        "mission_id": mission_id,
        "mission_slug": mission_slug,
        "graph_edges_null_mission_touching_entities": 0,
        "knowledge_sources_null_mission": 0,
        "entities_in_mission": 0,
    }
    if not _table_exists(conn, "entities"):
        return report
    cur = conn.execute(
        "SELECT COUNT(*) AS n FROM entities WHERE mission_id = ?", (mission_id,)
    )
    row = cur.fetchone()
    report["entities_in_mission"] = int(row[0] or 0) if row else 0

    if _table_exists(conn, "graph_edges") and _column_exists(conn, "graph_edges", "mission_id"):
        cur = conn.execute(
            """
            SELECT COUNT(*) AS n FROM graph_edges ge
            WHERE ge.mission_id IS NULL
              AND (
                ge.src_entity_id IN (SELECT id FROM entities WHERE mission_id = ?)
                OR ge.dst_entity_id IN (SELECT id FROM entities WHERE mission_id = ?)
              )
            """,
            (mission_id, mission_id),
        )
        row = cur.fetchone()
        report["graph_edges_null_mission_touching_entities"] = int(row[0] or 0) if row else 0

    if _table_exists(conn, "knowledge_sources") and _column_exists(
        conn, "knowledge_sources", "mission_id"
    ):
        cur = conn.execute(
            "SELECT COUNT(*) AS n FROM knowledge_sources WHERE mission_id IS NULL"
        )
        row = cur.fetchone()
        report["knowledge_sources_null_mission"] = int(row[0] or 0) if row else 0
        cur = conn.execute(
            "SELECT COUNT(*) AS n FROM knowledge_sources WHERE mission_id = ?",
            (mission_id,),
        )
        row = cur.fetchone()
        report["knowledge_sources_in_mission"] = int(row[0] or 0) if row else 0

    report["note"] = (
        "NULL mission_id graph edges may still appear in mission-scoped subgraph packs "
        "(legacy migration). Global knowledge_sources (NULL) are shared profile feeds."
    )
    return report
