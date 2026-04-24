"""count_unique_local_facts (distinct source_url) — graph-backed."""

from __future__ import annotations

import pytest

from ada.query_engine import QueryEngine
from ada.publish.facts import count_unique_local_facts


@pytest.mark.asyncio
async def test_count_distinct_source_urls_parametrize(tmp_path, schema_sql_path):
    db = tmp_path / "f.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        a = await qe.upsert_entity(
            type="service", name="Alpha Corp", payload_json={}
        )
        b = await qe.upsert_entity(type="regulation", name="r1", payload_json={})
        e1 = int(a["entity_id"])
        b1 = int(b["entity_id"])
        assert await count_unique_local_facts(qe, e1) == 0

        for i, url in enumerate(
            [
                "https://a.test/1",
                "https://a.test/2",
                "https://a.test/1",
            ]
        ):
            await qe.insert_graph_edge(
                src_entity_id=e1,
                dst_entity_id=b1,
                edge_type="cites",
                confidence=0.9,
                source_url=url,
            )
        assert await count_unique_local_facts(qe, e1) == 2
        await qe.insert_graph_edge(
            src_entity_id=e1,
            dst_entity_id=b1,
            edge_type="cites",
            confidence=0.9,
            source_url="https://a.test/3",
        )
        assert await count_unique_local_facts(qe, e1) == 3
        assert await qe.count_outgoing_active_edges(e1) == 4
    finally:
        await qe.close()
