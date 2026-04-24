"""Store / DRAFT: enrichment excerpts for grounding."""

from __future__ import annotations

import pytest

from ada.publish.draft import _format_grounding_pack
from ada.query_engine import QueryEngine


def test_format_grounding_pack_empty():
    assert _format_grounding_pack([]) == ""


def test_format_grounding_pack_includes_urls():
    s = _format_grounding_pack(
        [{"source_url": "https://a.test/x", "content_excerpt": "Hello world"}]
    )
    assert "Grounding excerpts" in s
    assert "https://a.test/x" in s
    assert "Hello world" in s


@pytest.mark.asyncio
async def test_list_enrichment_excerpts_for_entity(tmp_path, schema_sql_path):
    db = tmp_path / "ex.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        a = await qe.upsert_entity(type="service", name="S", payload_json={})
        b = await qe.upsert_entity(type="regulation", name="R", payload_json={})
        aid, bid = int(a["entity_id"]), int(b["entity_id"])
        sid = await qe.insert_knowledge_source("rss", label="L", base_url="https://src.test/f")
        ins = await qe.insert_knowledge_item(
            sid, "hx", content_excerpt="Body of knowledge for page.", tags=[]
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
        rows = await qe.list_enrichment_excerpts_for_entity(aid, limit=5)
        assert len(rows) == 1
        assert rows[0]["knowledge_id"] == kid
        assert "Body of knowledge" in rows[0]["content_excerpt"]
        assert rows[0]["source_url"] == "https://src.test/page"
    finally:
        await qe.close()
