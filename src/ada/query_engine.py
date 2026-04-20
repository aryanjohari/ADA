"""QueryEngine — transcript debounce + delegates persistence to PersistentState."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ada.persistent.store import (
    TASK_KIND_CHAT,
    TASK_KIND_GOAL,
    KnowledgeItemInsertResult,
    KnowledgeKind,
    PersistentState,
    TaskKind,
)
from ada.transcript_format import (
    ROLE_ASSISTANT,
    ROLE_SYSTEM,
    ROLE_TOOL,
    ROLE_USER,
)

# Backward-compatible re-exports for tests / adapters
__all__ = [
    "QueryEngine",
    "KnowledgeItemInsertResult",
    "KnowledgeKind",
    "ROLE_ASSISTANT",
    "ROLE_SYSTEM",
    "ROLE_TOOL",
    "ROLE_USER",
    "TASK_KIND_CHAT",
    "TASK_KIND_GOAL",
    "TaskKind",
]


@dataclass
class QueryEngine:
    """
    Facade: streaming debounce for assistant text + PersistentState for SQLite.
    Single writer to the DB for conversation turns (claude_logic §2.2).
    """

    db_path: Path
    schema_path: Path
    debounce_ms: int = 100

    _ps: PersistentState | None = field(default=None, repr=False)
    _debounce_tasks: dict[str, asyncio.Task[None]] = field(
        default_factory=dict, repr=False
    )

    @property
    def _store(self) -> PersistentState:
        if self._ps is None:
            raise RuntimeError("QueryEngine not connected")
        return self._ps

    async def connect(self) -> None:
        self._ps = PersistentState(self.db_path, self.schema_path)
        await self._ps.connect()

    async def close(self) -> None:
        if self._ps is not None:
            await self._ps.close()
            self._ps = None

    async def chain_head_uuid(self, session_id: int) -> str | None:
        return await self._store.chain_head_uuid(session_id)

    async def persist_user(self, session_id: int, text: str) -> str:
        return await self._store.persist_user(session_id, text)

    async def persist_assistant_begin(self, session_id: int, parent_uuid: str) -> str:
        return await self._store.persist_assistant_begin(session_id, parent_uuid)

    async def _flush_assistant_text(self, assistant_uuid: str, full_text: str) -> None:
        await self._store.flush_assistant_text(assistant_uuid, full_text)

    def schedule_assistant_append(
        self, assistant_uuid: str, full_text: str
    ) -> None:
        """Debounce disk writes while streaming (§5.2)."""

        async def _debounced() -> None:
            await asyncio.sleep(self.debounce_ms / 1000.0)
            await self._flush_assistant_text(assistant_uuid, full_text)
            self._debounce_tasks.pop(assistant_uuid, None)

        prev = self._debounce_tasks.get(assistant_uuid)
        if prev and not prev.done():
            prev.cancel()
        self._debounce_tasks[assistant_uuid] = asyncio.create_task(_debounced())

    async def persist_assistant_finalize(
        self,
        assistant_uuid: str,
        final_text: str,
        meta: dict[str, Any] | None = None,
        *,
        function_calls: list[dict[str, Any]] | None = None,
    ) -> None:
        t = self._debounce_tasks.pop(assistant_uuid, None)
        if t and not t.done():
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
        await self._store.persist_assistant_finalize(
            assistant_uuid,
            final_text,
            meta,
            function_calls=function_calls,
        )

    async def persist_tool_result(
        self,
        session_id: int,
        *,
        parent_assistant_uuid: str,
        name: str,
        tool_call_id: str | None,
        response: dict[str, Any],
    ) -> str:
        return await self._store.persist_tool_result(
            session_id,
            parent_assistant_uuid=parent_assistant_uuid,
            name=name,
            tool_call_id=tool_call_id,
            response=response,
        )

    async def record_web_tool_artifacts(
        self,
        session_id: int,
        tool_name: str,
        args: dict[str, Any],
        response: dict[str, Any],
    ) -> None:
        if tool_name not in ("web_search", "fetch_url_text"):
            return
        await self._store.record_web_tool_artifacts(
            session_id, tool_name, args, response
        )

    async def list_web_sources(
        self, session_id: int, *, limit: int = 50
    ) -> list[dict[str, Any]]:
        return await self._store.list_web_sources(session_id, limit=limit)

    async def record_usage(
        self,
        session_id: int,
        *,
        model: str | None,
        input_tokens: int | None,
        output_tokens: int | None,
        usage_extras_json: str | None = None,
    ) -> None:
        await self._store.record_usage(
            session_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            usage_extras_json=usage_extras_json,
        )

    async def get_session_token_usage(self, session_id: int) -> dict[str, Any]:
        return await self._store.get_session_token_usage(session_id)

    async def tombstone(
        self,
        uuids: Sequence[str],
        session_id: int,
        *,
        rewire_orphans: bool = True,
    ) -> None:
        await self._store.tombstone(
            uuids, session_id, rewire_orphans=rewire_orphans
        )

    async def rewire_parents_after_tombstone(
        self, session_id: int, tombstoned_uuids: Sequence[str]
    ) -> None:
        await self._store.rewire_parents_after_tombstone(session_id, tombstoned_uuids)

    async def load_chain_for_api(self, session_id: int) -> list[dict[str, Any]]:
        return await self._store.load_chain_for_api(session_id)

    async def state_set(self, key: str, value: str) -> None:
        await self._store.state_set(key, value)

    async def state_get(self, key: str) -> str | None:
        return await self._store.state_get(key)

    async def get_task_plan_json(self, task_id: int) -> str:
        return await self._store.get_task_plan_json(task_id)

    async def set_task_plan_json(self, task_id: int, plan_json: str) -> None:
        await self._store.set_task_plan_json(task_id, plan_json)

    async def update_task(
        self,
        task_id: int,
        *,
        status: str | None = None,
        current_output: str | None = None,
    ) -> None:
        await self._store.update_task(
            task_id, status=status, current_output=current_output
        )

    async def insert_task(
        self,
        goal: str,
        status: str = "pending",
        *,
        task_kind: TaskKind = TASK_KIND_GOAL,
    ) -> int:
        return await self._store.insert_task(goal, status, task_kind=task_kind)

    async def fetch_pending_task(self) -> tuple[int, str] | None:
        return await self._store.fetch_pending_task()

    async def latest_cli_session_task_id(self) -> int | None:
        return await self._store.latest_cli_session_task_id()

    async def list_goal_tasks(
        self,
        *,
        limit: int = 50,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return await self._store.list_goal_tasks(limit=limit, status=status)

    async def get_goal_task(self, task_id: int) -> dict[str, Any]:
        return await self._store.get_goal_task(task_id)

    async def get_goal_task_view_for_tool(self, task_id: int) -> dict[str, Any]:
        """Read-only goal row fields for the read_goal_task_view tool (raises like get_goal_task)."""
        r = await self.get_goal_task(task_id)
        return {
            "task_id": r["id"],
            "goal": r["goal"],
            "status": r["status"],
            "current_output": r["current_output"],
            "plan_json": r["plan_json"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }

    async def append_action_log(
        self,
        kind: str,
        payload: dict[str, Any],
        session_id: int | None = None,
    ) -> int:
        return await self._store.append_action_log(kind, payload, session_id)

    async def load_messages_for_dream(
        self, *, session_id: int | None, limit: int
    ) -> list[str]:
        return await self._store.load_messages_for_dream(
            session_id=session_id, limit=limit
        )

    async def load_usage_ledger_lines(self, limit: int) -> list[str]:
        return await self._store.load_usage_ledger_lines(limit)

    async def insert_knowledge_source(
        self,
        kind: KnowledgeKind,
        *,
        label: str | None = None,
        base_url: str = "",
    ) -> int:
        return await self._store.insert_knowledge_source(
            kind, label=label, base_url=base_url
        )

    async def list_knowledge_sources(
        self, *, kind: str | None = None
    ) -> list[dict[str, Any]]:
        return await self._store.list_knowledge_sources(kind=kind)

    async def insert_knowledge_item(
        self,
        source_id: int,
        content_hash: str,
        *,
        tags: list[str] | None = None,
        content_excerpt: str = "",
        payload: dict[str, Any] | None = None,
        external_id: str | None = None,
        published_at: str | None = None,
        relevance_score: float | None = None,
        expires_at: str | None = None,
        tombstoned: int = 0,
    ) -> KnowledgeItemInsertResult:
        return await self._store.insert_knowledge_item(
            source_id,
            content_hash,
            tags=tags,
            content_excerpt=content_excerpt,
            payload=payload,
            external_id=external_id,
            published_at=published_at,
            relevance_score=relevance_score,
            expires_at=expires_at,
            tombstoned=tombstoned,
        )

    async def insert_knowledge_synthesis(
        self,
        body: str,
        ref_item_ids: list[int],
        *,
        task_id: int | None = None,
    ) -> int:
        return await self._store.insert_knowledge_synthesis(
            body, ref_item_ids, task_id=task_id
        )

    async def get_knowledge_item(self, item_id: int) -> dict[str, Any]:
        return await self._store.get_knowledge_item(item_id)

    async def list_knowledge_items(
        self,
        *,
        source_id: int | None = None,
        limit: int = 100,
        ingested_after: str | None = None,
        ingested_before: str | None = None,
        min_relevance_score: float | None = None,
        valid_at_now: bool = True,
    ) -> list[dict[str, Any]]:
        return await self._store.list_knowledge_items(
            source_id=source_id,
            limit=limit,
            ingested_after=ingested_after,
            ingested_before=ingested_before,
            min_relevance_score=min_relevance_score,
            valid_at_now=valid_at_now,
        )

    async def search_knowledge_items(
        self,
        query: str,
        *,
        limit: int = 50,
        tag: str | None = None,
        ingested_after: str | None = None,
        ingested_before: str | None = None,
        prefer_fts: bool = True,
        search_mode: str = "lexical",
        query_embedding: list[float] | None = None,
        embedding_model: str | None = None,
        embedding_min_cosine: float = 0.25,
        min_relevance_score: float | None = None,
        valid_at_now: bool = True,
    ) -> list[dict[str, Any]]:
        return await self._store.search_knowledge_items(
            query,
            limit=limit,
            tag=tag,
            ingested_after=ingested_after,
            ingested_before=ingested_before,
            prefer_fts=prefer_fts,
            search_mode=search_mode,
            query_embedding=query_embedding,
            embedding_model=embedding_model,
            embedding_min_cosine=embedding_min_cosine,
            min_relevance_score=min_relevance_score,
            valid_at_now=valid_at_now,
        )

    async def upsert_knowledge_item_embedding(
        self,
        item_id: int,
        *,
        model: str,
        dim: int,
        embedding: bytes,
        content_hash: str,
    ) -> None:
        await self._store.upsert_knowledge_item_embedding(
            item_id,
            model=model,
            dim=dim,
            embedding=embedding,
            content_hash=content_hash,
        )

    async def list_knowledge_synthesis_for_task(
        self, task_id: int
    ) -> list[dict[str, Any]]:
        return await self._store.list_knowledge_synthesis_for_task(task_id)

    async def delete_knowledge_source(self, source_id: int) -> None:
        await self._store.delete_knowledge_source(source_id)

    async def list_unscored_knowledge(self, limit: int = 20) -> list[dict[str, Any]]:
        return await self._store.list_unscored_knowledge(limit)

    async def update_impact_score(self, knowledge_id: int, score: int) -> None:
        await self._store.update_impact_score(knowledge_id, score)

    async def insert_market_metric(
        self,
        metric_name: str,
        numeric_value: float,
        *,
        recorded_at: str | None = None,
        api_source: str = "",
    ) -> int:
        return await self._store.insert_market_metric(
            metric_name,
            numeric_value,
            recorded_at=recorded_at,
            api_source=api_source,
        )

    async def insert_synthesis_edge(
        self,
        knowledge_id: int,
        metric_id: int,
        causality_notes: str = "",
    ) -> int:
        return await self._store.insert_synthesis_edge(
            knowledge_id, metric_id, causality_notes
        )
