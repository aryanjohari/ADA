"""graph_edges mission_id: reject cross-mission edges; mission_scope filters pack."""

from __future__ import annotations

import pytest

from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_insert_graph_edge_rejects_cross_mission_entities(
    tmp_path, schema_sql_path
) -> None:
    db = tmp_path / "ge_mission.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        m1 = await qe.create_mission(slug="a", title="A")
        m2 = await qe.create_mission(slug="b", title="B")
        ea = await qe.upsert_entity(
            type="service", name="S1", mission_id=m1, payload_json={}
        )
        eb = await qe.upsert_entity(
            type="service", name="S2", mission_id=m2, payload_json={}
        )
        aid, bid = int(ea["entity_id"]), int(eb["entity_id"])
        with pytest.raises(ValueError, match="mission_id"):
            await qe.insert_graph_edge(
                src_entity_id=aid,
                dst_entity_id=bid,
                edge_type="ref",
                confidence=0.5,
            )
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_load_subject_subgraph_mission_scope_filters_edges(
    tmp_path, schema_sql_path
) -> None:
    db = tmp_path / "ge_scope.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        m1 = await qe.create_mission(slug="m1", title="M1")
        m2 = await qe.create_mission(slug="m2", title="M2")
        a = await qe.upsert_entity(
            type="service", name="Subj", mission_id=m1, payload_json={}
        )
        b = await qe.upsert_entity(
            type="regulation", name="R1", mission_id=m1, payload_json={}
        )
        aid, bid = int(a["entity_id"]), int(b["entity_id"])
        e_m1 = await qe.insert_graph_edge(
            src_entity_id=aid,
            dst_entity_id=bid,
            edge_type="ref",
            confidence=0.9,
        )
        assert e_m1 >= 1

        pack_default = await qe.load_subject_subgraph_context_pack(aid, max_edges=10)
        assert len(pack_default["outgoing_edges"]) == 1
        assert pack_default["outgoing_edges"][0]["id"] == e_m1

        pack_m1 = await qe.load_subject_subgraph_context_pack(
            aid, max_edges=10, mission_scope=m1
        )
        assert len(pack_m1["outgoing_edges"]) == 1

        pack_m2 = await qe.load_subject_subgraph_context_pack(
            aid, max_edges=10, mission_scope=m2
        )
        assert pack_m2["outgoing_edges"] == []
    finally:
        await qe.close()
