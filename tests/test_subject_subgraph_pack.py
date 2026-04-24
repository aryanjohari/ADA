"""Subject subgraph context pack for ENRICH."""

from __future__ import annotations

import pytest

from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_load_subject_subgraph_context_pack_shape(tmp_path, schema_sql_path):
    db = tmp_path / "sg.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        a = await qe.upsert_entity(type="service", name="Subject S", payload_json={"k": 1})
        b = await qe.upsert_entity(type="regulation", name="Rule R", payload_json={})
        aid, bid = int(a["entity_id"]), int(b["entity_id"])
        sid = await qe.insert_knowledge_source("rss", label="L", base_url="https://src.test/f")
        ins = await qe.insert_knowledge_item(
            sid, "hx", content_excerpt="Evidence excerpt text here.", tags=[]
        )
        kid = int(ins.id)
        eid = await qe.insert_graph_edge(
            src_entity_id=aid,
            dst_entity_id=bid,
            edge_type="ref",
            confidence=0.9,
            source_url="https://src.test/page",
        )
        await qe.link_edge_evidence_upsert(edge_id=eid, knowledge_id=kid)

        pack = await qe.load_subject_subgraph_context_pack(
            aid, max_edges=5, max_excerpt_items=5, excerpt_max_chars=200
        )
        assert pack["subject"] and pack["subject"]["id"] == aid
        assert len(pack["outgoing_edges"]) == 1
        e0 = pack["outgoing_edges"][0]
        assert e0["id"] == eid
        assert e0["dst_entity_id"] == bid
        assert e0["dst"]["name"] == "Rule R"
        assert len(pack["linked_knowledge_excerpts"]) == 1
        ex0 = pack["linked_knowledge_excerpts"][0]
        assert ex0["knowledge_id"] == kid
        assert ex0["edge_id"] == eid
        assert "Evidence excerpt" in ex0["content_excerpt"]

        assert await qe.max_graph_edge_id_for_src_entity(aid) == eid
        tid = await qe.insert_task("t", status="pending")
        u = await qe.persist_user(tid, "hi")
        assert await qe.max_message_sequence(tid) >= 1
        await qe.persist_assistant_begin(tid, u)
        assert await qe.max_message_sequence(tid) >= 2
    finally:
        await qe.close()
