"""DRAFT: knowledge_items retrieval merged into prompt (mocked search, offline)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest

from ada.config import Settings
from ada.query_engine import QueryEngine
from ada.publish.draft import (
    _draft_graph_anchored_query,
    _static_curated_hero_url,
    load_draft_knowledge_for_prompt,
    run_publish_draft,
)


def test_draft_graph_anchored_query_includes_edges():
    pack = {
        "subject": {"id": 1, "name": "Acme", "type": "service"},
        "outgoing_edges": [
            {
                "edge_type": "regulated_by",
                "dst": {"name": "SEC", "type": "jurisdiction"},
            }
        ],
    }
    q = _draft_graph_anchored_query(pack, {"niche": "fintech", "entity_id": 1}, pack["subject"])
    assert "Acme" in q or "fintech" in q
    assert "regulated" in q.lower() or "SEC" in q


@pytest.mark.asyncio
async def test_load_draft_knowledge_merges_search_chunks_deduped(tmp_path, schema_sql_path, monkeypatch):
    monkeypatch.setenv("ADA_PUBLISH_DRAFT_KNOWLEDGE_RETRIEVAL", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    db = tmp_path / "dk.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        ent = await qe.upsert_entity(type="service", name="S1", payload_json={})
        eid = int(ent["entity_id"])
        edge_ex = [
            {
                "knowledge_id": 10,
                "content_excerpt": "from graph edge A",
                "source_url": "https://e.test/a",
            }
        ]
        settings = Settings.load()
        assert settings.publish_draft_knowledge_retrieval is True

        async def fake_search(
            *args: object, **kwargs: object
        ) -> list[dict[str, object]]:
            return [
                {
                    "id": 10,
                    "content_excerpt": "from graph edge A",
                    "source_id": 1,
                    "external_id": None,
                    "payload": {"link": "https://e.test/a"},
                },
                {
                    "id": 20,
                    "content_excerpt": "unique corpus chunk about S1",
                    "source_id": 1,
                    "external_id": None,
                    "payload": None,
                },
            ]

        with mock.patch.object(qe, "search_knowledge_items", new=fake_search):
            block, items = await load_draft_knowledge_for_prompt(
                qe,
                settings,
                {"entity_id": eid, "niche": "x"},
                await qe.get_entity_by_id(eid) or {},
                edge_excerpts=edge_ex,
            )
        assert "knowledge_id=10" not in block
        assert "unique corpus chunk" in block
        assert len(items) == 1
        assert items[0].get("id") == 20
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_draft_user_prompt_includes_edge_and_knowledge_blocks(
    tmp_path, schema_sql_path, monkeypatch
):
    monkeypatch.setenv("ADA_PUBLISH_DRAFT_KNOWLEDGE_RETRIEVAL", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    db = tmp_path / "d2.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        src = await qe.insert_knowledge_source("rss", label="L", base_url="https://f.test/f")
        kin = await qe.insert_knowledge_item(
            int(src), "h1", content_excerpt="evidence body for edge", tags=[]
        )
        subj = await qe.upsert_entity(type="service", name="S2", payload_json={})
        dst = await qe.upsert_entity(type="org", name="D", payload_json={})
        eid = int(subj["entity_id"])
        did = int(dst["entity_id"])
        ege = await qe.insert_graph_edge(
            src_entity_id=eid,
            dst_entity_id=did,
            edge_type="cites",
            confidence=0.8,
            source_url="https://src.test/p",
        )
        await qe.insert_edge_evidence(
            edge_id=int(ege), knowledge_id=int(kin.id), span_json={}
        )
        captured: dict[str, str] = {}

        fixture = Path(__file__).resolve().parent / "fixtures" / "pseo_page.json"
        page_json = json.loads(fixture.read_text(encoding="utf-8"))

        async def fake_search(
            *args: object, **kwargs: object
        ) -> list[dict[str, object]]:
            return [
                {
                    "id": 99,
                    "content_excerpt": "extra RAG line not on edges",
                    "source_id": 1,
                    "external_id": None,
                    "payload": {"link": "https://kb.test/99"},
                }
            ]

        async def capture_gc(*args: object, **kwargs: object) -> object:
            contents = kwargs.get("contents")
            cfg = kwargs.get("config")
            if contents and len(contents) > 0 and hasattr(contents[0], "parts"):
                captured["user"] = contents[0].parts[0].text
            if cfg is not None and hasattr(cfg, "system_instruction"):
                captured["sys"] = str(cfg.system_instruction)
            m = mock.MagicMock()
            m.text = json.dumps(page_json)
            return m

        with mock.patch.object(qe, "search_knowledge_items", new=fake_search):
            with mock.patch("ada.publish.draft.genai.Client") as client_cls:
                inst = client_cls.return_value
                inst.aio.models.generate_content = mock.AsyncMock(side_effect=capture_gc)
                out = await run_publish_draft(
                    qe,
                    Settings.load(),
                    goal_text="g",
                    params={"entity_id": eid},
                )
        u = captured.get("user", "")
        sys_text = captured.get("sys") or ""
        assert "Subject subgraph" in u
        assert "outgoing_edges" in u
        assert "Grounding excerpts" in u
        assert "Map facts you draw" in u
        assert "evidence body for edge" in u
        assert "knowledge (knowledge_items search" in u
        assert "extra RAG line" in u
        assert "800+" in sys_text
        assert "SEO" in u
        assert "inline HTML link" in sys_text
        assert "source_url" in sys_text
        assert "Citations" in u
        page = out.get("page") or {}
        og = page.get("og_image", "")
        assert og.startswith("https://images.unsplash.com/photo-")
        assert "<img " in str(page.get("content") or "")
    finally:
        await qe.close()


def test_default_og_image_url_deterministic():
    a = _static_curated_hero_url({"niche": "dairy", "page_type": "guide"}, {"type": "farm"})
    b = _static_curated_hero_url({"niche": "dairy", "page_type": "guide"}, {"type": "farm"})
    assert a == b
    assert a.startswith("https://images.unsplash.com/photo-")
    c = _static_curated_hero_url(
        {"niche": "a-niche-unique-xyz", "page_type": ""}, {"type": "other-type"}
    )
    assert a != c


@pytest.mark.asyncio
async def test_draft_hero_uses_unsplash_api_when_key_set(
    tmp_path, schema_sql_path, monkeypatch
):
    monkeypatch.setenv("ADA_UNSPLASH_ACCESS_KEY", "test-unsplash-key")
    monkeypatch.setenv("ADA_PUBLISH_DRAFT_KNOWLEDGE_RETRIEVAL", "0")
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    db = tmp_path / "dus.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        subj = await qe.upsert_entity(type="service", name="E3", payload_json={})
        eid = int(subj["entity_id"])
        fixture = Path(__file__).resolve().parent / "fixtures" / "pseo_page.json"
        page_json = json.loads(fixture.read_text(encoding="utf-8"))
        assert page_json.get("og_image") is None

        fake_http = mock.MagicMock()
        fake_resp = mock.MagicMock()
        fake_resp.raise_for_status = mock.Mock()
        fake_resp.json = mock.Mock(
            return_value={"urls": {"raw": "https://images.unsplash.com/photo-abc-xyz-123"}}
        )
        fake_http.get = mock.AsyncMock(return_value=fake_resp)
        fake_http.__aenter__ = mock.AsyncMock(return_value=fake_http)
        fake_http.__aexit__ = mock.AsyncMock(return_value=None)

        async def capture_gc(*args: object, **kwargs: object) -> object:
            m = mock.MagicMock()
            m.text = json.dumps(page_json)
            return m

        with (
            mock.patch("ada.publish.draft.httpx.AsyncClient", return_value=fake_http),
            mock.patch("ada.publish.draft.genai.Client") as client_cls,
        ):
            ginst = client_cls.return_value
            ginst.aio.models.generate_content = mock.AsyncMock(side_effect=capture_gc)
            out = await run_publish_draft(
                qe,
                Settings.load(),
                goal_text="g",
                params={"entity_id": eid, "niche": "fintech", "category": "safety"},
            )
        call_kwargs = fake_http.get.await_args.kwargs
        assert (call_kwargs.get("params") or {}).get("query") == "safety"
        d = out.get("page") or {}
        assert d.get("og_image", "").startswith("https://images.unsplash.com/photo-abc-xyz-123")
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_draft_og_image_env_override(
    tmp_path, schema_sql_path, monkeypatch
):
    monkeypatch.setenv("ADA_PUBLISH_DRAFT_OG_IMAGE_DEFAULT", "https://operator.example/og.png")
    monkeypatch.setenv("ADA_PUBLISH_DRAFT_KNOWLEDGE_RETRIEVAL", "0")
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    db = tmp_path / "d3.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        subj = await qe.upsert_entity(type="service", name="E", payload_json={})
        eid = int(subj["entity_id"])
        fixture = Path(__file__).resolve().parent / "fixtures" / "pseo_page.json"
        page_json = json.loads(fixture.read_text(encoding="utf-8"))
        assert page_json.get("og_image") is None

        async def capture_gc(*args: object, **kwargs: object) -> object:
            m = mock.MagicMock()
            m.text = json.dumps(page_json)
            return m

        with mock.patch("ada.publish.draft.genai.Client") as client_cls:
            inst = client_cls.return_value
            inst.aio.models.generate_content = mock.AsyncMock(side_effect=capture_gc)
            out = await run_publish_draft(
                qe,
                Settings.load(),
                goal_text="g",
                params={"entity_id": eid, "project_id": "p", "campaign_id": "c", "niche": "n"},
            )
        p = out.get("page") or {}
        assert p.get("og_image") == "https://operator.example/og.png"
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_draft_og_image_preserves_model_value(
    tmp_path, schema_sql_path, monkeypatch
):
    monkeypatch.setenv("ADA_PUBLISH_DRAFT_KNOWLEDGE_RETRIEVAL", "0")
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    db = tmp_path / "d4.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        subj = await qe.upsert_entity(type="service", name="E2", payload_json={})
        eid = int(subj["entity_id"])
        fixture = Path(__file__).resolve().parent / "fixtures" / "pseo_page.json"
        page_json = json.loads(fixture.read_text(encoding="utf-8"))
        page_json["og_image"] = "https://from-model.example/hero.jpg"

        async def capture_gc(*args: object, **kwargs: object) -> object:
            m = mock.MagicMock()
            m.text = json.dumps(page_json)
            return m

        with mock.patch("ada.publish.draft.genai.Client") as client_cls:
            inst = client_cls.return_value
            inst.aio.models.generate_content = mock.AsyncMock(side_effect=capture_gc)
            out = await run_publish_draft(
                qe,
                Settings.load(),
                goal_text="g",
                params={"entity_id": eid},
            )
        p2 = out.get("page") or {}
        assert p2.get("og_image") == "https://from-model.example/hero.jpg"
    finally:
        await qe.close()
