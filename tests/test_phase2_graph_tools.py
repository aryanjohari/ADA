from __future__ import annotations

import pytest

from ada.stream_types import CompletedFunctionCall
from ada.tool_executor import StreamingToolExecutor


@pytest.mark.asyncio
async def test_graph_tool_dispatch_record_entity():
    async def _record_entity(call: CompletedFunctionCall) -> dict[str, object]:
        assert call.name == "record_entity"
        return {"entity_id": 11, "inserted": True, "normalized_name": "acme"}

    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=1.0,
        knowledge_record_entity=_record_entity,
    )
    out = await ex.run_ordered(
        [
            CompletedFunctionCall(
                name="record_entity",
                args={"name": "Acme", "type": "company"},
                id="t1",
            )
        ]
    )
    assert out[0].response["entity_id"] == 11


@pytest.mark.asyncio
async def test_graph_tool_dispatch_record_edge_and_link():
    async def _record_edge(_call: CompletedFunctionCall) -> dict[str, object]:
        return {"edge_id": 7, "status": "active", "evidence_linked": 2}

    async def _link_evidence(_call: CompletedFunctionCall) -> dict[str, object]:
        return {"edge_evidence_id": 3, "upserted": True}

    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=1.0,
        knowledge_record_edge=_record_edge,
        knowledge_link_evidence=_link_evidence,
    )
    out = await ex.run_ordered(
        [
            CompletedFunctionCall(
                name="record_edge",
                args={
                    "src_entity_id": 1,
                    "dst_entity_id": 2,
                    "edge_type": "supplies",
                    "confidence": 0.8,
                    "evidence_item_ids": [10, 11],
                },
                id="t2",
            ),
            CompletedFunctionCall(
                name="link_evidence",
                args={"edge_id": 7, "knowledge_id": 12},
                id="t3",
            ),
        ]
    )
    assert out[0].response["edge_id"] == 7
    assert out[1].response["edge_evidence_id"] == 3

