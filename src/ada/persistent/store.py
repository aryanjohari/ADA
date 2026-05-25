"""PersistentState — SQLite transcript, tasks, state KV, usage (claude_logic §2.1)."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import sqlite3
from collections.abc import Sequence
from datetime import datetime
from urllib.parse import urlparse, urlunparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import aiosqlite

TaskKind = Literal["chat", "goal", "system"]
KnowledgeKind = Literal["api", "rss", "web", "brand"]
TASK_KIND_CHAT: TaskKind = "chat"
TASK_KIND_GOAL: TaskKind = "goal"
TASK_KIND_SYSTEM: TaskKind = "system"


@dataclass(frozen=True)
class KnowledgeItemInsertResult:
    """Result of insert_knowledge_item (dedupe may skip insert)."""

    id: int
    inserted: bool

from ada.knowledge_embeddings import blob_to_float32_list, cosine_similarity
from ada.knowledge_search import build_fts_match_query, reciprocal_rank_fusion
from ada.triage.categories import TRIAGE_CATEGORY_CODES
from ada.workflow.steps import WORKFLOW_VALID_STEP_TYPES
from ada.transcript_format import (
    ROLE_ASSISTANT,
    ROLE_SYSTEM,
    ROLE_TOOL,
    ROLE_USER,
    new_uuid,
    pack_assistant_full,
    pack_assistant_text,
    pack_user_text,
)

GRAPH_EDGE_ACTIVE = "active"
GRAPH_EDGE_SUPERSEDED = "superseded"
GRAPH_EDGE_INVALID = "invalid"
GRAPH_EDGE_STATUSES = {
    GRAPH_EDGE_ACTIVE,
    GRAPH_EDGE_SUPERSEDED,
    GRAPH_EDGE_INVALID,
}


def _canonical_story_link(url: str) -> str | None:
    """Normalize http(s) URLs for cross-feed dedupe (scheme, host, path; drop fragment)."""
    raw = (url or "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return raw
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or ""
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse((scheme, netloc, path, "", parsed.query, ""))


def _story_link_sql_match_values(url: str) -> list[str]:
    """Distinct lower(trim(...)) values to match json payload link across feeds."""
    raw = (url or "").strip()
    if not raw:
        return []
    canon = _canonical_story_link(url)
    if not canon:
        return [raw.lower().strip()]
    candidates = [raw, canon]
    p = urlparse(canon)
    if p.scheme == "https":
        candidates.append(
            urlunparse(("http", p.netloc, p.path, "", p.query, ""))
        )
    elif p.scheme == "http":
        candidates.append(
            urlunparse(("https", p.netloc, p.path, "", p.query, ""))
        )
    seen: set[str] = set()
    out: list[str] = []
    for c in candidates:
        k = c.strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


@dataclass
class PersistentState:
    """Owns SQLite + schema; no GenAI client, no tool execution."""

    db_path: Path
    schema_path: Path

    _conn: aiosqlite.Connection | None = field(default=None, repr=False)

    async def connect(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.execute("PRAGMA journal_mode = WAL")
        await self._apply_schema()
        await self._migrate_schema()
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def _apply_schema(self) -> None:
        assert self._conn is not None
        sql = self.schema_path.read_text(encoding="utf-8")
        await self._conn.executescript(sql)

    async def _migrate_schema(self) -> None:
        assert self._conn is not None
        cur = await self._conn.execute("PRAGMA table_info(tasks)")
        cols = {str(row[1]) for row in await cur.fetchall()}
        if "plan_json" not in cols:
            await self._conn.execute(
                "ALTER TABLE tasks ADD COLUMN plan_json TEXT NOT NULL DEFAULT '{}'"
            )
        cur = await self._conn.execute("PRAGMA table_info(tasks)")
        cols = {str(row[1]) for row in await cur.fetchall()}
        if "task_kind" not in cols:
            await self._conn.execute(
                "ALTER TABLE tasks ADD COLUMN task_kind TEXT NOT NULL DEFAULT 'goal'"
            )
        await self._conn.execute(
            "UPDATE tasks SET task_kind = ? WHERE goal = 'Interactive session'",
            (TASK_KIND_CHAT,),
        )
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='action_log'"
        )
        if await cur.fetchone() is None:
            await self._conn.execute(
                """
                CREATE TABLE action_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
                    kind TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            await self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_action_log_created ON action_log(created_at)"
            )
            await self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_action_log_session ON action_log(session_id, created_at)"
            )

        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='web_sources'"
        )
        if await cur.fetchone() is None:
            await self._conn.execute(
                """
                CREATE TABLE web_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    url TEXT NOT NULL,
                    source_kind TEXT NOT NULL CHECK (source_kind IN ('search_hit', 'page_fetch')),
                    query_text TEXT,
                    content_excerpt TEXT NOT NULL DEFAULT '',
                    content_sha256 TEXT,
                    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            await self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_web_sources_session_fetched "
                "ON web_sources(session_id, fetched_at DESC)"
            )

        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_sources'"
        )
        if await cur.fetchone() is None:
            await self._conn.execute(
                """
                CREATE TABLE knowledge_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL CHECK (kind IN ('api', 'rss', 'web', 'brand')),
                    label TEXT,
                    base_url TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            await self._conn.execute(
                """
                CREATE TABLE knowledge_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL REFERENCES knowledge_sources(id) ON DELETE CASCADE,
                    external_id TEXT,
                    published_at TEXT,
                    ingested_at TEXT NOT NULL DEFAULT (datetime('now')),
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    content_excerpt TEXT NOT NULL DEFAULT '',
                    payload_json TEXT,
                    content_hash TEXT NOT NULL,
                    relevance_score REAL,
                    impact_score INTEGER CHECK (impact_score IS NULL OR (impact_score >= 1 AND impact_score <= 10)),
                    triage_primary_category TEXT,
                    triage_secondary_categories_json TEXT NOT NULL DEFAULT '[]',
                    expires_at TEXT,
                    tombstoned INTEGER NOT NULL DEFAULT 0 CHECK (tombstoned IN (0, 1))
                )
                """
            )
            await self._conn.execute(
                """
                CREATE INDEX idx_knowledge_items_source_ingested
                    ON knowledge_items(source_id, ingested_at DESC)
                """
            )
            await self._conn.execute(
                """
                CREATE UNIQUE INDEX idx_knowledge_items_source_external
                    ON knowledge_items(source_id, external_id)
                    WHERE external_id IS NOT NULL
                """
            )
            await self._conn.execute(
                """
                CREATE TABLE knowledge_synthesis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    body TEXT NOT NULL,
                    ref_item_ids_json TEXT NOT NULL DEFAULT '[]',
                    task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            await self._conn.executescript(self._knowledge_fts_ddl())

        await self._ensure_knowledge_item_embeddings_table()
        await self._migrate_knowledge_fts_if_needed()
        await self._migrate_knowledge_fts_payload_doc_v1()
        await self._ensure_knowledge_items_score_ttl_columns()
        await self._ensure_impact_score_and_kernel_indexes()
        await self._ensure_triage_category_columns()
        await self._migrate_knowledge_fts_triage_doc_v1()
        await self._ensure_market_metrics_and_synthesis_edges()
        await self._ensure_phase1_ingest_audit()
        await self._ensure_knowledge_source_kind_brand()
        await self._ensure_phase2_graph_lite()
        await self._ensure_publisher_graph_columns()
        await self._ensure_phase3_workflows()
        await self._ensure_publisher_workflow_step_types()
        await self._ensure_missions_schema()
        await self._ensure_knowledge_sources_mission_id()
        await self._ensure_entities_mission_scope()
        await self._ensure_job_plane_schema()
        await self._ensure_graph_edges_mission_id()

    async def _ensure_knowledge_sources_mission_id(self) -> None:
        """Mission-scoped knowledge sources (nullable = legacy global pool)."""
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_sources'"
        )
        if await cur.fetchone() is None:
            return
        cur = await self._conn.execute("PRAGMA table_info(knowledge_sources)")
        ks_cols = {str(row[1]) for row in await cur.fetchall()}
        if "mission_id" not in ks_cols:
            await self._conn.execute(
                """
                ALTER TABLE knowledge_sources ADD COLUMN mission_id INTEGER
                    REFERENCES missions(id) ON DELETE SET NULL
                """
            )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_sources_mission "
            "ON knowledge_sources(mission_id)"
        )
        await self._conn.commit()

    async def _ensure_entities_mission_scope(self) -> None:
        """Replace global UNIQUE(type,normalized_name) with mission-scoped partial uniques."""
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='entities'"
        )
        if await cur.fetchone() is None:
            return
        cur = await self._conn.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type='index' AND name='idx_entities_global_type_norm'
            """
        )
        if await cur.fetchone() is not None:
            return
        cur = await self._conn.execute("PRAGMA table_info(entities)")
        ecols = {str(row[1]) for row in await cur.fetchall()}
        has_lei = "last_enriched_at" in ecols
        try:
            await self._conn.execute("PRAGMA foreign_keys = OFF")
            await self._conn.execute("DROP TABLE IF EXISTS entities__mission_scoped")
            await self._conn.execute(
                """
                CREATE TABLE entities__mission_scoped (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    normalized_name TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    last_enriched_at TEXT,
                    mission_id INTEGER REFERENCES missions(id) ON DELETE SET NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            if has_lei:
                await self._conn.execute(
                    """
                    INSERT INTO entities__mission_scoped (
                        id, type, name, normalized_name,
                        payload_json, last_enriched_at, mission_id, created_at
                    )
                    SELECT id, type, name, normalized_name, payload_json,
                           last_enriched_at, NULL, created_at
                    FROM entities
                    """
                )
            else:
                await self._conn.execute(
                    """
                    INSERT INTO entities__mission_scoped (
                        id, type, name, normalized_name,
                        payload_json, last_enriched_at, mission_id, created_at
                    )
                    SELECT id, type, name, normalized_name, payload_json,
                           NULL, NULL, created_at
                    FROM entities
                    """
                )
            await self._conn.execute("DROP TABLE entities")
            await self._conn.execute(
                "ALTER TABLE entities__mission_scoped RENAME TO entities"
            )
            await self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_entities_normalized "
                "ON entities(normalized_name)"
            )
            await self._conn.execute(
                """
                CREATE UNIQUE INDEX idx_entities_global_type_norm
                    ON entities(type, normalized_name)
                    WHERE mission_id IS NULL
                """
            )
            await self._conn.execute(
                """
                CREATE UNIQUE INDEX idx_entities_mission_type_norm
                    ON entities(mission_id, type, normalized_name)
                    WHERE mission_id IS NOT NULL
                """
            )
            await self._conn.commit()
        except Exception:
            await self._conn.rollback()
            raise
        finally:
            await self._conn.execute("PRAGMA foreign_keys = ON")

    async def _ensure_missions_schema(self) -> None:
        """missions table + optional tasks.mission_id FK (ON DELETE SET NULL)."""
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='missions'"
        )
        if await cur.fetchone() is None:
            await self._conn.execute(
                """
                CREATE TABLE missions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    niche TEXT,
                    topic TEXT,
                    defaults_json TEXT NOT NULL DEFAULT '{}',
                    brief_md TEXT NOT NULL DEFAULT '',
                    brief_md_path TEXT,
                    schedule_hint_json TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
        cur = await self._conn.execute("PRAGMA table_info(tasks)")
        tcols = {str(row[1]) for row in await cur.fetchall()}
        if "mission_id" not in tcols:
            await self._conn.execute(
                """
                ALTER TABLE tasks ADD COLUMN mission_id INTEGER
                    REFERENCES missions(id) ON DELETE SET NULL
                """
            )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_tasks_mission_id ON tasks(mission_id)"
        )
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='workflows'"
        )
        if await cur.fetchone() is not None:
            cur = await self._conn.execute("PRAGMA table_info(workflows)")
            wfcols = {str(row[1]) for row in await cur.fetchall()}
            if "mission_id" not in wfcols:
                await self._conn.execute(
                    """
                    ALTER TABLE workflows ADD COLUMN mission_id INTEGER
                        REFERENCES missions(id) ON DELETE SET NULL
                    """
                )
            await self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_workflows_mission_id ON workflows(mission_id)"
            )
        await self._conn.commit()

    async def _ensure_job_plane_schema(self) -> None:
        """system_jobs queue + tasks.goal_dispatch_generation for idempotent goal.run_turn."""
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='system_jobs'"
        )
        if await cur.fetchone() is None:
            await self._conn.execute(
                """
                CREATE TABLE system_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    mission_id INTEGER REFERENCES missions(id) ON DELETE SET NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    idempotency_key TEXT,
                    status TEXT NOT NULL DEFAULT 'pending' CHECK (
                        status IN ('pending', 'running', 'completed', 'failed', 'dead', 'cancelled')
                    ),
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 8,
                    error TEXT NOT NULL DEFAULT '',
                    lease_owner TEXT NOT NULL DEFAULT '',
                    lease_expires_at TEXT,
                    run_after TEXT,
                    priority INTEGER NOT NULL DEFAULT 0,
                    correlation_id TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    started_at TEXT
                )
                """
            )
            await self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_system_jobs_status_run
                    ON system_jobs(status, run_after, priority DESC, id)
                """
            )
            await self._conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_system_jobs_idempotency
                    ON system_jobs(idempotency_key)
                    WHERE idempotency_key IS NOT NULL
                """
            )
        cur = await self._conn.execute("PRAGMA table_info(tasks)")
        tcols = {str(row[1]) for row in await cur.fetchall()}
        if "goal_dispatch_generation" not in tcols:
            await self._conn.execute(
                """
                ALTER TABLE tasks ADD COLUMN goal_dispatch_generation
                    INTEGER NOT NULL DEFAULT 0
                """
            )
        await self._conn.commit()

    async def _ensure_graph_edges_mission_id(self) -> None:
        """Mission scope on graph_edges (P0); nullable until backfill for ambiguous rows."""
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='graph_edges'"
        )
        if await cur.fetchone() is None:
            return
        cur = await self._conn.execute("PRAGMA table_info(graph_edges)")
        gcols = {str(row[1]) for row in await cur.fetchall()}
        if "mission_id" not in gcols:
            await self._conn.execute(
                """
                ALTER TABLE graph_edges ADD COLUMN mission_id INTEGER
                    REFERENCES missions(id) ON DELETE SET NULL
                """
            )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_graph_edges_mission_src "
            "ON graph_edges(mission_id, src_entity_id)"
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_graph_edges_mission_dst "
            "ON graph_edges(mission_id, dst_entity_id)"
        )
        cur_ent = await self._conn.execute("PRAGMA table_info(entities)")
        ent_cols = {str(row[1]) for row in await cur_ent.fetchall()}
        if "mission_id" in ent_cols:
            # Backfill when both endpoints share the same non-null mission.
            await self._conn.execute(
                """
                UPDATE graph_edges
                SET mission_id = (
                    SELECT e.mission_id FROM entities e WHERE e.id = graph_edges.src_entity_id
                )
                WHERE mission_id IS NULL
                  AND EXISTS (
                    SELECT 1 FROM entities s, entities d
                    WHERE s.id = graph_edges.src_entity_id
                      AND d.id = graph_edges.dst_entity_id
                      AND s.mission_id IS NOT NULL
                      AND s.mission_id IS d.mission_id
                  )
                """
            )
        await self._conn.commit()

    async def _ensure_phase3_workflows(self) -> None:
        """workflows + workflow_steps (Phase 3 workflow engine)."""
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='workflows'"
        )
        if await cur.fetchone() is None:
            await self._conn.execute(
                """
                CREATE TABLE workflows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    goal_text TEXT NOT NULL,
                    params_json TEXT NOT NULL DEFAULT '{}',
                    idempotency_key TEXT,
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'running', 'completed', 'failed')),
                    parent_task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    UNIQUE (kind, idempotency_key)
                )
                """
            )
            await self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_workflows_parent ON workflows(parent_task_id)"
            )
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='workflow_steps'"
        )
        if await cur.fetchone() is None:
            await self._conn.execute(
                """
                CREATE TABLE workflow_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id INTEGER NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
                    step_index INTEGER NOT NULL,
                    step_type TEXT NOT NULL CHECK (step_type IN (
                        'FETCH', 'EXTRACT', 'SYNTHESIZE', 'ENRICH', 'GATE', 'DRAFT', 'DEPLOY'
                    )),
                    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
                        'pending', 'running', 'completed', 'failed', 'skipped')),
                    input_json TEXT NOT NULL DEFAULT '{}',
                    output_json TEXT NOT NULL DEFAULT '{}',
                    error TEXT NOT NULL DEFAULT '',
                    idempotency_key TEXT,
                    task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    UNIQUE (workflow_id, step_index),
                    UNIQUE (workflow_id, idempotency_key)
                )
                """
            )
            await self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_workflow_steps_workflow "
                "ON workflow_steps(workflow_id, step_index)"
            )
        else:
            cur = await self._conn.execute("PRAGMA table_info(workflow_steps)")
            wcols = {str(row[1]) for row in await cur.fetchall()}
            if "attempt_count" not in wcols:
                await self._conn.execute(
                    "ALTER TABLE workflow_steps ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 0"
                )
        await self._conn.commit()

    async def _ensure_publisher_graph_columns(self) -> None:
        """B2B publisher: entities.last_enriched_at, graph_edges.source_url."""
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='entities'"
        )
        if await cur.fetchone() is None:
            return
        cur = await self._conn.execute("PRAGMA table_info(entities)")
        ecols = {str(row[1]) for row in await cur.fetchall()}
        if "last_enriched_at" not in ecols:
            await self._conn.execute(
                "ALTER TABLE entities ADD COLUMN last_enriched_at TEXT"
            )
        cur = await self._conn.execute("PRAGMA table_info(graph_edges)")
        gcols = {str(row[1]) for row in await cur.fetchall()}
        if gcols and "source_url" not in gcols:
            await self._conn.execute(
                "ALTER TABLE graph_edges ADD COLUMN source_url TEXT"
            )
        await self._conn.commit()

    async def _ensure_publisher_workflow_step_types(self) -> None:
        """Recreate workflow_steps if CHECK still limits step_type to pre-publisher set."""
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='workflow_steps'"
        )
        if await cur.fetchone() is None:
            return
        cur = await self._conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='workflow_steps'"
        )
        row = await cur.fetchone()
        create_sql = str(row[0] or "")
        if "ENRICH" in create_sql and "DEPLOY" in create_sql:
            return
        try:
            await self._conn.execute("DROP TABLE IF EXISTS workflow_steps__pub")
            await self._conn.execute(
                """
                CREATE TABLE workflow_steps__pub (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id INTEGER NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
                    step_index INTEGER NOT NULL,
                    step_type TEXT NOT NULL CHECK (step_type IN (
                        'FETCH', 'EXTRACT', 'SYNTHESIZE', 'ENRICH', 'GATE', 'DRAFT', 'DEPLOY'
                    )),
                    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
                        'pending', 'running', 'completed', 'failed', 'skipped'
                    )),
                    input_json TEXT NOT NULL DEFAULT '{}',
                    output_json TEXT NOT NULL DEFAULT '{}',
                    error TEXT NOT NULL DEFAULT '',
                    idempotency_key TEXT,
                    task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    UNIQUE (workflow_id, step_index),
                    UNIQUE (workflow_id, idempotency_key)
                )
                """
            )
            await self._conn.execute(
                """
                INSERT INTO workflow_steps__pub
                SELECT id, workflow_id, step_index, step_type, status, input_json, output_json,
                       error, idempotency_key, task_id, attempt_count, created_at, updated_at
                FROM workflow_steps
                """
            )
            await self._conn.execute("DROP TABLE workflow_steps")
            await self._conn.execute(
                "ALTER TABLE workflow_steps__pub RENAME TO workflow_steps"
            )
            await self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_workflow_steps_workflow "
                "ON workflow_steps(workflow_id, step_index)"
            )
            await self._conn.commit()
        except Exception:
            await self._conn.rollback()
            raise

    async def _ensure_phase1_ingest_audit(self) -> None:
        """ingest_jobs, ingest_raw, source_catalog; knowledge_sources.config_json."""
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ingest_jobs'"
        )
        if await cur.fetchone() is None:
            await self._conn.execute(
                """
                CREATE TABLE ingest_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    params_json TEXT NOT NULL DEFAULT '{}',
                    idempotency_key TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    error TEXT NOT NULL DEFAULT '',
                    started_at TEXT,
                    completed_at TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    UNIQUE (kind, idempotency_key)
                )
                """
            )
            await self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ingest_jobs_status_created "
                "ON ingest_jobs(status, created_at)"
            )
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ingest_raw'"
        )
        if await cur.fetchone() is None:
            await self._conn.execute(
                """
                CREATE TABLE ingest_raw (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ingest_job_id INTEGER REFERENCES ingest_jobs(id) ON DELETE SET NULL,
                    source TEXT NOT NULL,
                    uri TEXT NOT NULL DEFAULT '',
                    content_sha256 TEXT NOT NULL,
                    body TEXT NOT NULL DEFAULT '',
                    meta_json TEXT NOT NULL DEFAULT '{}',
                    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            await self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ingest_raw_sha ON ingest_raw(content_sha256)"
            )
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='source_catalog'"
        )
        if await cur.fetchone() is None:
            await self._conn.execute(
                """
                CREATE TABLE source_catalog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    kind TEXT NOT NULL,
                    config_json TEXT NOT NULL DEFAULT '{}',
                    host_allowlist_json TEXT NOT NULL DEFAULT '[]',
                    maps_to_kind TEXT NOT NULL DEFAULT '',
                    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_sources'"
        )
        if await cur.fetchone() is not None:
            cur = await self._conn.execute("PRAGMA table_info(knowledge_sources)")
            ks_cols = {str(row[1]) for row in await cur.fetchall()}
            if "config_json" not in ks_cols:
                await self._conn.execute(
                    "ALTER TABLE knowledge_sources ADD COLUMN config_json TEXT NOT NULL DEFAULT '{}'"
                )
        await self._conn.commit()

    async def _ensure_phase2_graph_lite(self) -> None:
        """Create Phase 2 graph-lite tables for upgraded DBs."""
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_items'"
        )
        if await cur.fetchone() is None:
            return
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (type, normalized_name)
            )
            """
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_entities_normalized ON entities(normalized_name)"
        )
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS graph_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                src_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                dst_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                edge_type TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
                status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'superseded', 'invalid')),
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                superseded_by INTEGER REFERENCES graph_edges(id)
            )
            """
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_graph_edges_src ON graph_edges(src_entity_id)"
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_graph_edges_dst ON graph_edges(dst_entity_id)"
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_graph_edges_type ON graph_edges(edge_type)"
        )
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS edge_evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                edge_id INTEGER NOT NULL REFERENCES graph_edges(id) ON DELETE CASCADE,
                knowledge_id INTEGER NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
                span_json TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (edge_id, knowledge_id)
            )
            """
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_edge_evidence_edge ON edge_evidence(edge_id)"
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_edge_evidence_knowledge ON edge_evidence(knowledge_id)"
        )
        await self._conn.commit()

    async def _ensure_knowledge_source_kind_brand(self) -> None:
        """Allow knowledge_sources.kind='brand' on upgraded DBs."""
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='knowledge_sources'"
        )
        row = await cur.fetchone()
        create_sql = str((row[0] if row else "") or "")
        if "'brand'" in create_sql:
            return
        try:
            await self._conn.execute("PRAGMA foreign_keys = OFF")
            await self._conn.execute("DROP TABLE IF EXISTS knowledge_sources__brand")
            await self._conn.execute(
                """
                CREATE TABLE knowledge_sources__brand (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL CHECK (kind IN ('api', 'rss', 'web', 'brand')),
                    label TEXT,
                    base_url TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    config_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            await self._conn.execute(
                """
                INSERT INTO knowledge_sources__brand(id, kind, label, base_url, created_at, config_json)
                SELECT id, kind, label, base_url, created_at, COALESCE(config_json, '{}')
                FROM knowledge_sources
                """
            )
            await self._conn.execute("DROP TABLE knowledge_sources")
            await self._conn.execute(
                "ALTER TABLE knowledge_sources__brand RENAME TO knowledge_sources"
            )
            await self._conn.execute("PRAGMA foreign_keys = ON")
            await self._conn.commit()
        except Exception:
            await self._conn.execute("PRAGMA foreign_keys = ON")
            await self._conn.rollback()
            raise

    async def _ensure_impact_score_and_kernel_indexes(self) -> None:
        """Add impact_score + triage indexes for upgraded DBs."""
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_items'"
        )
        if await cur.fetchone() is None:
            return
        cur = await self._conn.execute("PRAGMA table_info(knowledge_items)")
        cols = {str(row[1]) for row in await cur.fetchall()}
        if "impact_score" not in cols:
            await self._conn.execute(
                """
                ALTER TABLE knowledge_items ADD COLUMN impact_score INTEGER
                CHECK (impact_score IS NULL OR (impact_score >= 1 AND impact_score <= 10))
                """
            )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_items_unscored_ingested "
            "ON knowledge_items(ingested_at DESC) WHERE impact_score IS NULL"
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_items_impact_score "
            "ON knowledge_items(impact_score) WHERE impact_score IS NOT NULL"
        )
        await self._conn.commit()

    async def _ensure_triage_category_columns(self) -> None:
        """Add triage_primary_category + triage_secondary_categories_json for upgraded DBs."""
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_items'"
        )
        if await cur.fetchone() is None:
            return
        cur = await self._conn.execute("PRAGMA table_info(knowledge_items)")
        cols = {str(row[1]) for row in await cur.fetchall()}
        if "triage_primary_category" not in cols:
            await self._conn.execute(
                "ALTER TABLE knowledge_items ADD COLUMN triage_primary_category TEXT"
            )
        if "triage_secondary_categories_json" not in cols:
            await self._conn.execute(
                """
                ALTER TABLE knowledge_items ADD COLUMN triage_secondary_categories_json
                    TEXT NOT NULL DEFAULT '[]'
                """
            )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_items_triage_primary_ingested "
            "ON knowledge_items(triage_primary_category, ingested_at DESC) "
            "WHERE triage_primary_category IS NOT NULL AND tombstoned = 0"
        )
        await self._conn.commit()

    async def _migrate_knowledge_fts_triage_doc_v1(self) -> None:
        """Rebuild FTS doc + triggers to include triage category columns."""
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT value FROM state WHERE key = ?",
            ("schema.knowledge_fts.triage_doc_v1",),
        )
        row = await cur.fetchone()
        if row and str(row[0]) == "1":
            return
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_items_fts'"
        )
        if await cur.fetchone() is None:
            return
        cur = await self._conn.execute("PRAGMA table_info(knowledge_items)")
        cols = {str(row[1]) for row in await cur.fetchall()}
        if "triage_primary_category" not in cols or "triage_secondary_categories_json" not in cols:
            return
        await self._conn.executescript(
            """
            DROP TRIGGER IF EXISTS knowledge_items_ai;
            DROP TRIGGER IF EXISTS knowledge_items_ad;
            DROP TRIGGER IF EXISTS knowledge_items_au;
            """
        )
        await self._conn.executescript(
            """
            CREATE TRIGGER knowledge_items_ai AFTER INSERT ON knowledge_items BEGIN
                INSERT INTO knowledge_items_fts(rowid, doc)
                VALUES (
                    new.id,
                    new.content_excerpt || ' ' || new.tags_json || ' ' ||
                    COALESCE(json_extract(new.payload_json, '$.link'), '') || ' ' ||
                    COALESCE(json_extract(new.payload_json, '$.title'), '') || ' ' ||
                    COALESCE(json_extract(new.payload_json, '$.feed_url'), '') || ' ' ||
                    COALESCE(new.triage_primary_category, '') || ' ' ||
                    COALESCE(new.triage_secondary_categories_json, '')
                );
            END;
            CREATE TRIGGER knowledge_items_ad AFTER DELETE ON knowledge_items BEGIN
                INSERT INTO knowledge_items_fts(knowledge_items_fts, rowid)
                VALUES('delete', old.id);
            END;
            CREATE TRIGGER knowledge_items_au AFTER UPDATE ON knowledge_items BEGIN
                INSERT INTO knowledge_items_fts(knowledge_items_fts, rowid)
                VALUES('delete', old.id);
                INSERT INTO knowledge_items_fts(rowid, doc)
                VALUES (
                    new.id,
                    new.content_excerpt || ' ' || new.tags_json || ' ' ||
                    COALESCE(json_extract(new.payload_json, '$.link'), '') || ' ' ||
                    COALESCE(json_extract(new.payload_json, '$.title'), '') || ' ' ||
                    COALESCE(json_extract(new.payload_json, '$.feed_url'), '') || ' ' ||
                    COALESCE(new.triage_primary_category, '') || ' ' ||
                    COALESCE(new.triage_secondary_categories_json, '')
                );
            END;
            """
        )
        cur = await self._conn.execute("SELECT id FROM knowledge_items")
        for row in await cur.fetchall():
            rid = int(row[0])
            await self._conn.execute(
                "INSERT INTO knowledge_items_fts(knowledge_items_fts, rowid) VALUES('delete', ?)",
                (rid,),
            )
        expr = self._knowledge_fts_doc_select_expr(include_triage=True)
        await self._conn.execute(
            f"""
            INSERT INTO knowledge_items_fts(rowid, doc)
            SELECT id, {expr} FROM knowledge_items
            """
        )
        await self._conn.execute(
            """
            INSERT INTO state(key, value) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            ("schema.knowledge_fts.triage_doc_v1", "1"),
        )
        await self._conn.commit()

    async def _ensure_market_metrics_and_synthesis_edges(self) -> None:
        """Create market_metrics and synthesis_edges when upgrading older DBs."""
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_items'"
        )
        if await cur.fetchone() is None:
            return
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='market_metrics'"
        )
        if await cur.fetchone() is None:
            await self._conn.execute(
                """
                CREATE TABLE market_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    numeric_value REAL NOT NULL,
                    recorded_at TEXT NOT NULL DEFAULT (datetime('now')),
                    api_source TEXT NOT NULL DEFAULT ''
                )
                """
            )
            await self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_market_metrics_recorded "
                "ON market_metrics(recorded_at DESC)"
            )
            await self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_market_metrics_name_recorded "
                "ON market_metrics(metric_name, recorded_at DESC)"
            )
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='synthesis_edges'"
        )
        if await cur.fetchone() is None:
            await self._conn.execute(
                """
                CREATE TABLE synthesis_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    knowledge_id INTEGER NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
                    metric_id INTEGER NOT NULL REFERENCES market_metrics(id) ON DELETE CASCADE,
                    causality_notes TEXT NOT NULL DEFAULT ''
                )
                """
            )
            await self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_synthesis_edges_knowledge "
                "ON synthesis_edges(knowledge_id)"
            )
            await self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_synthesis_edges_metric "
                "ON synthesis_edges(metric_id)"
            )
        await self._conn.commit()

    async def _ensure_knowledge_items_score_ttl_columns(self) -> None:
        """Add relevance_score, expires_at, tombstoned + indexes for upgraded DBs."""
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_items'"
        )
        if await cur.fetchone() is None:
            return
        cur = await self._conn.execute("PRAGMA table_info(knowledge_items)")
        cols = {str(row[1]) for row in await cur.fetchall()}
        if "relevance_score" not in cols:
            await self._conn.execute(
                "ALTER TABLE knowledge_items ADD COLUMN relevance_score REAL"
            )
        if "expires_at" not in cols:
            await self._conn.execute(
                "ALTER TABLE knowledge_items ADD COLUMN expires_at TEXT"
            )
        if "tombstoned" not in cols:
            await self._conn.execute(
                """
                ALTER TABLE knowledge_items ADD COLUMN tombstoned INTEGER NOT NULL DEFAULT 0
                """
            )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_items_ingested_at "
            "ON knowledge_items(ingested_at DESC)"
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_items_relevance "
            "ON knowledge_items(relevance_score)"
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_items_expires_at "
            "ON knowledge_items(expires_at)"
        )
        await self._conn.commit()

    async def _ensure_knowledge_item_embeddings_table(self) -> None:
        """Create knowledge_item_embeddings when upgrading older DBs."""
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_items'"
        )
        if await cur.fetchone() is None:
            return
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_item_embeddings'"
        )
        if await cur.fetchone() is not None:
            return
        await self._conn.executescript(
            """
            CREATE TABLE knowledge_item_embeddings (
                item_id INTEGER NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
                model TEXT NOT NULL,
                dim INTEGER NOT NULL,
                embedding BLOB NOT NULL,
                content_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (item_id, model)
            );
            CREATE INDEX idx_knowledge_embeddings_model
                ON knowledge_item_embeddings(model);
            """
        )
        await self._conn.commit()

    @staticmethod
    def _knowledge_fts_doc_select_expr(
        alias: str = "", *, include_triage: bool = False
    ) -> str:
        """SQL expression for indexed doc text (keep FTS triggers in sync)."""
        p = f"{alias}." if alias else ""
        base = (
            f"{p}content_excerpt || ' ' || {p}tags_json || ' ' || "
            f"COALESCE(json_extract({p}payload_json, '$.link'), '') || ' ' || "
            f"COALESCE(json_extract({p}payload_json, '$.title'), '') || ' ' || "
            f"COALESCE(json_extract({p}payload_json, '$.feed_url'), '')"
        )
        if not include_triage:
            return base
        return (
            f"{base} || ' ' || COALESCE({p}triage_primary_category, '') || ' ' || "
            f"COALESCE({p}triage_secondary_categories_json, '')"
        )

    def _knowledge_fts_ddl(self) -> str:
        return """
            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_items_fts USING fts5(
                doc,
                content='',
                tokenize='porter unicode61'
            );
            CREATE TRIGGER IF NOT EXISTS knowledge_items_ai AFTER INSERT ON knowledge_items BEGIN
                INSERT INTO knowledge_items_fts(rowid, doc)
                VALUES (
                    new.id,
                    new.content_excerpt || ' ' || new.tags_json || ' ' ||
                    COALESCE(json_extract(new.payload_json, '$.link'), '') || ' ' ||
                    COALESCE(json_extract(new.payload_json, '$.title'), '') || ' ' ||
                    COALESCE(json_extract(new.payload_json, '$.feed_url'), '')
                );
            END;
            CREATE TRIGGER IF NOT EXISTS knowledge_items_ad AFTER DELETE ON knowledge_items BEGIN
                INSERT INTO knowledge_items_fts(knowledge_items_fts, rowid)
                VALUES('delete', old.id);
            END;
            CREATE TRIGGER IF NOT EXISTS knowledge_items_au AFTER UPDATE ON knowledge_items BEGIN
                INSERT INTO knowledge_items_fts(knowledge_items_fts, rowid)
                VALUES('delete', old.id);
                INSERT INTO knowledge_items_fts(rowid, doc)
                VALUES (
                    new.id,
                    new.content_excerpt || ' ' || new.tags_json || ' ' ||
                    COALESCE(json_extract(new.payload_json, '$.link'), '') || ' ' ||
                    COALESCE(json_extract(new.payload_json, '$.title'), '') || ' ' ||
                    COALESCE(json_extract(new.payload_json, '$.feed_url'), '')
                );
            END;
            """

    async def _migrate_knowledge_fts_if_needed(self) -> None:
        """Add FTS + triggers + backfill when upgrading DBs that have items but no FTS."""
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_items'"
        )
        if await cur.fetchone() is None:
            return
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_items_fts'"
        )
        if await cur.fetchone() is not None:
            return
        await self._conn.executescript(self._knowledge_fts_ddl())
        expr = self._knowledge_fts_doc_select_expr(include_triage=False)
        await self._conn.execute(
            f"""
            INSERT INTO knowledge_items_fts(rowid, doc)
            SELECT id, {expr} FROM knowledge_items
            """
        )
        await self._conn.commit()

    async def _migrate_knowledge_fts_payload_doc_v1(self) -> None:
        """Rebuild FTS doc to include payload title/link/feed_url; refresh triggers."""
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT value FROM state WHERE key = ?",
            ("schema.knowledge_fts.payload_doc_v1",),
        )
        row = await cur.fetchone()
        if row and str(row[0]) == "1":
            return
        cur = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_items_fts'"
        )
        if await cur.fetchone() is None:
            return
        await self._conn.executescript(
            """
            DROP TRIGGER IF EXISTS knowledge_items_ai;
            DROP TRIGGER IF EXISTS knowledge_items_ad;
            DROP TRIGGER IF EXISTS knowledge_items_au;
            """
        )
        await self._conn.executescript(
            """
            CREATE TRIGGER knowledge_items_ai AFTER INSERT ON knowledge_items BEGIN
                INSERT INTO knowledge_items_fts(rowid, doc)
                VALUES (
                    new.id,
                    new.content_excerpt || ' ' || new.tags_json || ' ' ||
                    COALESCE(json_extract(new.payload_json, '$.link'), '') || ' ' ||
                    COALESCE(json_extract(new.payload_json, '$.title'), '') || ' ' ||
                    COALESCE(json_extract(new.payload_json, '$.feed_url'), '')
                );
            END;
            CREATE TRIGGER knowledge_items_ad AFTER DELETE ON knowledge_items BEGIN
                INSERT INTO knowledge_items_fts(knowledge_items_fts, rowid)
                VALUES('delete', old.id);
            END;
            CREATE TRIGGER knowledge_items_au AFTER UPDATE ON knowledge_items BEGIN
                INSERT INTO knowledge_items_fts(knowledge_items_fts, rowid)
                VALUES('delete', old.id);
                INSERT INTO knowledge_items_fts(rowid, doc)
                VALUES (
                    new.id,
                    new.content_excerpt || ' ' || new.tags_json || ' ' ||
                    COALESCE(json_extract(new.payload_json, '$.link'), '') || ' ' ||
                    COALESCE(json_extract(new.payload_json, '$.title'), '') || ' ' ||
                    COALESCE(json_extract(new.payload_json, '$.feed_url'), '')
                );
            END;
            """
        )
        # Contentless FTS5 does not support "DELETE FROM ..."; remove rows by rowid.
        cur = await self._conn.execute("SELECT id FROM knowledge_items")
        for row in await cur.fetchall():
            rid = int(row[0])
            await self._conn.execute(
                "INSERT INTO knowledge_items_fts(knowledge_items_fts, rowid) VALUES('delete', ?)",
                (rid,),
            )
        expr = self._knowledge_fts_doc_select_expr(include_triage=False)
        await self._conn.execute(
            f"""
            INSERT INTO knowledge_items_fts(rowid, doc)
            SELECT id, {expr} FROM knowledge_items
            """
        )
        await self._conn.execute(
            """
            INSERT INTO state(key, value) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            ("schema.knowledge_fts.payload_doc_v1", "1"),
        )
        await self._conn.commit()

    async def _next_sequence(self, session_id: int) -> int:
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT COALESCE(MAX(sequence), 0) + 1 FROM messages WHERE session_id = ?",
            (session_id,),
        )
        row = await cur.fetchone()
        return int(row[0]) if row else 1

    async def chain_head_uuid(self, session_id: int) -> str | None:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT uuid FROM messages
            WHERE session_id = ? AND tombstone = 0
            ORDER BY sequence DESC
            LIMIT 1
            """,
            (session_id,),
        )
        row = await cur.fetchone()
        return str(row[0]) if row else None

    async def persist_user(self, session_id: int, text: str) -> str:
        assert self._conn is not None
        mid = new_uuid()
        parent = await self.chain_head_uuid(session_id)
        seq = await self._next_sequence(session_id)
        await self._conn.execute(
            """
            INSERT INTO messages (uuid, session_id, parent_uuid, role, content_json, tombstone, sequence)
            VALUES (?, ?, ?, ?, ?, 0, ?)
            """,
            (mid, session_id, parent, ROLE_USER, pack_user_text(text), seq),
        )
        await self._conn.commit()
        return mid

    async def persist_assistant_begin(self, session_id: int, parent_uuid: str) -> str:
        assert self._conn is not None
        mid = new_uuid()
        seq = await self._next_sequence(session_id)
        await self._conn.execute(
            """
            INSERT INTO messages (uuid, session_id, parent_uuid, role, content_json, tombstone, sequence)
            VALUES (?, ?, ?, ?, ?, 0, ?)
            """,
            (mid, session_id, parent_uuid, ROLE_ASSISTANT, pack_assistant_text(""), seq),
        )
        await self._conn.commit()
        return mid

    async def flush_assistant_text(self, assistant_uuid: str, full_text: str) -> None:
        assert self._conn is not None
        await self._conn.execute(
            "UPDATE messages SET content_json = ? WHERE uuid = ?",
            (pack_assistant_text(full_text), assistant_uuid),
        )
        await self._conn.commit()

    async def persist_assistant_finalize(
        self,
        assistant_uuid: str,
        final_text: str,
        meta: dict[str, Any] | None = None,
        *,
        function_calls: list[dict[str, Any]] | None = None,
    ) -> None:
        assert self._conn is not None
        if function_calls:
            payload = pack_assistant_full(
                text=final_text,
                function_calls=function_calls,
                meta=meta,
            )
        elif meta:
            payload = pack_assistant_text(final_text, {"meta": meta})
        else:
            payload = pack_assistant_text(final_text)
        await self._conn.execute(
            "UPDATE messages SET content_json = ? WHERE uuid = ?",
            (payload, assistant_uuid),
        )
        await self._conn.commit()

    async def persist_tool_result(
        self,
        session_id: int,
        *,
        parent_assistant_uuid: str,
        name: str,
        tool_call_id: str | None,
        response: dict[str, Any],
    ) -> str:
        assert self._conn is not None
        mid = new_uuid()
        seq = await self._next_sequence(session_id)
        payload = {
            "parts": [
                {
                    "type": "function_response",
                    "name": name,
                    "response": response,
                    "tool_call_id": tool_call_id or "",
                }
            ]
        }
        await self._conn.execute(
            """
            INSERT INTO messages (uuid, session_id, parent_uuid, role, content_json, tombstone, sequence)
            VALUES (?, ?, ?, ?, ?, 0, ?)
            """,
            (
                mid,
                session_id,
                parent_assistant_uuid,
                ROLE_TOOL,
                json.dumps(payload, ensure_ascii=False),
                seq,
            ),
        )
        await self._conn.commit()
        await self._conn.commit()
        return mid

    async def record_web_tool_artifacts(
        self,
        session_id: int,
        tool_name: str,
        args: dict[str, Any],
        response: dict[str, Any],
    ) -> None:
        """Persist bounded rows for successful web_search / fetch_url_text tool results."""
        from ada.web_persistence import rows_for_web_tool

        rows = rows_for_web_tool(tool_name, args, response)
        if not rows:
            return
        assert self._conn is not None
        for url, kind, query_text, excerpt, sha in rows:
            await self._conn.execute(
                """
                INSERT INTO web_sources (
                    session_id, url, source_kind, query_text, content_excerpt, content_sha256
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, url, kind, query_text, excerpt, sha),
            )
        await self._conn.commit()

    async def list_web_sources(
        self, session_id: int, *, limit: int = 50
    ) -> list[dict[str, Any]]:
        assert self._conn is not None
        lim = max(1, min(limit, 200))
        cur = await self._conn.execute(
            """
            SELECT id, session_id, url, source_kind, query_text, content_excerpt,
                   content_sha256, fetched_at
            FROM web_sources
            WHERE session_id = ?
            ORDER BY datetime(fetched_at) DESC
            LIMIT ?
            """,
            (session_id, lim),
        )
        raw = await cur.fetchall()
        out: list[dict[str, Any]] = []
        for row in raw:
            out.append(
                {
                    "id": row[0],
                    "session_id": row[1],
                    "url": row[2],
                    "source_kind": row[3],
                    "query_text": row[4],
                    "content_excerpt": row[5],
                    "content_sha256": row[6],
                    "fetched_at": row[7],
                }
            )
        return out

    async def record_usage(
        self,
        session_id: int,
        *,
        model: str | None,
        input_tokens: int | None,
        output_tokens: int | None,
        usage_extras_json: str | None = None,
    ) -> None:
        if input_tokens is None and output_tokens is None:
            return
        assert self._conn is not None
        await self._conn.execute(
            """
            INSERT INTO usage_ledger (session_id, model, input_tokens, output_tokens)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, model, input_tokens, output_tokens),
        )
        await self._conn.commit()
        # Per-request counts from the API (multi-leg turns overlap on prompt — do not sum naively).
        if input_tokens is not None:
            await self.state_set("session.last_leg_input_tokens", str(input_tokens))
        if output_tokens is not None:
            await self.state_set("session.last_leg_output_tokens", str(output_tokens))
        if usage_extras_json:
            await self.state_set("session.last_usage_extras_json", usage_extras_json)

    async def get_session_token_usage(self, session_id: int) -> dict[str, Any]:
        """
        Sum input/output token counts from usage_ledger for this session.
        Operational upper bound only — multi-leg turns may overlap prompt context in billing.
        """
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT COALESCE(SUM(input_tokens), 0), COALESCE(SUM(output_tokens), 0)
            FROM usage_ledger
            WHERE session_id = ?
            """,
            (session_id,),
        )
        row = await cur.fetchone()
        if not row:
            return {"input_tokens": 0, "output_tokens": 0, "total": 0}
        inp, out = int(row[0]), int(row[1])
        return {"input_tokens": inp, "output_tokens": out, "total": inp + out}

    async def get_global_usage_token_totals_utc(self) -> dict[str, int]:
        """
        Global sums from usage_ledger for the current UTC calendar day and month.
        Uses date(recorded_at) and strftime('%Y-%m', recorded_at) in UTC-aligned stored timestamps.
        Same caveat as per-session sums: ledger rows are per model leg; totals are an operational bound.
        """
        assert self._conn is not None
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        day = now.strftime("%Y-%m-%d")
        ym = now.strftime("%Y-%m")
        cur = await self._conn.execute(
            """
            SELECT COALESCE(SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)), 0)
            FROM usage_ledger
            WHERE date(recorded_at) = date(?)
            """,
            (day,),
        )
        row = await cur.fetchone()
        day_total = int(row[0]) if row else 0
        cur = await self._conn.execute(
            """
            SELECT COALESCE(SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)), 0)
            FROM usage_ledger
            WHERE strftime('%Y-%m', recorded_at) = ?
            """,
            (ym,),
        )
        row = await cur.fetchone()
        month_total = int(row[0]) if row else 0
        return {"day_total": day_total, "month_total": month_total}

    async def rewire_parents_after_tombstone(
        self, session_id: int, tombstoned_uuids: Sequence[str]
    ) -> None:
        """
        Point live rows whose parent was tombstoned at the nearest prior live message.
        """
        if not tombstoned_uuids:
            return
        assert self._conn is not None
        tomb = set(tombstoned_uuids)
        cur = await self._conn.execute(
            """
            SELECT uuid, sequence, parent_uuid FROM messages
            WHERE session_id = ? AND tombstone = 0
            ORDER BY sequence ASC
            """,
            (session_id,),
        )
        rows = await cur.fetchall()
        for uuid_str, seq, parent_uuid in rows:
            if not parent_uuid or parent_uuid not in tomb:
                continue
            cur2 = await self._conn.execute(
                """
                SELECT uuid FROM messages
                WHERE session_id = ? AND tombstone = 0 AND sequence < ?
                ORDER BY sequence DESC LIMIT 1
                """,
                (session_id, seq),
            )
            row2 = await cur2.fetchone()
            new_parent = str(row2[0]) if row2 else None
            await self._conn.execute(
                "UPDATE messages SET parent_uuid = ? WHERE uuid = ?",
                (new_parent, uuid_str),
            )
        await self._conn.commit()

    async def tombstone(
        self,
        uuids: Sequence[str],
        session_id: int,
        *,
        rewire_orphans: bool = True,
    ) -> None:
        if not uuids:
            return
        assert self._conn is not None
        placeholders = ",".join("?" for _ in uuids)
        await self._conn.execute(
            f"""
            UPDATE messages SET tombstone = 1
            WHERE session_id = ? AND uuid IN ({placeholders})
            """,
            (session_id, *uuids),
        )
        await self._conn.commit()
        if rewire_orphans:
            await self.rewire_parents_after_tombstone(session_id, uuids)

    async def load_chain_for_api(self, session_id: int) -> list[dict[str, Any]]:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT role, content_json, sequence FROM messages
            WHERE session_id = ? AND tombstone = 0 AND role != ?
            ORDER BY sequence ASC
            """,
            (session_id, ROLE_SYSTEM),
        )
        rows = await cur.fetchall()
        out: list[dict[str, Any]] = []
        for role, content_json, sequence in rows:
            payload = json.loads(content_json)
            out.append({"role": role, "sequence": int(sequence), **payload})
        return out

    async def state_set(self, key: str, value: str) -> None:
        assert self._conn is not None
        await self._conn.execute(
            "INSERT INTO state(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await self._conn.commit()

    async def state_get(self, key: str) -> str | None:
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT value FROM state WHERE key = ?", (key,)
        )
        row = await cur.fetchone()
        return str(row[0]) if row else None

    async def ensure_profile_identity(
        self,
        *,
        profile_id: str,
        profile_data_root: str,
        profile_fingerprint: str,
    ) -> None:
        """
        Bind the SQLite file to a single runtime profile. First writer initializes
        profile keys; subsequent writers must match exactly.
        """
        assert self._conn is not None
        expected = {
            "profile.id": str(profile_id),
            "profile.data_root": str(profile_data_root),
            "profile.fingerprint": str(profile_fingerprint),
        }
        for key, value in expected.items():
            cur = await self._conn.execute("SELECT value FROM state WHERE key = ?", (key,))
            row = await cur.fetchone()
            if row is None:
                await self._conn.execute(
                    "INSERT INTO state(key, value) VALUES(?, ?)",
                    (key, value),
                )
                continue
            current = str(row[0])
            if current != value:
                raise ValueError(
                    f"profile mismatch for {key}: db={current!r} runtime={value!r}"
                )
        await self._conn.commit()

    async def upsert_approval_record(
        self,
        *,
        artifact_type: str,
        artifact_ref: str,
        status: str,
        requested_by: str = "",
        approved_by: str = "",
        reason: str = "",
        payload_json: dict[str, Any] | None = None,
        set_decided: bool = False,
    ) -> None:
        assert self._conn is not None
        if status not in ("requested", "approved", "rejected", "expired"):
            raise ValueError(f"invalid approval status: {status!r}")
        payload = json.dumps(payload_json or {}, ensure_ascii=False)
        await self._conn.execute(
            """
            INSERT INTO approval_records (
                artifact_type, artifact_ref, status, requested_by, approved_by, reason, payload_json, requested_at, updated_at, decided_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), CASE WHEN ? THEN datetime('now') ELSE NULL END)
            ON CONFLICT(artifact_type, artifact_ref) DO UPDATE SET
                status = excluded.status,
                requested_by = excluded.requested_by,
                approved_by = excluded.approved_by,
                reason = excluded.reason,
                payload_json = excluded.payload_json,
                updated_at = datetime('now'),
                decided_at = CASE WHEN excluded.status IN ('approved', 'rejected', 'expired') THEN datetime('now') ELSE approval_records.decided_at END
            """,
            (
                artifact_type,
                artifact_ref,
                status,
                requested_by,
                approved_by,
                reason,
                payload,
                1 if set_decided else 0,
            ),
        )
        await self._conn.commit()

    async def get_approval_record(
        self, *, artifact_type: str, artifact_ref: str
    ) -> dict[str, Any] | None:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT id, artifact_type, artifact_ref, status, requested_by, approved_by, reason,
                   payload_json, requested_at, decided_at, updated_at
            FROM approval_records
            WHERE artifact_type = ? AND artifact_ref = ?
            LIMIT 1
            """,
            (artifact_type, artifact_ref),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        try:
            payload = json.loads(str(row[7] or "{}"))
            if not isinstance(payload, dict):
                payload = {}
        except json.JSONDecodeError:
            payload = {}
        return {
            "id": int(row[0]),
            "artifact_type": str(row[1]),
            "artifact_ref": str(row[2]),
            "status": str(row[3]),
            "requested_by": str(row[4] or ""),
            "approved_by": str(row[5] or ""),
            "reason": str(row[6] or ""),
            "payload_json": payload,
            "requested_at": str(row[8] or ""),
            "decided_at": str(row[9] or "") if row[9] is not None else None,
            "updated_at": str(row[10] or ""),
        }

    async def ensure_analytics_provider(
        self,
        *,
        provider: str,
        property_ref: str,
        account_ref: str = "",
        config_json: dict[str, Any] | None = None,
    ) -> int:
        assert self._conn is not None
        cfg = json.dumps(config_json or {}, ensure_ascii=False)
        try:
            cur = await self._conn.execute(
                """
                INSERT INTO analytics_providers(provider, account_ref, property_ref, config_json)
                VALUES (?, ?, ?, ?)
                """,
                (provider, account_ref, property_ref, cfg),
            )
            await self._conn.commit()
            return int(cur.lastrowid)
        except sqlite3.IntegrityError:
            cur = await self._conn.execute(
                """
                SELECT id FROM analytics_providers WHERE provider = ? AND property_ref = ? LIMIT 1
                """,
                (provider, property_ref),
            )
            row = await cur.fetchone()
            if row is None:
                raise
            return int(row[0])

    async def upsert_analytics_snapshot(
        self,
        *,
        provider_id: int,
        ingest_job_id: int | None,
        window_start: str,
        window_end: str,
        request_hash: str,
        response_version: str,
        row_count: int,
    ) -> int:
        assert self._conn is not None
        try:
            cur = await self._conn.execute(
                """
                INSERT INTO analytics_snapshots(
                    provider_id, ingest_job_id, window_start, window_end, request_hash, response_version, row_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    provider_id,
                    ingest_job_id,
                    window_start,
                    window_end,
                    request_hash,
                    response_version,
                    row_count,
                ),
            )
            await self._conn.commit()
            return int(cur.lastrowid)
        except sqlite3.IntegrityError:
            cur = await self._conn.execute(
                """
                SELECT id FROM analytics_snapshots WHERE provider_id = ? AND request_hash = ? LIMIT 1
                """,
                (provider_id, request_hash),
            )
            row = await cur.fetchone()
            if row is None:
                raise
            return int(row[0])

    async def upsert_gsc_search_analytics_row(
        self,
        *,
        provider_id: int,
        snapshot_id: int,
        data_date: str,
        query: str,
        page: str,
        country: str,
        device: str,
        clicks: float,
        impressions: float,
        ctr: float,
        position: float,
        row_hash: str,
    ) -> None:
        assert self._conn is not None
        await self._conn.execute(
            """
            INSERT INTO gsc_search_analytics_rows(
                provider_id, snapshot_id, data_date, query, page, country, device,
                clicks, impressions, ctr, position, row_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(provider_id, data_date, query, page, country, device)
            DO UPDATE SET
                snapshot_id = excluded.snapshot_id,
                clicks = excluded.clicks,
                impressions = excluded.impressions,
                ctr = excluded.ctr,
                position = excluded.position,
                row_hash = excluded.row_hash
            """,
            (
                provider_id,
                snapshot_id,
                data_date,
                query,
                page,
                country,
                device,
                clicks,
                impressions,
                ctr,
                position,
                row_hash,
            ),
        )

    @staticmethod
    def _validate_iso_date(value: str, *, field: str) -> str:
        s = str(value).strip()
        try:
            datetime.strptime(s, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"{field} must be YYYY-MM-DD") from e
        return s

    @staticmethod
    def _validate_gsc_read_limit(limit: int, *, max_limit: int = 200) -> int:
        lim = int(limit)
        if lim < 1 or lim > max_limit:
            raise ValueError(f"limit must be between 1 and {max_limit}")
        return lim

    async def _gsc_tables_present(self) -> bool:
        assert self._conn is not None
        for tbl in ("analytics_providers", "gsc_search_analytics_rows"):
            cur = await self._conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (tbl,),
            )
            if await cur.fetchone() is None:
                return False
        return True

    async def list_gsc_top_queries(
        self, *, site: str, start_date: str, end_date: str, limit: int
    ) -> list[dict[str, Any]]:
        if not await self._gsc_tables_present():
            raise ValueError("GSC tables are not available")
        assert self._conn is not None
        site_s = str(site).strip()
        if not site_s:
            raise ValueError("site is required")
        start_s = self._validate_iso_date(start_date, field="start_date")
        end_s = self._validate_iso_date(end_date, field="end_date")
        if start_s > end_s:
            raise ValueError("start_date must be <= end_date")
        lim = self._validate_gsc_read_limit(limit)
        cur = await self._conn.execute(
            """
            SELECT
                r.query,
                SUM(r.clicks) AS clicks,
                SUM(r.impressions) AS impressions,
                CASE
                    WHEN SUM(r.impressions) > 0 THEN SUM(r.clicks) / SUM(r.impressions)
                    ELSE 0
                END AS ctr,
                CASE
                    WHEN SUM(r.impressions) > 0 THEN SUM(r.position * r.impressions) / SUM(r.impressions)
                    ELSE 0
                END AS avg_position
            FROM gsc_search_analytics_rows r
            JOIN analytics_providers p ON p.id = r.provider_id
            WHERE p.provider = 'gsc'
              AND p.property_ref = ?
              AND r.data_date >= ?
              AND r.data_date <= ?
              AND TRIM(r.query) <> ''
            GROUP BY r.query
            ORDER BY impressions DESC, avg_position ASC, ctr ASC, r.query ASC
            LIMIT ?
            """,
            (site_s, start_s, end_s, lim),
        )
        rows = await cur.fetchall()
        return [
            {
                "query": str(r[0]),
                "clicks": float(r[1] or 0.0),
                "impressions": float(r[2] or 0.0),
                "ctr": float(r[3] or 0.0),
                "avg_position": float(r[4] or 0.0),
            }
            for r in rows
        ]

    async def list_gsc_top_queries_safe(
        self, *, site: str, start_date: str, end_date: str, limit: int
    ) -> dict[str, Any]:
        if not await self._gsc_tables_present():
            return {"tables_present": False, "rows": []}
        rows = await self.list_gsc_top_queries(
            site=site, start_date=start_date, end_date=end_date, limit=limit
        )
        return {"tables_present": True, "rows": rows}

    async def list_gsc_top_pages(
        self, *, site: str, start_date: str, end_date: str, limit: int
    ) -> list[dict[str, Any]]:
        if not await self._gsc_tables_present():
            raise ValueError("GSC tables are not available")
        assert self._conn is not None
        site_s = str(site).strip()
        if not site_s:
            raise ValueError("site is required")
        start_s = self._validate_iso_date(start_date, field="start_date")
        end_s = self._validate_iso_date(end_date, field="end_date")
        if start_s > end_s:
            raise ValueError("start_date must be <= end_date")
        lim = self._validate_gsc_read_limit(limit)
        cur = await self._conn.execute(
            """
            SELECT
                r.page,
                SUM(r.clicks) AS clicks,
                SUM(r.impressions) AS impressions,
                CASE
                    WHEN SUM(r.impressions) > 0 THEN SUM(r.clicks) / SUM(r.impressions)
                    ELSE 0
                END AS ctr,
                CASE
                    WHEN SUM(r.impressions) > 0 THEN SUM(r.position * r.impressions) / SUM(r.impressions)
                    ELSE 0
                END AS avg_position
            FROM gsc_search_analytics_rows r
            JOIN analytics_providers p ON p.id = r.provider_id
            WHERE p.provider = 'gsc'
              AND p.property_ref = ?
              AND r.data_date >= ?
              AND r.data_date <= ?
              AND TRIM(r.page) <> ''
            GROUP BY r.page
            ORDER BY impressions DESC, avg_position ASC, ctr ASC, r.page ASC
            LIMIT ?
            """,
            (site_s, start_s, end_s, lim),
        )
        rows = await cur.fetchall()
        return [
            {
                "page": str(r[0]),
                "clicks": float(r[1] or 0.0),
                "impressions": float(r[2] or 0.0),
                "ctr": float(r[3] or 0.0),
                "avg_position": float(r[4] or 0.0),
            }
            for r in rows
        ]

    async def list_gsc_quick_wins(
        self, *, site: str, start_date: str, end_date: str, limit: int
    ) -> list[dict[str, Any]]:
        if not await self._gsc_tables_present():
            raise ValueError("GSC tables are not available")
        assert self._conn is not None
        site_s = str(site).strip()
        if not site_s:
            raise ValueError("site is required")
        start_s = self._validate_iso_date(start_date, field="start_date")
        end_s = self._validate_iso_date(end_date, field="end_date")
        if start_s > end_s:
            raise ValueError("start_date must be <= end_date")
        lim = self._validate_gsc_read_limit(limit)
        cur = await self._conn.execute(
            """
            WITH query_page AS (
                SELECT
                    r.query AS query,
                    r.page AS page,
                    SUM(r.clicks) AS clicks,
                    SUM(r.impressions) AS impressions
                FROM gsc_search_analytics_rows r
                JOIN analytics_providers p ON p.id = r.provider_id
                WHERE p.provider = 'gsc'
                  AND p.property_ref = ?
                  AND r.data_date >= ?
                  AND r.data_date <= ?
                  AND TRIM(r.query) <> ''
                GROUP BY r.query, r.page
            ),
            ranked AS (
                SELECT
                    query,
                    page,
                    clicks,
                    impressions,
                    ROW_NUMBER() OVER (
                        PARTITION BY query
                        ORDER BY impressions DESC, clicks DESC, page ASC
                    ) AS rn
                FROM query_page
            ),
            query_rollup AS (
                SELECT
                    r.query AS query,
                    SUM(r.clicks) AS clicks,
                    SUM(r.impressions) AS impressions,
                    CASE
                        WHEN SUM(r.impressions) > 0 THEN SUM(r.clicks) / SUM(r.impressions)
                        ELSE 0
                    END AS ctr,
                    CASE
                        WHEN SUM(r.impressions) > 0 THEN SUM(r.position * r.impressions) / SUM(r.impressions)
                        ELSE 0
                    END AS avg_position
                FROM gsc_search_analytics_rows r
                JOIN analytics_providers p ON p.id = r.provider_id
                WHERE p.provider = 'gsc'
                  AND p.property_ref = ?
                  AND r.data_date >= ?
                  AND r.data_date <= ?
                  AND TRIM(r.query) <> ''
                GROUP BY r.query
            )
            SELECT
                q.query,
                COALESCE(r.page, '') AS page,
                q.clicks,
                q.impressions,
                q.ctr,
                q.avg_position
            FROM query_rollup q
            LEFT JOIN ranked r
              ON r.query = q.query AND r.rn = 1
            WHERE q.impressions > 0
              AND q.avg_position BETWEEN 6.0 AND 20.0
            ORDER BY q.impressions DESC, q.ctr ASC, q.avg_position ASC, q.query ASC
            LIMIT ?
            """,
            (site_s, start_s, end_s, site_s, start_s, end_s, lim),
        )
        rows = await cur.fetchall()
        return [
            {
                "query": str(r[0]),
                "page": str(r[1] or ""),
                "clicks": float(r[2] or 0.0),
                "impressions": float(r[3] or 0.0),
                "ctr": float(r[4] or 0.0),
                "avg_position": float(r[5] or 0.0),
            }
            for r in rows
        ]

    async def list_gsc_content_gaps(
        self, *, site: str, start_date: str, end_date: str, limit: int
    ) -> list[dict[str, Any]]:
        if not await self._gsc_tables_present():
            raise ValueError("GSC tables are not available")
        assert self._conn is not None
        site_s = str(site).strip()
        if not site_s:
            raise ValueError("site is required")
        start_s = self._validate_iso_date(start_date, field="start_date")
        end_s = self._validate_iso_date(end_date, field="end_date")
        if start_s > end_s:
            raise ValueError("start_date must be <= end_date")
        lim = self._validate_gsc_read_limit(limit)
        cur = await self._conn.execute(
            """
            WITH query_page AS (
                SELECT
                    r.query AS query,
                    r.page AS page,
                    SUM(r.clicks) AS clicks,
                    SUM(r.impressions) AS impressions
                FROM gsc_search_analytics_rows r
                JOIN analytics_providers p ON p.id = r.provider_id
                WHERE p.provider = 'gsc'
                  AND p.property_ref = ?
                  AND r.data_date >= ?
                  AND r.data_date <= ?
                  AND TRIM(r.query) <> ''
                GROUP BY r.query, r.page
            ),
            ranked AS (
                SELECT
                    query,
                    page,
                    clicks,
                    impressions,
                    ROW_NUMBER() OVER (
                        PARTITION BY query
                        ORDER BY impressions DESC, clicks DESC, page ASC
                    ) AS rn
                FROM query_page
            ),
            totals AS (
                SELECT
                    query,
                    SUM(impressions) AS total_impressions
                FROM query_page
                GROUP BY query
            )
            SELECT
                t.query,
                COALESCE(r.page, '') AS top_page,
                t.total_impressions,
                COALESCE(r.impressions, 0) AS top_page_impressions,
                CASE
                    WHEN t.total_impressions > 0 THEN COALESCE(r.impressions, 0) / t.total_impressions
                    ELSE 0
                END AS top_page_share
            FROM totals t
            LEFT JOIN ranked r
              ON r.query = t.query AND r.rn = 1
            WHERE t.total_impressions > 0
              AND (
                TRIM(COALESCE(r.page, '')) = ''
                OR (CASE
                    WHEN t.total_impressions > 0 THEN COALESCE(r.impressions, 0) / t.total_impressions
                    ELSE 0
                END) < 0.60
              )
            ORDER BY t.total_impressions DESC, top_page_share ASC, t.query ASC
            LIMIT ?
            """,
            (site_s, start_s, end_s, lim),
        )
        rows = await cur.fetchall()
        return [
            {
                "query": str(r[0]),
                "top_page": str(r[1] or ""),
                "total_impressions": float(r[2] or 0.0),
                "top_page_impressions": float(r[3] or 0.0),
                "top_page_share": float(r[4] or 0.0),
            }
            for r in rows
        ]

    async def list_gsc_page_fixes(
        self, *, site: str, start_date: str, end_date: str, limit: int
    ) -> list[dict[str, Any]]:
        if not await self._gsc_tables_present():
            raise ValueError("GSC tables are not available")
        assert self._conn is not None
        site_s = str(site).strip()
        if not site_s:
            raise ValueError("site is required")
        start_s = self._validate_iso_date(start_date, field="start_date")
        end_s = self._validate_iso_date(end_date, field="end_date")
        if start_s > end_s:
            raise ValueError("start_date must be <= end_date")
        lim = self._validate_gsc_read_limit(limit)
        cur = await self._conn.execute(
            """
            SELECT
                r.page,
                SUM(r.clicks) AS clicks,
                SUM(r.impressions) AS impressions,
                CASE
                    WHEN SUM(r.impressions) > 0 THEN SUM(r.clicks) / SUM(r.impressions)
                    ELSE 0
                END AS ctr,
                CASE
                    WHEN SUM(r.impressions) > 0 THEN SUM(r.position * r.impressions) / SUM(r.impressions)
                    ELSE 0
                END AS avg_position
            FROM gsc_search_analytics_rows r
            JOIN analytics_providers p ON p.id = r.provider_id
            WHERE p.provider = 'gsc'
              AND p.property_ref = ?
              AND r.data_date >= ?
              AND r.data_date <= ?
              AND TRIM(r.page) <> ''
            GROUP BY r.page
            HAVING impressions > 0
            ORDER BY impressions DESC, ctr ASC, avg_position ASC, r.page ASC
            LIMIT ?
            """,
            (site_s, start_s, end_s, lim),
        )
        rows = await cur.fetchall()
        return [
            {
                "page": str(r[0]),
                "clicks": float(r[1] or 0.0),
                "impressions": float(r[2] or 0.0),
                "ctr": float(r[3] or 0.0),
                "avg_position": float(r[4] or 0.0),
            }
            for r in rows
        ]

    async def get_task_plan_json(self, task_id: int) -> str:
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT plan_json FROM tasks WHERE id = ?", (task_id,)
        )
        row = await cur.fetchone()
        if not row:
            raise LookupError(f"no task with id={task_id}")
        return str(row[0])

    async def set_task_plan_json(self, task_id: int, plan_json: str) -> None:
        assert self._conn is not None
        try:
            json.loads(plan_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"plan_json is not valid JSON: {e}") from e
        cur = await self._conn.execute(
            """
            UPDATE tasks
            SET plan_json = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (plan_json, task_id),
        )
        if cur.rowcount == 0:
            raise LookupError(f"no task with id={task_id}")
        await self._conn.commit()

    async def update_task(
        self,
        task_id: int,
        *,
        status: str | None = None,
        current_output: str | None = None,
    ) -> None:
        assert self._conn is not None
        sets: list[str] = []
        args: list[Any] = []
        if status is not None:
            sets.append("status = ?")
            args.append(status)
        if current_output is not None:
            sets.append("current_output = ?")
            args.append(current_output)
        if not sets:
            return
        sets.append("updated_at = datetime('now')")
        args.append(task_id)
        await self._conn.execute(
            f"UPDATE tasks SET {', '.join(sets)} WHERE id = ?", args
        )
        await self._conn.commit()

    async def insert_task(
        self,
        goal: str,
        status: str = "pending",
        *,
        task_kind: TaskKind = TASK_KIND_GOAL,
        mission_id: int | None = None,
    ) -> int:
        if task_kind not in ("chat", "goal", "system"):
            raise ValueError(f"invalid task_kind: {task_kind!r}")
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            INSERT INTO tasks (goal, status, current_output, task_kind, mission_id)
            VALUES (?, ?, '', ?, ?)
            """,
            (goal, status, task_kind, mission_id),
        )
        await self._conn.commit()
        return int(cur.lastrowid)

    async def create_mission(
        self,
        slug: str,
        title: str,
        *,
        niche: str | None = None,
        topic: str | None = None,
        defaults_json: str | dict[str, Any] | None = None,
        brief_md: str = "",
        brief_md_path: str | None = None,
        schedule_hint_json: str | dict[str, Any] | None = None,
    ) -> int:
        assert self._conn is not None
        if defaults_json is None:
            defaults_s = "{}"
        elif isinstance(defaults_json, dict):
            defaults_s = json.dumps(defaults_json, ensure_ascii=False)
        else:
            defaults_s = defaults_json
        if schedule_hint_json is None:
            schedule_s: str | None = None
        elif isinstance(schedule_hint_json, dict):
            schedule_s = json.dumps(schedule_hint_json, ensure_ascii=False)
        else:
            schedule_s = schedule_hint_json
        cur = await self._conn.execute(
            """
            INSERT INTO missions (
                slug, title, niche, topic, defaults_json, brief_md,
                brief_md_path, schedule_hint_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                slug,
                title,
                niche,
                topic,
                defaults_s,
                brief_md,
                brief_md_path,
                schedule_s,
            ),
        )
        await self._conn.commit()
        return int(cur.lastrowid)

    async def get_mission_by_slug(self, slug: str) -> dict[str, Any] | None:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT id, slug, title, niche, topic, defaults_json, brief_md,
                   brief_md_path, schedule_hint_json, created_at, updated_at
            FROM missions WHERE slug = ? LIMIT 1
            """,
            (slug,),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        return {
            "id": int(row[0]),
            "slug": str(row[1]),
            "title": str(row[2]),
            "niche": row[3],
            "topic": row[4],
            "defaults_json": json.loads(str(row[5] or "{}")),
            "brief_md": str(row[6] or ""),
            "brief_md_path": row[7],
            "schedule_hint_json": json.loads(row[8])
            if row[8] not in (None, "")
            else None,
            "created_at": str(row[9]),
            "updated_at": str(row[10]),
        }

    async def update_mission_defaults_json(
        self,
        slug: str,
        patch: dict[str, Any],
        *,
        force: bool = False,
    ) -> dict[str, Any]:
        """Merge ``patch`` into ``missions.defaults_json``; skip existing keys unless ``force``."""
        assert self._conn is not None
        row = await self.get_mission_by_slug(slug)
        if row is None:
            raise LookupError(f"no mission with slug {slug!r}")
        raw = row.get("defaults_json")
        current: dict[str, Any] = dict(raw) if isinstance(raw, dict) else {}
        merged = dict(current)
        for k, v in patch.items():
            if k in merged and not force:
                continue
            merged[k] = v
        await self._conn.execute(
            """
            UPDATE missions
            SET defaults_json = ?, updated_at = datetime('now')
            WHERE slug = ?
            """,
            (json.dumps(merged, ensure_ascii=False), slug),
        )
        await self._conn.commit()
        return merged

    async def get_mission_by_id(self, mission_id: int) -> dict[str, Any] | None:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT id, slug, title, niche, topic, defaults_json, brief_md,
                   brief_md_path, schedule_hint_json, created_at, updated_at
            FROM missions WHERE id = ? LIMIT 1
            """,
            (int(mission_id),),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        return {
            "id": int(row[0]),
            "slug": str(row[1]),
            "title": str(row[2]),
            "niche": row[3],
            "topic": row[4],
            "defaults_json": json.loads(str(row[5] or "{}")),
            "brief_md": str(row[6] or ""),
            "brief_md_path": row[7],
            "schedule_hint_json": json.loads(row[8])
            if row[8] not in (None, "")
            else None,
            "created_at": str(row[9]),
            "updated_at": str(row[10]),
        }

    async def update_mission_meta(
        self,
        slug: str,
        *,
        title: str | None = None,
        brief_md: str | None = None,
        schedule_hint_json: dict[str, Any] | None = None,
    ) -> None:
        assert self._conn is not None
        sets: list[str] = ["updated_at = datetime('now')"]
        args: list[Any] = []
        if title is not None and title.strip():
            sets.append("title = ?")
            args.append(title.strip())
        if brief_md is not None:
            sets.append("brief_md = ?")
            args.append(brief_md)
        if schedule_hint_json is not None:
            sets.append("schedule_hint_json = ?")
            args.append(json.dumps(schedule_hint_json, ensure_ascii=False))
        if len(sets) == 1:
            return
        args.append(slug)
        await self._conn.execute(
            f"UPDATE missions SET {', '.join(sets)} WHERE slug = ?",
            args,
        )
        await self._conn.commit()

    async def rename_mission_slug(self, old_slug: str, new_slug: str) -> None:
        """Rename mission slug when ``new_slug`` is not already taken."""
        assert self._conn is not None
        old = old_slug.strip()
        new = new_slug.strip()
        if not old or not new or old == new:
            return
        cur = await self._conn.execute(
            "SELECT id FROM missions WHERE slug = ? LIMIT 1",
            (new,),
        )
        if await cur.fetchone() is not None:
            raise ValueError(f"mission slug already exists: {new!r}")
        cur = await self._conn.execute(
            "SELECT id FROM missions WHERE slug = ? LIMIT 1",
            (old,),
        )
        if await cur.fetchone() is None:
            return
        await self._conn.execute(
            """
            UPDATE missions
            SET slug = ?, updated_at = datetime('now')
            WHERE slug = ?
            """,
            (new, old),
        )
        await self._conn.commit()

    async def list_missions(self, *, limit: int = 50) -> list[dict[str, Any]]:
        assert self._conn is not None
        limit = max(1, min(int(limit), 500))
        cur = await self._conn.execute(
            """
            SELECT id, slug, title, niche, topic, created_at, updated_at
            FROM missions
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cur.fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            out.append(
                {
                    "id": int(row[0]),
                    "slug": str(row[1]),
                    "title": str(row[2]),
                    "niche": row[3],
                    "topic": row[4],
                    "created_at": str(row[5]),
                    "updated_at": str(row[6]),
                }
            )
        return out

    async def attach_task_to_mission(
        self, task_id: int, mission_id: int | None
    ) -> None:
        assert self._conn is not None
        await self._conn.execute(
            """
            UPDATE tasks SET mission_id = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (mission_id, task_id),
        )
        await self._conn.commit()

    async def fetch_pending_task(
        self,
    ) -> tuple[int, str, int | None, str | None] | None:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT t.id, t.goal, t.mission_id, m.slug
            FROM tasks t
            LEFT JOIN missions m ON m.id = t.mission_id
            WHERE t.status = 'pending' AND t.task_kind = ?
            ORDER BY t.id ASC
            LIMIT 1
            """,
            (TASK_KIND_GOAL,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        mid = row[2]
        slug = row[3]
        return (
            int(row[0]),
            str(row[1]),
            int(mid) if mid is not None else None,
            str(slug) if slug is not None else None,
        )

    async def latest_cli_session_task_id(self) -> int | None:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT id FROM tasks
            WHERE task_kind = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (TASK_KIND_CHAT,),
        )
        row = await cur.fetchone()
        return int(row[0]) if row else None

    async def list_goal_tasks(
        self,
        *,
        limit: int = 50,
        status: str | None = None,
        mission_slug: str | None = None,
    ) -> list[dict[str, Any]]:
        assert self._conn is not None
        limit = max(1, min(limit, 500))
        if mission_slug is not None:
            slug = mission_slug.strip()
            if status is not None:
                cur = await self._conn.execute(
                    """
                    SELECT t.id, t.goal, t.status, t.plan_json, t.created_at, t.updated_at,
                           t.mission_id, m.slug
                    FROM tasks t
                    INNER JOIN missions m ON m.id = t.mission_id AND m.slug = ?
                    WHERE t.task_kind = ? AND t.status = ?
                    ORDER BY t.id DESC
                    LIMIT ?
                    """,
                    (slug, TASK_KIND_GOAL, status, limit),
                )
            else:
                cur = await self._conn.execute(
                    """
                    SELECT t.id, t.goal, t.status, t.plan_json, t.created_at, t.updated_at,
                           t.mission_id, m.slug
                    FROM tasks t
                    INNER JOIN missions m ON m.id = t.mission_id AND m.slug = ?
                    WHERE t.task_kind = ?
                    ORDER BY t.id DESC
                    LIMIT ?
                    """,
                    (slug, TASK_KIND_GOAL, limit),
                )
        elif status is not None:
            cur = await self._conn.execute(
                """
                SELECT t.id, t.goal, t.status, t.plan_json, t.created_at, t.updated_at,
                       t.mission_id, m.slug
                FROM tasks t
                LEFT JOIN missions m ON m.id = t.mission_id
                WHERE t.task_kind = ? AND t.status = ?
                ORDER BY t.id DESC
                LIMIT ?
                """,
                (TASK_KIND_GOAL, status, limit),
            )
        else:
            cur = await self._conn.execute(
                """
                SELECT t.id, t.goal, t.status, t.plan_json, t.created_at, t.updated_at,
                       t.mission_id, m.slug
                FROM tasks t
                LEFT JOIN missions m ON m.id = t.mission_id
                WHERE t.task_kind = ?
                ORDER BY t.id DESC
                LIMIT ?
                """,
                (TASK_KIND_GOAL, limit),
            )
        rows = await cur.fetchall()
        return self._goal_task_rows_to_dicts(rows)

    @staticmethod
    def _goal_task_rows_to_dicts(
        rows: list[Any],
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for row in rows:
            mid = row[6]
            slug = row[7]
            out.append(
                {
                    "id": int(row[0]),
                    "goal": str(row[1]),
                    "status": str(row[2]),
                    "plan_json": str(row[3]),
                    "created_at": str(row[4]),
                    "updated_at": str(row[5]),
                    "mission_id": int(mid) if mid is not None else None,
                    "mission_slug": str(slug) if slug is not None else None,
                }
            )
        return out

    async def get_goal_task(self, task_id: int) -> dict[str, Any]:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT t.id, t.goal, t.status, t.plan_json, t.current_output, t.task_kind,
                   t.created_at, t.updated_at, t.mission_id, m.slug
            FROM tasks t
            LEFT JOIN missions m ON m.id = t.mission_id
            WHERE t.id = ?
            """,
            (task_id,),
        )
        row = await cur.fetchone()
        if not row:
            raise LookupError(f"no task with id={task_id}")
        if str(row[5]) != TASK_KIND_GOAL:
            raise ValueError(f"task {task_id} is not a goal task (task_kind={row[5]!r})")
        mid = row[8]
        slug = row[9]
        return {
            "id": int(row[0]),
            "goal": str(row[1]),
            "status": str(row[2]),
            "plan_json": str(row[3]),
            "current_output": str(row[4]),
            "task_kind": str(row[5]),
            "created_at": str(row[6]),
            "updated_at": str(row[7]),
            "mission_id": int(mid) if mid is not None else None,
            "mission_slug": str(slug) if slug is not None else None,
        }

    async def list_system_tasks(
        self,
        mission_id: int,
        *,
        limit: int = 50,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        assert self._conn is not None
        limit = max(1, min(limit, 500))
        mid = int(mission_id)
        if status is not None:
            cur = await self._conn.execute(
                """
                SELECT t.id, t.goal, t.status, t.plan_json, t.created_at, t.updated_at,
                       t.mission_id, m.slug
                FROM tasks t
                LEFT JOIN missions m ON m.id = t.mission_id
                WHERE t.task_kind = ? AND t.mission_id = ? AND t.status = ?
                ORDER BY t.id DESC
                LIMIT ?
                """,
                (TASK_KIND_SYSTEM, mid, status, limit),
            )
        else:
            cur = await self._conn.execute(
                """
                SELECT t.id, t.goal, t.status, t.plan_json, t.created_at, t.updated_at,
                       t.mission_id, m.slug
                FROM tasks t
                LEFT JOIN missions m ON m.id = t.mission_id
                WHERE t.task_kind = ? AND t.mission_id = ?
                ORDER BY t.id DESC
                LIMIT ?
                """,
                (TASK_KIND_SYSTEM, mid, limit),
            )
        rows = await cur.fetchall()
        return self._goal_task_rows_to_dicts(rows)

    async def get_system_task(self, task_id: int) -> dict[str, Any]:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT t.id, t.goal, t.status, t.plan_json, t.current_output, t.task_kind,
                   t.created_at, t.updated_at, t.mission_id, m.slug
            FROM tasks t
            LEFT JOIN missions m ON m.id = t.mission_id
            WHERE t.id = ?
            """,
            (task_id,),
        )
        row = await cur.fetchone()
        if not row:
            raise LookupError(f"no task with id={task_id}")
        if str(row[5]) != TASK_KIND_SYSTEM:
            raise ValueError(
                f"task {task_id} is not a system task (task_kind={row[5]!r})"
            )
        mid = row[8]
        slug = row[9]
        return {
            "id": int(row[0]),
            "goal": str(row[1]),
            "status": str(row[2]),
            "plan_json": str(row[3]),
            "current_output": str(row[4]),
            "task_kind": str(row[5]),
            "created_at": str(row[6]),
            "updated_at": str(row[7]),
            "mission_id": int(mid) if mid is not None else None,
            "mission_slug": str(slug) if slug is not None else None,
        }

    async def append_action_log(
        self,
        kind: str,
        payload: dict[str, Any],
        session_id: int | None = None,
    ) -> int:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            INSERT INTO action_log (session_id, kind, payload_json)
            VALUES (?, ?, ?)
            """,
            (session_id, kind, json.dumps(payload, ensure_ascii=False)),
        )
        await self._conn.commit()
        return int(cur.lastrowid)

    async def load_messages_for_dream(
        self, *, session_id: int | None, limit: int
    ) -> list[str]:
        """Chronological compact lines for dream compression (newest window)."""
        assert self._conn is not None
        if session_id is not None:
            cur = await self._conn.execute(
                """
                SELECT session_id, role, content_json
                FROM messages
                WHERE session_id = ? AND tombstone = 0 AND role != ?
                ORDER BY sequence DESC
                LIMIT ?
                """,
                (session_id, ROLE_SYSTEM, limit),
            )
        else:
            cur = await self._conn.execute(
                """
                SELECT session_id, role, content_json
                FROM messages
                WHERE tombstone = 0 AND role != ?
                ORDER BY datetime(created_at) DESC, sequence DESC
                LIMIT ?
                """,
                (ROLE_SYSTEM, limit),
            )
        rows = await cur.fetchall()
        rows = list(reversed(rows))
        from ada.dream.transcript_compact import compact_message_line

        return [compact_message_line(int(sid), role, cj) for sid, role, cj in rows]

    async def load_usage_ledger_lines(self, limit: int) -> list[str]:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT session_id, model, input_tokens, output_tokens, recorded_at
            FROM usage_ledger
            ORDER BY datetime(recorded_at) DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cur.fetchall()
        rows = list(reversed(rows))
        lines: list[str] = []
        for sid, model, inp, out, rec in rows:
            lines.append(
                f"task={sid} model={model or ''} in={inp} out={out} at={rec}"
            )
        return lines

    @staticmethod
    def _tags_to_json(tags: list[str] | None) -> str:
        if tags is None:
            return "[]"
        if not all(isinstance(t, str) for t in tags):
            raise TypeError("tags must be a list of strings")
        return json.dumps(tags, ensure_ascii=False)

    @staticmethod
    def _tags_from_json(tags_json: str) -> list[str]:
        try:
            v = json.loads(tags_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"invalid tags_json: {e}") from e
        if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            raise ValueError("tags_json must be a JSON array of strings")
        return v

    @staticmethod
    def _ref_item_ids_to_json(ref_item_ids: list[int]) -> str:
        if not all(isinstance(x, int) for x in ref_item_ids):
            raise TypeError("ref_item_ids must be a list of int")
        return json.dumps(ref_item_ids, ensure_ascii=False)

    @staticmethod
    def _ref_item_ids_from_json(raw: str) -> list[int]:
        try:
            v = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"invalid ref_item_ids_json: {e}") from e
        if not isinstance(v, list) or not all(isinstance(x, int) for x in v):
            raise ValueError("ref_item_ids_json must be a JSON array of integers")
        return v

    @staticmethod
    def _knowledge_mission_source_join_clause(
        mission_scope: int | None, *, ki_alias: str = "ki", ks_alias: str = "ks"
    ) -> tuple[str, list[Any]]:
        """Join knowledge_items to sources; scoped = global rows + owned mission."""
        if mission_scope is None:
            return "", []
        join = (
            f" INNER JOIN knowledge_sources {ks_alias} ON {ks_alias}.id = {ki_alias}.source_id "
            f"AND ({ks_alias}.mission_id IS NULL OR {ks_alias}.mission_id = ?)"
        )
        return join, [mission_scope]

    async def get_task_mission_id(self, task_id: int) -> int | None:
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT mission_id FROM tasks WHERE id = ?",
            (int(task_id),),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        raw = row[0]
        return int(raw) if raw is not None else None

    async def insert_knowledge_source(
        self,
        kind: KnowledgeKind,
        *,
        label: str | None = None,
        base_url: str = "",
        config_json: str | dict[str, Any] | None = None,
        mission_id: int | None = None,
    ) -> int:
        if kind not in ("api", "rss", "web", "brand"):
            raise ValueError(f"invalid knowledge source kind: {kind!r}")
        assert self._conn is not None
        if isinstance(config_json, dict):
            cfg = json.dumps(config_json, ensure_ascii=False)
        elif config_json is None:
            cfg = "{}"
        else:
            cfg = str(config_json)
        cur = await self._conn.execute(
            """
            INSERT INTO knowledge_sources (kind, label, base_url, config_json, mission_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (kind, label, base_url, cfg, mission_id),
        )
        await self._conn.commit()
        return int(cur.lastrowid)

    async def list_knowledge_sources(
        self,
        *,
        kind: str | None = None,
        ingest_mission_id: int | None = None,
    ) -> list[dict[str, Any]]:
        assert self._conn is not None
        conds: list[str] = []
        args: list[Any] = []
        if kind is not None:
            conds.append("kind = ?")
            args.append(kind)
        if ingest_mission_id is not None:
            conds.append("(mission_id IS NULL OR mission_id = ?)")
            args.append(int(ingest_mission_id))
        where = f"WHERE {' AND '.join(conds)}" if conds else ""
        cur = await self._conn.execute(
            f"""
            SELECT id, kind, label, base_url, config_json, mission_id, created_at
            FROM knowledge_sources
            {where}
            ORDER BY id ASC
            """,
            args,
        )
        rows = await cur.fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            cfg_raw = row[4]
            try:
                cfg_parsed: Any = json.loads(str(cfg_raw)) if cfg_raw else {}
            except json.JSONDecodeError:
                cfg_parsed = {}
            mid_raw = row[5]
            out.append(
                {
                    "id": int(row[0]),
                    "kind": str(row[1]),
                    "label": row[2],
                    "base_url": str(row[3]),
                    "config_json": cfg_parsed,
                    "mission_id": int(mid_raw) if mid_raw is not None else None,
                    "created_at": str(row[6]),
                }
            )
        return out

    async def ensure_knowledge_source(
        self,
        kind: KnowledgeKind,
        *,
        label: str,
        base_url: str = "",
        config_json: dict[str, Any] | None = None,
        mission_id: int | None = None,
    ) -> int:
        """Return existing knowledge_sources.id matching kind+label+mission, else insert."""
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT id FROM knowledge_sources
            WHERE kind = ? AND COALESCE(label, '') = ?
              AND mission_id IS NOT DISTINCT FROM ?
            LIMIT 1
            """,
            (kind, label, mission_id),
        )
        row = await cur.fetchone()
        if row is not None:
            return int(row[0])
        return await self.insert_knowledge_source(
            kind,
            label=label,
            base_url=base_url,
            config_json=config_json or {},
            mission_id=mission_id,
        )

    async def create_ingest_job(
        self,
        kind: str,
        params_json: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> int:
        assert self._conn is not None
        payload = json.dumps(params_json, ensure_ascii=False)
        try:
            cur = await self._conn.execute(
                """
                INSERT INTO ingest_jobs (kind, params_json, idempotency_key, status)
                VALUES (?, ?, ?, 'pending')
                """,
                (kind, payload, idempotency_key),
            )
            await self._conn.commit()
            return int(cur.lastrowid)
        except sqlite3.IntegrityError:
            cur = await self._conn.execute(
                """
                SELECT id FROM ingest_jobs
                WHERE kind = ? AND idempotency_key IS NOT DISTINCT FROM ?
                LIMIT 1
                """,
                (kind, idempotency_key),
            )
            row = await cur.fetchone()
            if row is None:
                raise
            return int(row[0])

    async def update_ingest_job(
        self,
        job_id: int,
        *,
        status: str,
        error: str = "",
        set_started: bool = False,
        set_completed: bool = False,
    ) -> None:
        assert self._conn is not None
        parts: list[str] = ["status = ?", "error = ?"]
        args: list[Any] = [status, error]
        if set_started:
            parts.append("started_at = datetime('now')")
        if set_completed:
            parts.append("completed_at = datetime('now')")
        sql = f"UPDATE ingest_jobs SET {', '.join(parts)} WHERE id = ?"
        args.append(job_id)
        await self._conn.execute(sql, tuple(args))
        await self._conn.commit()

    async def insert_ingest_raw(
        self,
        *,
        ingest_job_id: int | None,
        source: str,
        uri: str,
        body: str,
        meta_json: dict[str, Any] | None = None,
    ) -> int:
        assert self._conn is not None
        h = hashlib.sha256(body.encode("utf-8", errors="replace")).hexdigest()
        meta = json.dumps(meta_json or {}, ensure_ascii=False)
        cur = await self._conn.execute(
            """
            INSERT INTO ingest_raw (
                ingest_job_id, source, uri, content_sha256, body, meta_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (ingest_job_id, source, uri, f"sha256:{h}", body, meta),
        )
        await self._conn.commit()
        return int(cur.lastrowid)

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
        assert self._conn is not None
        cur_sm = await self._conn.execute(
            "SELECT mission_id FROM knowledge_sources WHERE id = ?",
            (int(source_id),),
        )
        src_row = await cur_sm.fetchone()
        if src_row is None:
            raise LookupError(f"no knowledge source with id={source_id}")
        raw_m = src_row[0]
        source_mission: int | None = int(raw_m) if raw_m is not None else None
        if source_mission is None:
            link_pool_sql = "ks.mission_id IS NULL"
            link_pool_args: list[Any] = []
        else:
            link_pool_sql = "(ks.mission_id IS NULL OR ks.mission_id = ?)"
            link_pool_args = [source_mission]
        if external_id is not None:
            cur = await self._conn.execute(
                """
                SELECT id FROM knowledge_items
                WHERE source_id = ? AND external_id = ?
                LIMIT 1
                """,
                (source_id, external_id),
            )
            row = await cur.fetchone()
            if row is not None:
                return KnowledgeItemInsertResult(int(row[0]), False)
        else:
            cur = await self._conn.execute(
                """
                SELECT id FROM knowledge_items
                WHERE source_id = ? AND content_hash = ? AND external_id IS NULL
                LIMIT 1
                """,
                (source_id, content_hash),
            )
            row = await cur.fetchone()
            if row is not None:
                return KnowledgeItemInsertResult(int(row[0]), False)

        if payload is not None:
            raw_link = payload.get("link")
            if isinstance(raw_link, str):
                match_vals = _story_link_sql_match_values(raw_link)
                if match_vals:
                    ph = ",".join("?" * len(match_vals))
                    cur = await self._conn.execute(
                        f"""
                        SELECT ki.id FROM knowledge_items ki
                        INNER JOIN knowledge_sources ks ON ks.id = ki.source_id
                        WHERE ki.payload_json IS NOT NULL
                          AND json_extract(ki.payload_json, '$.link') IS NOT NULL
                          AND lower(trim(json_extract(ki.payload_json, '$.link'))) IN ({ph})
                          AND {link_pool_sql}
                        LIMIT 1
                        """,
                        (*link_pool_args, *match_vals),
                    )
                    row = await cur.fetchone()
                    if row is not None:
                        return KnowledgeItemInsertResult(int(row[0]), False)

        tags_json = self._tags_to_json(tags)
        payload_json: str | None
        if payload is not None:
            payload_json = json.dumps(payload, ensure_ascii=False)
        else:
            payload_json = None
        cur = await self._conn.execute(
            """
            INSERT INTO knowledge_items (
                source_id, external_id, published_at, tags_json,
                content_excerpt, payload_json, content_hash,
                relevance_score, expires_at, tombstoned
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                external_id,
                published_at,
                tags_json,
                content_excerpt,
                payload_json,
                content_hash,
                relevance_score,
                expires_at,
                tombstoned,
            ),
        )
        await self._conn.commit()
        return KnowledgeItemInsertResult(int(cur.lastrowid), True)

    async def insert_knowledge_synthesis(
        self,
        body: str,
        ref_item_ids: list[int],
        *,
        task_id: int | None = None,
    ) -> int:
        assert self._conn is not None
        ref_json = self._ref_item_ids_to_json(ref_item_ids)
        cur = await self._conn.execute(
            """
            INSERT INTO knowledge_synthesis (body, ref_item_ids_json, task_id)
            VALUES (?, ?, ?)
            """,
            (body, ref_json, task_id),
        )
        await self._conn.commit()
        return int(cur.lastrowid)

    def _row_to_knowledge_item(self, row: tuple[Any, ...]) -> dict[str, Any]:
        (
            iid,
            source_id,
            external_id,
            published_at,
            ingested_at,
            tags_json,
            content_excerpt,
            payload_json,
            content_hash,
            relevance_score,
            impact_score,
            triage_primary_category,
            triage_secondary_categories_json,
            expires_at,
            tombstoned,
        ) = row
        payload: dict[str, Any] | None
        if payload_json is None:
            payload = None
        else:
            payload = json.loads(str(payload_json))
        rs: float | None
        if relevance_score is None:
            rs = None
        else:
            rs = float(relevance_score)
        imp: int | None
        if impact_score is None:
            imp = None
        else:
            imp = int(impact_score)
        triage_pc: str | None
        if triage_primary_category is None or str(triage_primary_category).strip() == "":
            triage_pc = None
        else:
            triage_pc = str(triage_primary_category).strip()
        sec_raw = str(triage_secondary_categories_json or "[]")
        try:
            parsed_sec = json.loads(sec_raw)
        except json.JSONDecodeError:
            parsed_sec = []
        triage_secs: list[str] = []
        if isinstance(parsed_sec, list):
            for x in parsed_sec:
                if isinstance(x, str) and x.strip():
                    triage_secs.append(x.strip())
        return {
            "id": int(iid),
            "source_id": int(source_id),
            "external_id": external_id,
            "published_at": published_at,
            "ingested_at": str(ingested_at),
            "tags": self._tags_from_json(str(tags_json)),
            "content_excerpt": str(content_excerpt),
            "payload": payload,
            "content_hash": str(content_hash),
            "relevance_score": rs,
            "impact_score": imp,
            "triage_primary_category": triage_pc,
            "triage_secondary_categories": triage_secs,
            "expires_at": str(expires_at) if expires_at is not None else None,
            "tombstoned": int(tombstoned),
        }

    async def get_knowledge_item(
        self,
        item_id: int,
        *,
        mission_scope: int | None = None,
    ) -> dict[str, Any]:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT id, source_id, external_id, published_at, ingested_at,
                   tags_json, content_excerpt, payload_json, content_hash,
                   relevance_score, impact_score,
                   triage_primary_category, triage_secondary_categories_json,
                   expires_at, tombstoned
            FROM knowledge_items WHERE id = ?
            """,
            (item_id,),
        )
        row = await cur.fetchone()
        if not row:
            raise LookupError(f"no knowledge item with id={item_id}")
        if mission_scope is not None:
            cur2 = await self._conn.execute(
                """
                SELECT 1 FROM knowledge_items ki
                INNER JOIN knowledge_sources ks ON ks.id = ki.source_id
                WHERE ki.id = ?
                  AND (ks.mission_id IS NULL OR ks.mission_id = ?)
                LIMIT 1
                """,
                (int(item_id), int(mission_scope)),
            )
            if await cur2.fetchone() is None:
                raise LookupError(f"no knowledge item with id={item_id}")
        return self._row_to_knowledge_item(row)

    async def list_knowledge_items(
        self,
        *,
        source_id: int | None = None,
        mission_scope: int | None = None,
        limit: int = 100,
        ingested_after: str | None = None,
        ingested_before: str | None = None,
        min_relevance_score: float | None = None,
        valid_at_now: bool = True,
    ) -> list[dict[str, Any]]:
        assert self._conn is not None
        lim = max(1, min(limit, 500))
        mj_join, mj_args = self._knowledge_mission_source_join_clause(
            mission_scope, ki_alias="ki"
        )
        conds: list[str] = []
        args: list[Any] = list(mj_args)
        if source_id is not None:
            conds.append("ki.source_id = ?")
            args.append(source_id)
        if ingested_after is not None:
            conds.append("datetime(ki.ingested_at) >= datetime(?)")
            args.append(ingested_after)
        if ingested_before is not None:
            conds.append("datetime(ki.ingested_at) <= datetime(?)")
            args.append(ingested_before)
        vf_parts, vf_args = self._knowledge_filter_parts(
            table_alias="ki",
            tag=None,
            ingested_after=None,
            ingested_before=None,
            min_relevance_score=min_relevance_score,
            valid_at_now=valid_at_now,
        )
        conds.extend(vf_parts)
        args.extend(vf_args)
        where = f"WHERE {' AND '.join(conds)}" if conds else ""
        args.append(lim)
        cur = await self._conn.execute(
            f"""
            SELECT ki.id, ki.source_id, ki.external_id, ki.published_at, ki.ingested_at,
                   ki.tags_json, ki.content_excerpt, ki.payload_json, ki.content_hash,
                   ki.relevance_score, ki.impact_score,
                   ki.triage_primary_category, ki.triage_secondary_categories_json,
                   ki.expires_at, ki.tombstoned
            FROM knowledge_items ki{mj_join}
            {where}
            ORDER BY datetime(ki.ingested_at) DESC
            LIMIT ?
            """,
            args,
        )
        rows = await cur.fetchall()
        return [self._row_to_knowledge_item(r) for r in rows]

    async def _knowledge_fts_table_exists(self) -> bool:
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='knowledge_items_fts'"
        )
        return await cur.fetchone() is not None

    def _knowledge_filter_parts(
        self,
        *,
        table_alias: str,
        tag: str | None,
        ingested_after: str | None,
        ingested_before: str | None,
        min_relevance_score: float | None = None,
        valid_at_now: bool = True,
        primary_triage_category: str | None = None,
    ) -> tuple[list[str], list[Any]]:
        conds: list[str] = []
        args: list[Any] = []
        prefix = f"{table_alias}." if table_alias else ""
        if valid_at_now:
            conds.append(f"{prefix}tombstoned = 0")
            conds.append(
                f"({prefix}expires_at IS NULL OR datetime({prefix}expires_at) > datetime('now'))"
            )
        if min_relevance_score is not None:
            conds.append(f"COALESCE({prefix}relevance_score, 1.0) >= ?")
            args.append(min_relevance_score)
        if tag is not None:
            conds.append(
                f"EXISTS (SELECT 1 FROM json_each({prefix}tags_json) j WHERE j.value = ?)"
            )
            args.append(tag)
        if primary_triage_category is not None and str(primary_triage_category).strip():
            conds.append(f"{prefix}triage_primary_category = ?")
            args.append(str(primary_triage_category).strip())
        if ingested_after is not None:
            conds.append(f"datetime({prefix}ingested_at) >= datetime(?)")
            args.append(ingested_after)
        if ingested_before is not None:
            conds.append(f"datetime({prefix}ingested_at) <= datetime(?)")
            args.append(ingested_before)
        return conds, args

    def _knowledge_filter_sql(
        self,
        *,
        table_alias: str,
        tag: str | None,
        ingested_after: str | None,
        ingested_before: str | None,
        min_relevance_score: float | None = None,
        valid_at_now: bool = True,
        primary_triage_category: str | None = None,
    ) -> tuple[str, list[Any]]:
        conds, args = self._knowledge_filter_parts(
            table_alias=table_alias,
            tag=tag,
            ingested_after=ingested_after,
            ingested_before=ingested_before,
            min_relevance_score=min_relevance_score,
            valid_at_now=valid_at_now,
            primary_triage_category=primary_triage_category,
        )
        if not conds:
            return "", []
        return " AND " + " AND ".join(conds), args

    async def upsert_knowledge_item_embedding(
        self,
        item_id: int,
        *,
        model: str,
        dim: int,
        embedding: bytes,
        content_hash: str,
    ) -> None:
        assert self._conn is not None
        await self._conn.execute(
            """
            INSERT INTO knowledge_item_embeddings (item_id, model, dim, embedding, content_hash)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(item_id, model) DO UPDATE SET
                dim = excluded.dim,
                embedding = excluded.embedding,
                content_hash = excluded.content_hash,
                created_at = datetime('now')
            """,
            (item_id, model, dim, embedding, content_hash),
        )
        await self._conn.commit()

    async def _search_knowledge_items_lexical(
        self,
        query: str,
        *,
        limit: int,
        tag: str | None,
        ingested_after: str | None,
        ingested_before: str | None,
        prefer_fts: bool,
        min_relevance_score: float | None = None,
        valid_at_now: bool = True,
        primary_triage_category: str | None = None,
        mission_scope: int | None = None,
    ) -> list[dict[str, Any]]:
        mq = build_fts_match_query(query)
        lim = max(1, min(limit, 500))
        assert self._conn is not None
        mj_join, mj_args = self._knowledge_mission_source_join_clause(
            mission_scope, ki_alias="ki"
        )
        extra_fts, args_fts = self._knowledge_filter_sql(
            table_alias="ki",
            tag=tag,
            ingested_after=ingested_after,
            ingested_before=ingested_before,
            min_relevance_score=min_relevance_score,
            valid_at_now=valid_at_now,
            primary_triage_category=primary_triage_category,
        )
        if not mq:
            return await self._search_knowledge_items_like(
                query,
                limit=lim,
                tag=tag,
                ingested_after=ingested_after,
                ingested_before=ingested_before,
                min_relevance_score=min_relevance_score,
                valid_at_now=valid_at_now,
                primary_triage_category=primary_triage_category,
                mission_scope=mission_scope,
            )
        if prefer_fts and await self._knowledge_fts_table_exists():
            try:
                sql = f"""
                    SELECT ki.id, ki.source_id, ki.external_id, ki.published_at, ki.ingested_at,
                           ki.tags_json, ki.content_excerpt, ki.payload_json, ki.content_hash,
                           ki.relevance_score, ki.impact_score,
                           ki.triage_primary_category, ki.triage_secondary_categories_json,
                           ki.expires_at, ki.tombstoned
                    FROM knowledge_items ki{mj_join}
                    INNER JOIN knowledge_items_fts ON ki.id = knowledge_items_fts.rowid
                    WHERE knowledge_items_fts MATCH ?{extra_fts}
                    ORDER BY bm25(knowledge_items_fts) ASC, datetime(ki.ingested_at) DESC
                    LIMIT ?
                    """
                params: list[Any] = [*mj_args, mq, *args_fts, lim]
                cur = await self._conn.execute(sql, params)
                rows = await cur.fetchall()
                return [self._row_to_knowledge_item(r) for r in rows]
            except Exception:
                pass
        return await self._search_knowledge_items_like(
            query,
            limit=lim,
            tag=tag,
            ingested_after=ingested_after,
            ingested_before=ingested_before,
            min_relevance_score=min_relevance_score,
            valid_at_now=valid_at_now,
            primary_triage_category=primary_triage_category,
            mission_scope=mission_scope,
        )

    async def _search_knowledge_items_semantic(
        self,
        query_vec: list[float],
        *,
        embedding_model: str,
        limit: int,
        min_cosine: float,
        tag: str | None,
        ingested_after: str | None,
        ingested_before: str | None,
        min_relevance_score: float | None = None,
        valid_at_now: bool = True,
        primary_triage_category: str | None = None,
        mission_scope: int | None = None,
    ) -> list[dict[str, Any]]:
        assert self._conn is not None
        mj_join, mj_args = self._knowledge_mission_source_join_clause(
            mission_scope, ki_alias="ki"
        )
        extra, args_extra = self._knowledge_filter_sql(
            table_alias="ki",
            tag=tag,
            ingested_after=ingested_after,
            ingested_before=ingested_before,
            min_relevance_score=min_relevance_score,
            valid_at_now=valid_at_now,
            primary_triage_category=primary_triage_category,
        )
        sql = f"""
            SELECT e.item_id, e.embedding, e.dim
            FROM knowledge_item_embeddings e
            INNER JOIN knowledge_items ki ON ki.id = e.item_id{mj_join}
            WHERE e.model = ?{extra}
            """
        params: list[Any] = [*mj_args, embedding_model, *args_extra]
        cur = await self._conn.execute(sql, params)
        raw_rows = await cur.fetchall()
        scored: list[tuple[int, float]] = []
        qdim = len(query_vec)
        for iid, emb_blob, dim in raw_rows:
            if int(dim) != qdim:
                continue
            vec = blob_to_float32_list(bytes(emb_blob))
            if len(vec) != qdim:
                continue
            sim = cosine_similarity(query_vec, vec)
            if sim >= min_cosine:
                scored.append((int(iid), sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        ids = [i for i, _ in scored[: max(1, min(limit, 500))]]
        return await self._knowledge_items_by_ids_ordered(
            ids, mission_scope=mission_scope
        )

    async def _knowledge_items_by_ids_ordered(
        self,
        ids: list[int],
        *,
        mission_scope: int | None = None,
    ) -> list[dict[str, Any]]:
        if not ids:
            return []
        assert self._conn is not None
        ph = ",".join("?" * len(ids))
        mj_join, mj_args = self._knowledge_mission_source_join_clause(
            mission_scope, ki_alias="ki"
        )
        cur = await self._conn.execute(
            f"""
            SELECT ki.id, ki.source_id, ki.external_id, ki.published_at, ki.ingested_at,
                   ki.tags_json, ki.content_excerpt, ki.payload_json, ki.content_hash,
                   ki.relevance_score, ki.impact_score,
                   ki.triage_primary_category, ki.triage_secondary_categories_json,
                   ki.expires_at, ki.tombstoned
            FROM knowledge_items ki{mj_join}
            WHERE ki.id IN ({ph})
            """,
            [*mj_args, *ids],
        )
        rows = await cur.fetchall()
        by_id: dict[int, dict[str, Any]] = {}
        for r in rows:
            item = self._row_to_knowledge_item(r)
            by_id[item["id"]] = item
        return [by_id[i] for i in ids if i in by_id]

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
        primary_triage_category: str | None = None,
        mission_scope: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Lexical (FTS/LIKE), semantic (cosine on stored embeddings), or hybrid (RRF).
        """
        sm = (search_mode or "lexical").strip().lower()
        if sm not in ("lexical", "semantic", "hybrid"):
            sm = "lexical"
        lim = max(1, min(limit, 500))
        arm = max(lim, 60)

        if sm == "semantic":
            if (
                query_embedding
                and embedding_model
                and len(query_embedding) > 0
            ):
                return await self._search_knowledge_items_semantic(
                    query_embedding,
                    embedding_model=embedding_model,
                    limit=lim,
                    min_cosine=embedding_min_cosine,
                    tag=tag,
                    ingested_after=ingested_after,
                    ingested_before=ingested_before,
                    min_relevance_score=min_relevance_score,
                    valid_at_now=valid_at_now,
                    primary_triage_category=primary_triage_category,
                    mission_scope=mission_scope,
                )
            return await self._search_knowledge_items_lexical(
                query,
                limit=lim,
                tag=tag,
                ingested_after=ingested_after,
                ingested_before=ingested_before,
                prefer_fts=prefer_fts,
                min_relevance_score=min_relevance_score,
                valid_at_now=valid_at_now,
                primary_triage_category=primary_triage_category,
                mission_scope=mission_scope,
            )

        if sm == "hybrid":
            if (
                query_embedding
                and embedding_model
                and len(query_embedding) > 0
            ):
                lex = await self._search_knowledge_items_lexical(
                    query,
                    limit=arm,
                    tag=tag,
                    ingested_after=ingested_after,
                    ingested_before=ingested_before,
                    prefer_fts=prefer_fts,
                    min_relevance_score=min_relevance_score,
                    valid_at_now=valid_at_now,
                    primary_triage_category=primary_triage_category,
                    mission_scope=mission_scope,
                )
                sem = await self._search_knowledge_items_semantic(
                    query_embedding,
                    embedding_model=embedding_model,
                    limit=arm,
                    min_cosine=embedding_min_cosine,
                    tag=tag,
                    ingested_after=ingested_after,
                    ingested_before=ingested_before,
                    min_relevance_score=min_relevance_score,
                    valid_at_now=valid_at_now,
                    primary_triage_category=primary_triage_category,
                    mission_scope=mission_scope,
                )
                lex_ids = [x["id"] for x in lex]
                sem_ids = [x["id"] for x in sem]
                fused = reciprocal_rank_fusion([lex_ids, sem_ids], k=60)
                pick = fused[:lim]
                return await self._knowledge_items_by_ids_ordered(
                    pick, mission_scope=mission_scope
                )
            return await self._search_knowledge_items_lexical(
                query,
                limit=lim,
                tag=tag,
                ingested_after=ingested_after,
                ingested_before=ingested_before,
                prefer_fts=prefer_fts,
                min_relevance_score=min_relevance_score,
                valid_at_now=valid_at_now,
                primary_triage_category=primary_triage_category,
                mission_scope=mission_scope,
            )

        return await self._search_knowledge_items_lexical(
            query,
            limit=lim,
            tag=tag,
            ingested_after=ingested_after,
            ingested_before=ingested_before,
            prefer_fts=prefer_fts,
            min_relevance_score=min_relevance_score,
            valid_at_now=valid_at_now,
            primary_triage_category=primary_triage_category,
            mission_scope=mission_scope,
        )

    async def _search_knowledge_items_like(
        self,
        query: str,
        *,
        limit: int,
        tag: str | None,
        ingested_after: str | None,
        ingested_before: str | None,
        min_relevance_score: float | None = None,
        valid_at_now: bool = True,
        primary_triage_category: str | None = None,
        mission_scope: int | None = None,
    ) -> list[dict[str, Any]]:
        assert self._conn is not None
        token = query.strip()
        if not token:
            return []
        esc = token.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{esc}%"
        mj_join, mj_args = self._knowledge_mission_source_join_clause(
            mission_scope, ki_alias="ki"
        )
        extra, args_extra = self._knowledge_filter_sql(
            table_alias="ki",
            tag=tag,
            ingested_after=ingested_after,
            ingested_before=ingested_before,
            min_relevance_score=min_relevance_score,
            valid_at_now=valid_at_now,
            primary_triage_category=primary_triage_category,
        )
        sql = f"""
            SELECT ki.id, ki.source_id, ki.external_id, ki.published_at, ki.ingested_at,
                   ki.tags_json, ki.content_excerpt, ki.payload_json, ki.content_hash,
                   ki.relevance_score, ki.impact_score,
                   ki.triage_primary_category, ki.triage_secondary_categories_json,
                   ki.expires_at, ki.tombstoned
            FROM knowledge_items ki{mj_join}
            WHERE (ki.content_excerpt LIKE ? ESCAPE '\\' OR ki.tags_json LIKE ? ESCAPE '\\')
            {extra}
            ORDER BY datetime(ki.ingested_at) DESC
            LIMIT ?
            """
        params = [*mj_args, pattern, pattern, *args_extra, limit]
        cur = await self._conn.execute(sql, params)
        rows = await cur.fetchall()
        return [self._row_to_knowledge_item(r) for r in rows]

    async def list_knowledge_synthesis_for_task(
        self, task_id: int
    ) -> list[dict[str, Any]]:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT id, body, ref_item_ids_json, task_id, created_at
            FROM knowledge_synthesis
            WHERE task_id = ?
            ORDER BY datetime(created_at) DESC
            """,
            (task_id,),
        )
        rows = await cur.fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            iid, body, ref_json, tid, created_at = row
            out.append(
                {
                    "id": int(iid),
                    "body": str(body),
                    "ref_item_ids": self._ref_item_ids_from_json(str(ref_json)),
                    "task_id": int(tid) if tid is not None else None,
                    "created_at": str(created_at),
                }
            )
        return out

    async def list_unscored_knowledge(
        self, limit: int = 20, *, mission_scope: int | None = None
    ) -> list[dict[str, Any]]:
        """Return active knowledge rows with ``impact_score IS NULL`` (newest first).

        Excludes tombstoned rows and rows past ``expires_at`` — same validity rules as
        :meth:`list_knowledge_items` with ``valid_at_now=True``.
        """
        assert self._conn is not None
        lim = max(1, min(limit, 500))
        mj_join, mj_args = self._knowledge_mission_source_join_clause(
            mission_scope, ki_alias="ki"
        )
        cur = await self._conn.execute(
            f"""
            SELECT ki.id, ki.source_id, ki.external_id, ki.published_at, ki.ingested_at,
                   ki.tags_json, ki.content_excerpt, ki.payload_json, ki.content_hash,
                   ki.relevance_score, ki.impact_score,
                   ki.triage_primary_category, ki.triage_secondary_categories_json,
                   ki.expires_at, ki.tombstoned
            FROM knowledge_items ki{mj_join}
            WHERE ki.impact_score IS NULL
              AND ki.tombstoned = 0
              AND (ki.expires_at IS NULL OR datetime(ki.expires_at) > datetime('now'))
            ORDER BY datetime(ki.ingested_at) DESC
            LIMIT ?
            """,
            (*mj_args, lim),
        )
        rows = await cur.fetchall()
        return [self._row_to_knowledge_item(r) for r in rows]

    async def update_impact_score(self, knowledge_id: int, score: int) -> None:
        if not isinstance(score, int) or score < 1 or score > 10:
            raise ValueError("score must be an integer from 1 to 10")
        assert self._conn is not None
        cur = await self._conn.execute(
            "UPDATE knowledge_items SET impact_score = ? WHERE id = ?",
            (score, knowledge_id),
        )
        if cur.rowcount == 0:
            raise LookupError(f"no knowledge item with id={knowledge_id}")
        await self._conn.commit()

    async def update_triage_result(
        self,
        knowledge_id: int,
        *,
        impact_score: int,
        primary_category: str,
        secondary_categories: list[str],
    ) -> None:
        if not isinstance(impact_score, int) or impact_score < 1 or impact_score > 10:
            raise ValueError("impact_score must be an integer from 1 to 10")
        if not isinstance(primary_category, str) or not primary_category.strip():
            raise ValueError("primary_category required")
        sec_json = json.dumps(list(secondary_categories), ensure_ascii=False)
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            UPDATE knowledge_items SET
                impact_score = ?,
                triage_primary_category = ?,
                triage_secondary_categories_json = ?
            WHERE id = ?
            """,
            (impact_score, primary_category.strip(), sec_json, knowledge_id),
        )
        if cur.rowcount == 0:
            raise LookupError(f"no knowledge item with id={knowledge_id}")
        await self._conn.commit()

    async def list_backfill_triage_categories(
        self, limit: int = 20, *, mission_scope: int | None = None
    ) -> list[dict[str, Any]]:
        """Rows scored but missing triage primary category (newest first)."""
        assert self._conn is not None
        lim = max(1, min(limit, 500))
        mj_join, mj_args = self._knowledge_mission_source_join_clause(
            mission_scope, ki_alias="ki"
        )
        cur = await self._conn.execute(
            f"""
            SELECT ki.id, ki.source_id, ki.external_id, ki.published_at, ki.ingested_at,
                   ki.tags_json, ki.content_excerpt, ki.payload_json, ki.content_hash,
                   ki.relevance_score, ki.impact_score,
                   ki.triage_primary_category, ki.triage_secondary_categories_json,
                   ki.expires_at, ki.tombstoned
            FROM knowledge_items ki{mj_join}
            WHERE ki.impact_score IS NOT NULL
              AND ki.triage_primary_category IS NULL
              AND ki.tombstoned = 0
              AND (ki.expires_at IS NULL OR datetime(ki.expires_at) > datetime('now'))
            ORDER BY datetime(ki.ingested_at) DESC
            LIMIT ?
            """,
            (*mj_args, lim),
        )
        rows = await cur.fetchall()
        return [self._row_to_knowledge_item(r) for r in rows]

    async def insert_market_metric(
        self,
        metric_name: str,
        numeric_value: float,
        *,
        recorded_at: str | None = None,
        api_source: str = "",
    ) -> int:
        assert self._conn is not None
        if recorded_at is None:
            cur = await self._conn.execute(
                """
                INSERT INTO market_metrics (metric_name, numeric_value, api_source)
                VALUES (?, ?, ?)
                """,
                (metric_name, numeric_value, api_source),
            )
        else:
            cur = await self._conn.execute(
                """
                INSERT INTO market_metrics (metric_name, numeric_value, recorded_at, api_source)
                VALUES (?, ?, ?, ?)
                """,
                (metric_name, numeric_value, recorded_at, api_source),
            )
        await self._conn.commit()
        return int(cur.lastrowid)

    async def insert_synthesis_edge(
        self,
        knowledge_id: int,
        metric_id: int,
        causality_notes: str = "",
    ) -> int:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            INSERT INTO synthesis_edges (knowledge_id, metric_id, causality_notes)
            VALUES (?, ?, ?)
            """,
            (knowledge_id, metric_id, causality_notes),
        )
        await self._conn.commit()
        return int(cur.lastrowid)

    @staticmethod
    def normalize_entity_name(name: str) -> str:
        return " ".join((name or "").strip().lower().split())

    async def upsert_entity(
        self,
        *,
        type: str,
        name: str,
        aliases: list[str] | None = None,
        external_ids: dict[str, str] | None = None,
        payload_json: dict[str, Any] | None = None,
        last_enriched_at: str | None = None,
        mission_id: int | None = None,
    ) -> dict[str, Any]:
        assert self._conn is not None
        etype = str(type).strip().lower()
        ename = str(name).strip()
        if not etype:
            raise ValueError("entity type required")
        if not ename:
            raise ValueError("entity name required")
        normalized_name = self.normalize_entity_name(ename)
        if not normalized_name:
            raise ValueError("entity name required")
        payload: dict[str, Any] = dict(payload_json or {})
        if aliases:
            payload["aliases"] = [str(a).strip() for a in aliases if str(a).strip()]
        if external_ids:
            payload["external_ids"] = {
                str(k): str(v) for k, v in external_ids.items() if str(k).strip()
            }
        payload_str = json.dumps(payload, ensure_ascii=False)
        cur = await self._conn.execute(
            """
            SELECT id, name, payload_json FROM entities
            WHERE type = ? AND normalized_name = ?
              AND mission_id IS NOT DISTINCT FROM ?
            LIMIT 1
            """,
            (etype, normalized_name, mission_id),
        )
        row = await cur.fetchone()
        if row is not None:
            eid = int(row[0])
            existing_name = str(row[1] or "")
            existing_payload_raw = str(row[2] or "{}")
            try:
                existing_payload = json.loads(existing_payload_raw)
            except json.JSONDecodeError:
                existing_payload = {}
            existing_aliases = set(existing_payload.get("aliases", []))
            merged_aliases = sorted(
                {a for a in existing_aliases if isinstance(a, str)}
                | set(payload.get("aliases", []))
            )
            merged_external_ids: dict[str, str] = {}
            ext = existing_payload.get("external_ids", {})
            if isinstance(ext, dict):
                merged_external_ids.update(
                    {str(k): str(v) for k, v in ext.items() if str(k).strip()}
                )
            merged_external_ids.update(payload.get("external_ids", {}))
            merged_payload = existing_payload | payload
            if merged_aliases:
                merged_payload["aliases"] = merged_aliases
            if merged_external_ids:
                merged_payload["external_ids"] = merged_external_ids
            if last_enriched_at is not None:
                await self._conn.execute(
                    "UPDATE entities SET name = ?, payload_json = ?, last_enriched_at = ? "
                    "WHERE id = ?",
                    (
                        existing_name if existing_name else ename,
                        json.dumps(merged_payload, ensure_ascii=False),
                        str(last_enriched_at).strip(),
                        eid,
                    ),
                )
            else:
                await self._conn.execute(
                    "UPDATE entities SET name = ?, payload_json = ? WHERE id = ?",
                    (
                        existing_name if existing_name else ename,
                        json.dumps(merged_payload, ensure_ascii=False),
                        eid,
                    ),
                )
            await self._conn.commit()
            return {"entity_id": eid, "inserted": False, "normalized_name": normalized_name}
        le = str(last_enriched_at).strip() if last_enriched_at is not None else None
        cur = await self._conn.execute(
            """
            INSERT INTO entities (
                type, name, normalized_name, payload_json, last_enriched_at, mission_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (etype, ename, normalized_name, payload_str, le, mission_id),
        )
        await self._conn.commit()
        return {
            "entity_id": int(cur.lastrowid),
            "inserted": True,
            "normalized_name": normalized_name,
        }

    async def ensure_triage_category_entities(self) -> int:
        """Upsert graph-lite entities for each fixed triage code (type=category)."""
        n = 0
        for code in sorted(TRIAGE_CATEGORY_CODES):
            await self.upsert_entity(
                type="category",
                name=code,
                mission_id=None,
                payload_json={"triage_code": code, "role": "triage_taxonomy_parent"},
            )
            n += 1
        return n

    async def insert_graph_edge(
        self,
        *,
        src_entity_id: int,
        dst_entity_id: int,
        edge_type: str,
        confidence: float,
        status: str = GRAPH_EDGE_ACTIVE,
        superseded_by: int | None = None,
        source_url: str | None = None,
    ) -> int:
        """Insert edge; mission_id from matching endpoints (see docs/GRAPH_MISSION_SCOPE.md)."""
        assert self._conn is not None
        etype = str(edge_type).strip().lower()
        if not etype:
            raise ValueError("edge_type required")
        conf = float(confidence)
        if conf < 0 or conf > 1:
            raise ValueError("confidence must be between 0 and 1")
        st = str(status).strip().lower()
        if st not in GRAPH_EDGE_STATUSES:
            raise ValueError("invalid edge status")
        su: str | None
        if source_url is not None and str(source_url).strip():
            su = str(source_url).strip()
        else:
            su = None
        src_e = await self.get_entity_by_id(int(src_entity_id))
        dst_e = await self.get_entity_by_id(int(dst_entity_id))
        if src_e is None or dst_e is None:
            raise ValueError("unknown src_entity_id or dst_entity_id")
        sm = src_e.get("mission_id")
        dm = dst_e.get("mission_id")
        st_src = str(src_e.get("type") or "").strip().lower()
        st_dst = str(dst_e.get("type") or "").strip().lower()
        mission_id: int | None
        if sm == dm:
            mission_id = int(sm) if sm is not None else None
        elif etype == "classified_as":
            if sm is not None and dm is None and st_dst == "category":
                mission_id = int(sm)
            elif dm is not None and sm is None and st_src == "category":
                mission_id = int(dm)
            else:
                raise ValueError(
                    "record_edge: src/dst mission_id mismatch for classified_as"
                )
        else:
            raise ValueError(
                "record_edge: src_entity and dst_entity must share the same "
                "mission_id (or triage category bridge for classified_as)"
            )
        cur_ge = await self._conn.execute("PRAGMA table_info(graph_edges)")
        ge_cols = {str(row[1]) for row in await cur_ge.fetchall()}
        if "mission_id" in ge_cols:
            cur = await self._conn.execute(
                """
                INSERT INTO graph_edges (
                    src_entity_id, dst_entity_id, edge_type, confidence, status,
                    superseded_by, source_url, mission_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (src_entity_id, dst_entity_id, etype, conf, st, superseded_by, su, mission_id),
            )
        else:
            cur = await self._conn.execute(
                """
                INSERT INTO graph_edges (
                    src_entity_id, dst_entity_id, edge_type, confidence, status,
                    superseded_by, source_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (src_entity_id, dst_entity_id, etype, conf, st, superseded_by, su),
            )
        await self._conn.commit()
        return int(cur.lastrowid)

    async def get_entity_by_id(self, entity_id: int) -> dict[str, Any] | None:
        assert self._conn is not None
        eid = int(entity_id)
        cur = await self._conn.execute(
            """
            SELECT id, type, name, normalized_name, payload_json, last_enriched_at,
                   mission_id, created_at
            FROM entities WHERE id = ?
            """,
            (eid,),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        raw_payload = str(row[4] or "{}")
        try:
            payload: dict[str, Any] = json.loads(raw_payload)
        except json.JSONDecodeError:
            payload = {}
        le = row[5]
        mid_raw = row[6]
        return {
            "id": int(row[0]),
            "type": str(row[1]),
            "name": str(row[2]),
            "normalized_name": str(row[3]),
            "payload_json": payload,
            "last_enriched_at": le if le is not None else None,
            "mission_id": int(mid_raw) if mid_raw is not None else None,
            "created_at": str(row[7]),
        }

    async def count_unique_local_facts(self, entity_id: int) -> int:
        """
        Gatekeeper: count distinct non-empty source_url on active outgoing graph_edges.
        (Normative for ADA_PUBLISH_MIN_UNIQUE_FACTS; must match test matrix.)
        """
        assert self._conn is not None
        eid = int(entity_id)
        cur = await self._conn.execute(
            """
            SELECT COUNT(DISTINCT source_url) FROM graph_edges
            WHERE src_entity_id = ?
              AND status = ?
              AND source_url IS NOT NULL
              AND length(trim(source_url)) > 0
            """,
            (eid, GRAPH_EDGE_ACTIVE),
        )
        row = await cur.fetchone()
        if row is None or row[0] is None:
            return 0
        return int(row[0])

    async def count_outgoing_active_edges(self, entity_id: int) -> int:
        """Count active outgoing graph_edges (row count) for src_entity_id."""
        assert self._conn is not None
        eid = int(entity_id)
        cur = await self._conn.execute(
            """
            SELECT COUNT(*) FROM graph_edges
            WHERE src_entity_id = ? AND status = ?
            """,
            (eid, GRAPH_EDGE_ACTIVE),
        )
        row = await cur.fetchone()
        if row is None or row[0] is None:
            return 0
        return int(row[0])

    async def max_graph_edge_id_for_src_entity(self, entity_id: int) -> int:
        assert self._conn is not None
        eid = int(entity_id)
        cur = await self._conn.execute(
            """
            SELECT COALESCE(MAX(id), 0) FROM graph_edges WHERE src_entity_id = ?
            """,
            (eid,),
        )
        row = await cur.fetchone()
        if row is None or row[0] is None:
            return 0
        return int(row[0])

    async def max_message_sequence(self, session_id: int) -> int:
        assert self._conn is not None
        sid = int(session_id)
        cur = await self._conn.execute(
            """
            SELECT COALESCE(MAX(sequence), 0) FROM messages WHERE session_id = ?
            """,
            (sid,),
        )
        row = await cur.fetchone()
        if row is None or row[0] is None:
            return 0
        return int(row[0])

    def _trim_subgraph_pack_to_budget(
        self,
        pack: dict[str, Any],
        *,
        excerpt_floor_chars: int,
        max_total_json_chars: int,
    ) -> None:
        """Shrink outgoing_edges / linked_knowledge_excerpts until JSON fits ``max_total_json_chars``."""
        truncated_subject = False
        while True:
            blob = json.dumps(pack, ensure_ascii=False)
            if len(blob) <= max_total_json_chars:
                return
            ex_list = pack.get("linked_knowledge_excerpts")
            edges = pack.get("outgoing_edges")
            if not isinstance(ex_list, list):
                ex_list = []
                pack["linked_knowledge_excerpts"] = ex_list
            if not isinstance(edges, list):
                edges = []
                pack["outgoing_edges"] = edges
            if ex_list:
                ex_list.pop()
                continue
            if edges:
                dropped = edges.pop()
                eid_drop = int(dropped["id"]) if isinstance(dropped.get("id"), int) else None
                if eid_drop is not None:
                    pack["linked_knowledge_excerpts"] = [
                        x
                        for x in ex_list
                        if not (
                            isinstance(x, dict)
                            and int(x.get("edge_id") or 0) == eid_drop
                        )
                    ]
                continue
            shortened = False
            for it in ex_list:
                if isinstance(it, dict) and "content_excerpt" in it:
                    raw = str(it.get("content_excerpt") or "")
                    if len(raw) > excerpt_floor_chars:
                        it["content_excerpt"] = raw[:excerpt_floor_chars] + "…"
                        shortened = True
                        break
            if shortened:
                continue
            sub = pack.get("subject")
            if (
                not truncated_subject
                and isinstance(sub, dict)
                and isinstance(sub.get("payload_json"), dict)
                and sub["payload_json"]
            ):
                sub["payload_json"] = {"_truncated": True}
                truncated_subject = True
                continue
            return

    async def load_subject_subgraph_context_pack(
        self,
        entity_id: int,
        *,
        max_edges: int = 30,
        max_excerpt_items: int = 15,
        excerpt_max_chars: int = 800,
        max_total_json_chars: int = 60_000,
        mission_scope: int | None = None,
    ) -> dict[str, Any]:
        """
        Bounded JSON pack: subject entity, active outgoing edges + dst summaries,
        and knowledge excerpts (via edge_evidence) deduped by knowledge_id.
        When ``mission_scope`` is set, only edges whose ``mission_id`` matches or
        is legacy NULL (pre-backfill) are included.
        """
        assert self._conn is not None
        eid = int(entity_id)
        me = max(1, min(200, int(max_edges)))
        mex = max(1, min(100, int(max_excerpt_items)))
        cap = max(120, min(4000, int(excerpt_max_chars)))
        budget = max(4096, int(max_total_json_chars))

        subj = await self.get_entity_by_id(eid)
        if subj is None:
            return {
                "subject": None,
                "outgoing_edges": [],
                "linked_knowledge_excerpts": [],
            }
        subj_mid = subj.get("mission_id")
        cur_ge = await self._conn.execute("PRAGMA table_info(graph_edges)")
        has_ge_mission = "mission_id" in {str(r[1]) for r in await cur_ge.fetchall()}
        if mission_scope is not None:
            mid = int(mission_scope)
            if has_ge_mission:
                edge_mission_filter = (
                    " AND (ge.mission_id IS NULL OR ge.mission_id = ?) "
                )
                edge_args: tuple[int, ...] = (eid, GRAPH_EDGE_ACTIVE, mid, me)
            else:
                edge_mission_filter = ""
                edge_args = (eid, GRAPH_EDGE_ACTIVE, me)
        elif subj_mid is not None and has_ge_mission:
            mid = int(subj_mid)
            edge_mission_filter = " AND (ge.mission_id IS NULL OR ge.mission_id = ?) "
            edge_args = (eid, GRAPH_EDGE_ACTIVE, mid, me)
        else:
            edge_mission_filter = ""
            edge_args = (eid, GRAPH_EDGE_ACTIVE, me)

        cur = await self._conn.execute(
            f"""
            SELECT ge.id, ge.edge_type, ge.confidence, ge.source_url, ge.dst_entity_id,
                   e.id, e.type, e.name, e.normalized_name, e.payload_json, e.last_enriched_at
            FROM graph_edges ge
            INNER JOIN entities e ON e.id = ge.dst_entity_id
            WHERE ge.src_entity_id = ? AND ge.status = ?{edge_mission_filter}
            ORDER BY ge.id DESC
            LIMIT ?
            """,
            edge_args,
        )
        edge_rows = await cur.fetchall()
        edges_out: list[dict[str, Any]] = []
        edge_ids: list[int] = []
        for row in edge_rows:
            geid = int(row[0])
            edge_ids.append(geid)
            raw_dst_payload = str(row[9] or "{}")
            try:
                dst_payload: dict[str, Any] = json.loads(raw_dst_payload)
            except json.JSONDecodeError:
                dst_payload = {}
            le = row[10]
            edges_out.append(
                {
                    "id": geid,
                    "edge_type": str(row[1]),
                    "confidence": float(row[2]),
                    "source_url": str(row[3]).strip() if row[3] is not None else "",
                    "dst_entity_id": int(row[4]),
                    "dst": {
                        "id": int(row[5]),
                        "type": str(row[6]),
                        "name": str(row[7]),
                        "normalized_name": str(row[8]),
                        "payload_json": dst_payload,
                        "last_enriched_at": le if le is not None else None,
                    },
                }
            )

        excerpts: list[dict[str, Any]] = []
        if edge_ids:
            placeholders = ",".join("?" * len(edge_ids))
            cur2 = await self._conn.execute(
                f"""
                SELECT ee.edge_id, ki.id, ki.content_excerpt
                FROM edge_evidence ee
                INNER JOIN knowledge_items ki ON ki.id = ee.knowledge_id
                WHERE ee.edge_id IN ({placeholders})
                ORDER BY ee.edge_id DESC, ee.id DESC
                """,
                tuple(edge_ids),
            )
            seen_k: set[int] = set()
            for erow in await cur2.fetchall():
                kid = int(erow[1])
                if kid in seen_k:
                    continue
                seen_k.add(kid)
                raw_ex = str(erow[2] or "")
                ex = raw_ex if len(raw_ex) <= cap else raw_ex[:cap] + "…"
                excerpts.append(
                    {
                        "knowledge_id": kid,
                        "edge_id": int(erow[0]),
                        "content_excerpt": ex,
                    }
                )
                if len(excerpts) >= mex:
                    break

        pack: dict[str, Any] = {
            "subject": {
                "id": subj["id"],
                "type": subj["type"],
                "name": subj["name"],
                "normalized_name": subj["normalized_name"],
                "payload_json": subj["payload_json"],
                "last_enriched_at": subj["last_enriched_at"],
            },
            "outgoing_edges": edges_out,
            "linked_knowledge_excerpts": excerpts,
        }
        self._trim_subgraph_pack_to_budget(
            pack, excerpt_floor_chars=200, max_total_json_chars=budget
        )
        return pack

    async def list_enrichment_excerpts_for_entity(
        self,
        entity_id: int,
        *,
        limit: int = 12,
        excerpt_max_chars: int = 800,
    ) -> list[dict[str, Any]]:
        """
        Knowledge excerpts linked as evidence on active outgoing edges from entity_id
        (newest edges first), for DRAFT grounding.
        """
        assert self._conn is not None
        eid = int(entity_id)
        lim = max(1, min(50, int(limit)))
        cap = max(120, min(4000, int(excerpt_max_chars)))
        cur = await self._conn.execute(
            """
            SELECT ki.id, ki.content_excerpt, ge.source_url
            FROM graph_edges ge
            INNER JOIN edge_evidence ee ON ee.edge_id = ge.id
            INNER JOIN knowledge_items ki ON ki.id = ee.knowledge_id
            WHERE ge.src_entity_id = ? AND ge.status = ?
            ORDER BY ge.id DESC, ee.id DESC
            """,
            (eid, GRAPH_EDGE_ACTIVE),
        )
        rows = await cur.fetchall()
        seen: set[int] = set()
        out: list[dict[str, Any]] = []
        for row in rows:
            kid = int(row[0])
            if kid in seen:
                continue
            seen.add(kid)
            raw_ex = str(row[1] or "")
            ex = raw_ex if len(raw_ex) <= cap else raw_ex[:cap] + "…"
            su = row[2]
            out.append(
                {
                    "knowledge_id": kid,
                    "content_excerpt": ex,
                    "source_url": str(su).strip() if su is not None else "",
                }
            )
            if len(out) >= lim:
                break
        return out

    async def list_subjects_with_classified_category(
        self,
        *,
        entity_types: frozenset[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        """Matrix router: subject entities (types) linked to a taxonomy category.

        Links may be ``classified_as`` or ``under_category`` (graph-lite emits the latter).
        Destination must be an entity with ``type`` category.
        """
        assert self._conn is not None
        if not entity_types:
            return []
        lim = max(1, min(int(limit), 10_000))
        placeholders = ",".join("?" * len(entity_types))
        types_lower = [str(t).strip().lower() for t in entity_types]
        cur = await self._conn.execute(
            f"""
            SELECT DISTINCT e.id, e.type, e.name, e.normalized_name, e.payload_json,
                   e.last_enriched_at, c.name AS category_name
            FROM entities e
            JOIN graph_edges ge
              ON ge.src_entity_id = e.id
             AND lower(ge.edge_type) IN ('classified_as', 'under_category')
             AND ge.status = ?
            JOIN entities c ON c.id = ge.dst_entity_id AND lower(c.type) = 'category'
            WHERE lower(e.type) IN ({placeholders})
            ORDER BY e.id ASC, category_name ASC
            LIMIT ?
            """,
            (GRAPH_EDGE_ACTIVE, *types_lower, lim),
        )
        rows = await cur.fetchall()
        return self._subject_rows_category_join(rows)

    async def list_subjects_with_classified_category_recent_for_planner(
        self,
        *,
        entity_types: frozenset[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        """Same subject join as legacy matrix-scan; **recent** ordering for prioritized planner."""

        assert self._conn is not None
        if not entity_types:
            return []
        lim = max(1, min(int(limit), 10_000))
        placeholders = ",".join("?" * len(entity_types))
        types_lower = [str(t).strip().lower() for t in entity_types]
        cur = await self._conn.execute(
            f"""
            SELECT DISTINCT e.id, e.type, e.name, e.normalized_name, e.payload_json,
                   e.last_enriched_at, c.name AS category_name
            FROM entities e
            JOIN graph_edges ge
              ON ge.src_entity_id = e.id
             AND lower(ge.edge_type) IN ('classified_as', 'under_category')
             AND ge.status = ?
            JOIN entities c ON c.id = ge.dst_entity_id AND lower(c.type) = 'category'
            WHERE lower(e.type) IN ({placeholders})
            ORDER BY (e.last_enriched_at IS NULL) ASC,
                     e.last_enriched_at DESC,
                     e.id DESC,
                     category_name ASC
            LIMIT ?
            """,
            (GRAPH_EDGE_ACTIVE, *types_lower, lim),
        )
        rows = await cur.fetchall()
        return self._subject_rows_category_join(rows)

    def _subject_rows_category_join(self, rows: list[Any]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for row in rows:
            raw = str(row[4] or "{}")
            try:
                payload: dict[str, Any] = json.loads(raw)
            except json.JSONDecodeError:
                payload = {}
            le = row[5]
            out.append(
                {
                    "id": int(row[0]),
                    "type": str(row[1]),
                    "name": str(row[2]),
                    "normalized_name": str(row[3]),
                    "payload_json": payload,
                    "last_enriched_at": le if le is not None else None,
                    "category_code": str(row[6] or "").strip().lower(),
                }
            )
        return out

    async def insert_edge_evidence(
        self,
        *,
        edge_id: int,
        knowledge_id: int,
        span_json: dict[str, Any] | None = None,
    ) -> int:
        assert self._conn is not None
        span = json.dumps(span_json, ensure_ascii=False) if span_json is not None else None
        cur = await self._conn.execute(
            """
            INSERT INTO edge_evidence (edge_id, knowledge_id, span_json)
            VALUES (?, ?, ?)
            """,
            (edge_id, knowledge_id, span),
        )
        await self._conn.commit()
        return int(cur.lastrowid)

    async def link_edge_evidence_upsert(
        self,
        *,
        edge_id: int,
        knowledge_id: int,
        span_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT id FROM edge_evidence
            WHERE edge_id = ? AND knowledge_id = ?
            LIMIT 1
            """,
            (edge_id, knowledge_id),
        )
        row = await cur.fetchone()
        span = json.dumps(span_json, ensure_ascii=False) if span_json is not None else None
        if row is not None:
            edge_evidence_id = int(row[0])
            if span_json is not None:
                await self._conn.execute(
                    "UPDATE edge_evidence SET span_json = ? WHERE id = ?",
                    (span, edge_evidence_id),
                )
                await self._conn.commit()
            return {"edge_evidence_id": edge_evidence_id, "upserted": False}
        edge_evidence_id = await self.insert_edge_evidence(
            edge_id=edge_id,
            knowledge_id=knowledge_id,
            span_json=span_json,
        )
        return {"edge_evidence_id": edge_evidence_id, "upserted": True}

    async def list_edge_evidence(self, edge_id: int) -> list[dict[str, Any]]:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT id, edge_id, knowledge_id, span_json, created_at
            FROM edge_evidence
            WHERE edge_id = ?
            ORDER BY id ASC
            """,
            (edge_id,),
        )
        rows = await cur.fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            span = None
            if row[3] is not None:
                try:
                    span = json.loads(str(row[3]))
                except json.JSONDecodeError:
                    span = None
            out.append(
                {
                    "id": int(row[0]),
                    "edge_id": int(row[1]),
                    "knowledge_id": int(row[2]),
                    "span_json": span,
                    "created_at": str(row[4]),
                }
            )
        return out

    async def mark_edge_invalid(self, edge_id: int, reason: str) -> None:
        assert self._conn is not None
        cur = await self._conn.execute(
            "UPDATE graph_edges SET status = ? WHERE id = ?",
            (GRAPH_EDGE_INVALID, edge_id),
        )
        if cur.rowcount == 0:
            raise LookupError(f"no graph edge with id={edge_id}")
        await self._conn.commit()
        await self.append_action_log(
            "graph_edge_invalidated",
            {"edge_id": edge_id, "reason": str(reason)},
        )

    async def delete_knowledge_source(self, source_id: int) -> None:
        """Delete a registered source and cascade knowledge_items (not synthesis refs)."""
        assert self._conn is not None
        await self._conn.execute(
            "DELETE FROM knowledge_sources WHERE id = ?",
            (source_id,),
        )
        await self._conn.commit()

    async def find_workflow_by_idempotency(
        self, kind: str, idempotency_key: str
    ) -> dict[str, Any] | None:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT id, kind, goal_text, params_json, idempotency_key, status, parent_task_id,
                   mission_id, created_at, updated_at
            FROM workflows WHERE kind = ? AND idempotency_key = ?
            LIMIT 1
            """,
            (str(kind).strip(), str(idempotency_key).strip()),
        )
        row = await cur.fetchone()
        if not row:
            return None
        return self._workflow_row_to_dict(row)

    async def get_workflow_by_parent_task_id(self, parent_task_id: int) -> dict[str, Any] | None:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT id, kind, goal_text, params_json, idempotency_key, status, parent_task_id,
                   mission_id, created_at, updated_at
            FROM workflows WHERE parent_task_id = ? ORDER BY id DESC LIMIT 1
            """,
            (parent_task_id,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        return self._workflow_row_to_dict(row)

    async def get_workflow_by_id(self, workflow_id: int) -> dict[str, Any] | None:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT id, kind, goal_text, params_json, idempotency_key, status, parent_task_id,
                   mission_id, created_at, updated_at
            FROM workflows WHERE id = ?
            """,
            (workflow_id,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        return self._workflow_row_to_dict(row)

    def _workflow_row_to_dict(self, row: tuple[Any, ...]) -> dict[str, Any]:
        params_raw = str(row[3] or "{}")
        try:
            params_obj = json.loads(params_raw)
        except json.JSONDecodeError:
            params_obj = {}
        mission_raw = row[7]
        return {
            "id": int(row[0]),
            "kind": str(row[1]),
            "goal_text": str(row[2]),
            "params_json": params_obj,
            "idempotency_key": row[4],
            "status": str(row[5]),
            "parent_task_id": int(row[6]) if row[6] is not None else None,
            "mission_id": int(mission_raw) if mission_raw is not None else None,
            "created_at": str(row[8]),
            "updated_at": str(row[9]),
        }

    async def list_workflow_steps(self, workflow_id: int) -> list[dict[str, Any]]:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT id, workflow_id, step_index, step_type, status, input_json, output_json,
                   error, idempotency_key, task_id, attempt_count, created_at, updated_at
            FROM workflow_steps WHERE workflow_id = ?
            ORDER BY step_index ASC
            """,
            (workflow_id,),
        )
        rows = await cur.fetchall()
        return [self._workflow_step_row_to_dict(row) for row in rows]

    def _workflow_step_row_to_dict(self, row: tuple[Any, ...]) -> dict[str, Any]:
        def _parse(j: str) -> dict[str, Any]:
            try:
                o = json.loads(str(j or "{}"))
                return o if isinstance(o, dict) else {}
            except json.JSONDecodeError:
                return {}

        return {
            "id": int(row[0]),
            "workflow_id": int(row[1]),
            "step_index": int(row[2]),
            "step_type": str(row[3]),
            "status": str(row[4]),
            "input_json": _parse(str(row[5] or "{}")),
            "output_json": _parse(str(row[6] or "{}")),
            "error": str(row[7] or ""),
            "idempotency_key": row[8],
            "task_id": int(row[9]) if row[9] is not None else None,
            "attempt_count": int(row[10] or 0),
            "created_at": str(row[11]),
            "updated_at": str(row[12]),
        }

    async def enqueue_workflow(
        self,
        *,
        kind: str,
        goal_text: str,
        params_json: dict[str, Any],
        parent_task_id: int,
        idempotency_key: str | None,
        steps: list[dict[str, Any]],
        mission_id: int | None = None,
    ) -> tuple[int, bool]:
        """
        Insert workflow + steps. Idempotent when idempotency_key is set (non-empty).
        Returns (workflow_id, created_new).
        """
        assert self._conn is not None
        kind_s = str(kind).strip()
        if not kind_s:
            raise ValueError("workflow kind required")
        key_s = idempotency_key.strip() if idempotency_key else None
        if key_s:
            cur = await self._conn.execute(
                "SELECT id FROM workflows WHERE kind = ? AND idempotency_key = ?",
                (kind_s, key_s),
            )
            row = await cur.fetchone()
            if row:
                return int(row[0]), False

        params_s = json.dumps(params_json, ensure_ascii=False)
        try:
            cur = await self._conn.execute(
                """
                INSERT INTO workflows (
                    kind, goal_text, params_json, idempotency_key, status, parent_task_id, mission_id
                ) VALUES (?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    kind_s,
                    str(goal_text).strip(),
                    params_s,
                    key_s,
                    parent_task_id,
                    int(mission_id) if mission_id is not None else None,
                ),
            )
            wf_id = int(cur.lastrowid)
        except aiosqlite.IntegrityError:
            await self._conn.rollback()
            cur = await self._conn.execute(
                "SELECT id FROM workflows WHERE kind = ? AND idempotency_key = ?",
                (kind_s, key_s),
            )
            row = await cur.fetchone()
            if not row:
                raise
            return int(row[0]), False

        for st in steps:
            idx = int(st["step_index"])
            stype = str(st["step_type"]).strip().upper()
            if stype not in WORKFLOW_VALID_STEP_TYPES:
                await self._conn.execute("DELETE FROM workflows WHERE id = ?", (wf_id,))
                await self._conn.commit()
                raise ValueError(f"invalid step_type: {stype!r}")
            inp = st.get("input_json") if isinstance(st.get("input_json"), dict) else {}
            sid_key = st.get("idempotency_key")
            sid_key_s = str(sid_key).strip() if sid_key else None
            await self._conn.execute(
                """
                INSERT INTO workflow_steps (
                    workflow_id, step_index, step_type, status, input_json, idempotency_key
                ) VALUES (?, ?, ?, 'pending', ?, ?)
                """,
                (wf_id, idx, stype, json.dumps(inp, ensure_ascii=False), sid_key_s),
            )
        await self._conn.commit()
        return wf_id, True

    async def update_workflow_row(
        self,
        workflow_id: int,
        *,
        status: str | None = None,
    ) -> None:
        assert self._conn is not None
        if status is None:
            return
        st = str(status).strip().lower()
        if st not in ("pending", "running", "completed", "failed"):
            raise ValueError(f"invalid workflow status: {status!r}")
        await self._conn.execute(
            """
            UPDATE workflows SET status = ?, updated_at = datetime('now') WHERE id = ?
            """,
            (st, workflow_id),
        )
        await self._conn.commit()

    async def merge_workflow_params_json(
        self, workflow_id: int, patch: dict[str, Any]
    ) -> None:
        """Shallow-merge ``patch`` into ``workflows.params_json`` (resume-safe)."""
        assert self._conn is not None
        if not patch:
            return
        cur = await self._conn.execute(
            "SELECT params_json FROM workflows WHERE id = ?",
            (workflow_id,),
        )
        row = await cur.fetchone()
        if row is None:
            raise ValueError(f"no workflow with id={workflow_id}")
        try:
            base = json.loads(str(row[0] or "{}"))
        except json.JSONDecodeError:
            base = {}
        if not isinstance(base, dict):
            base = {}
        merged = {**base, **patch}
        await self._conn.execute(
            """
            UPDATE workflows SET params_json = ?, updated_at = datetime('now') WHERE id = ?
            """,
            (json.dumps(merged, ensure_ascii=False), workflow_id),
        )
        await self._conn.commit()

    async def update_workflow_step_row(
        self,
        step_row_id: int,
        *,
        status: str | None = None,
        output_json: dict[str, Any] | None = None,
        error: str | None = None,
        increment_attempt: bool = False,
    ) -> None:
        assert self._conn is not None
        sets: list[str] = []
        args: list[Any] = []
        if status is not None:
            st = str(status).strip().lower()
            if st not in ("pending", "running", "completed", "failed", "skipped"):
                raise ValueError(f"invalid step status: {status!r}")
            sets.append("status = ?")
            args.append(st)
        if output_json is not None:
            sets.append("output_json = ?")
            args.append(json.dumps(output_json, ensure_ascii=False))
        if error is not None:
            sets.append("error = ?")
            args.append(str(error))
        if increment_attempt:
            sets.append("attempt_count = attempt_count + 1")
        if not sets:
            return
        sets.append("updated_at = datetime('now')")
        args.append(step_row_id)
        await self._conn.execute(
            f"UPDATE workflow_steps SET {', '.join(sets)} WHERE id = ?",
            args,
        )
        await self._conn.commit()

    async def retry_failed_workflow(
        self,
        workflow_id: int,
        *,
        reason: str = "manual_retry",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Resume-safe reset: workflows.status pending, tail steps pending/error cleared,
        parent goal task pending. Single transaction unless dry_run (read-only plan).
        Eligible only when workflow.status == failed, parent_task_id set, steps exist,
        and not every step completed.
        """
        assert self._conn is not None

        wf = await self.get_workflow_by_id(workflow_id)
        if wf is None:
            return {"error": f"no workflow with id={workflow_id}"}
        wf_status = str(wf["status"]).strip().lower()
        if wf_status != "failed":
            return {"error": f"workflow_retry requires workflows.status=='failed', got {wf_status!r}"}

        parent_task_id = wf.get("parent_task_id")
        if parent_task_id is None:
            return {"error": "workflow_retry requires workflows.parent_task_id"}

        pid = int(parent_task_id)
        try:
            task_before = await self.get_goal_task(pid)
        except (LookupError, ValueError) as e:
            return {"error": f"invalid parent task: {e}"}

        steps = await self.list_workflow_steps(workflow_id)
        if not steps:
            return {"error": "workflow has no steps"}

        if all(str(s["status"]).lower() == "completed" for s in steps):
            return {"error": "ineligible: all steps completed"}

        tail_start_idx: int | None = None
        for i, s in enumerate(steps):
            if str(s["status"]).lower() != "completed":
                tail_start_idx = i
                break
        assert tail_start_idx is not None
        tail = steps[tail_start_idx:]
        step_ids_reset = [int(s["id"]) for s in tail]

        reason_s = str(reason).strip() or "manual_retry"
        payload_base: dict[str, Any] = {
            "workflow_id": workflow_id,
            "parent_task_id": pid,
            "reason": reason_s,
            "dry_run": dry_run,
            "host": socket.gethostname(),
            "operator": os.getenv("USER") or "unknown",
        }

        plan: dict[str, Any] = {
            "workflow_id": workflow_id,
            "workflow_status_before": wf["status"],
            "workflow_status_after": "pending",
            "parent_task_id": pid,
            "task_status_before": task_before["status"],
            "task_status_after": "pending",
            "tail_start_step_index": int(steps[tail_start_idx]["step_index"]),
            "step_row_ids_pending_reset": step_ids_reset,
        }

        if dry_run:
            return {"ok": True, "dry_run": True, "plan": plan, "payload_preview": payload_base}

        try:
            await self._conn.execute("BEGIN IMMEDIATE")
            await self._conn.execute(
                """
                UPDATE workflows SET status = ?, updated_at = datetime('now') WHERE id = ?
                """,
                ("pending", workflow_id),
            )
            for sid in step_ids_reset:
                await self._conn.execute(
                    """
                    UPDATE workflow_steps SET status = 'pending', error = '',
                    updated_at = datetime('now') WHERE id = ?
                    """,
                    (sid,),
                )
            await self._conn.execute(
                """
                UPDATE tasks
                SET status = 'pending', current_output = '', updated_at = datetime('now')
                WHERE id = ?
                """,
                (pid,),
            )
            payload = {**payload_base, "dry_run": False}
            await self._conn.execute(
                """
                INSERT INTO action_log (session_id, kind, payload_json)
                VALUES (?, ?, ?)
                """,
                (
                    None,
                    "workflow_retry_requested",
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
            await self._conn.commit()
        except Exception:
            await self._conn.rollback()
            raise

        return {
            "ok": True,
            "dry_run": False,
            "workflow_id": workflow_id,
            "parent_task_id": pid,
            "plan": plan,
        }

    async def list_recent_knowledge_item_ids(
        self, *, limit: int, mission_scope: int | None = None
    ) -> list[int]:
        """Most recently ingested knowledge_items ids (non-tombstoned)."""
        assert self._conn is not None
        lim = max(1, min(int(limit), 500))
        mj_join, mj_args = self._knowledge_mission_source_join_clause(
            mission_scope, ki_alias="ki"
        )
        cur = await self._conn.execute(
            f"""
            SELECT ki.id FROM knowledge_items ki{mj_join}
            WHERE ki.tombstoned = 0
            ORDER BY ki.ingested_at DESC, ki.id DESC
            LIMIT ?
            """,
            (*mj_args, lim),
        )
        rows = await cur.fetchall()
        return [int(r[0]) for r in rows]

    # --- system_jobs (job plane) ---

    SYSTEM_JOB_KIND_GOAL_RUN_TURN = "goal.run_turn"
    SYSTEM_JOB_KIND_NOOP_PING = "noop.ping"
    SYSTEM_JOB_KIND_WORKFLOW_START = "workflow.start"
    SYSTEM_JOB_KIND_INGEST_RUN = "ingest.run"
    SYSTEM_JOB_KIND_TICK_GSC_KEYWORD = "tick.gsc_keyword_publish"
    SYSTEM_JOB_KIND_MATRIX_SCAN = "matrix.scan"

    async def get_task_goal_dispatch_generation(self, task_id: int) -> int:
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT IFNULL(goal_dispatch_generation, 0) FROM tasks WHERE id = ?",
            (int(task_id),),
        )
        row = await cur.fetchone()
        return int(row[0]) if row is not None else 0

    async def insert_system_job(
        self,
        *,
        kind: str,
        payload_json: dict[str, Any],
        mission_id: int | None = None,
        idempotency_key: str | None = None,
        run_after: str | None = None,
        priority: int = 0,
        max_attempts: int = 8,
        correlation_id: str | None = None,
    ) -> int:
        """Insert a pending system job. On idempotency conflict returns existing id."""
        assert self._conn is not None
        payload_s = json.dumps(payload_json, ensure_ascii=False)
        key = idempotency_key.strip() if idempotency_key else None
        try:
            cur = await self._conn.execute(
                """
                INSERT INTO system_jobs (
                    kind, mission_id, payload_json, idempotency_key, status,
                    max_attempts, run_after, priority, correlation_id
                )
                VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?)
                """,
                (
                    str(kind).strip(),
                    mission_id,
                    payload_s,
                    key,
                    int(max_attempts),
                    run_after,
                    int(priority),
                    correlation_id,
                ),
            )
            await self._conn.commit()
            return int(cur.lastrowid)
        except sqlite3.IntegrityError:
            if not key:
                raise
            cur2 = await self._conn.execute(
                "SELECT id FROM system_jobs WHERE idempotency_key = ? LIMIT 1",
                (key,),
            )
            row = await cur2.fetchone()
            if row is None:
                raise
            return int(row[0])

    async def _goal_run_turn_inflight_exists(self, task_id: int) -> bool:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT 1 FROM system_jobs
            WHERE kind = ?
              AND json_extract(payload_json, '$.task_id') = ?
              AND status IN ('pending', 'running')
            LIMIT 1
            """,
            (self.SYSTEM_JOB_KIND_GOAL_RUN_TURN, int(task_id)),
        )
        return await cur.fetchone() is not None

    async def try_enqueue_goal_run_turn(self, task_id: int) -> int | None:
        """
        If task is a pending goal with no in-flight goal.run_turn job, enqueue one.
        Returns new system_jobs.id or None if nothing to do.
        """
        assert self._conn is not None
        tid = int(task_id)
        try:
            await self._conn.execute("BEGIN IMMEDIATE")
            if await self._goal_run_turn_inflight_exists(tid):
                await self._conn.commit()
                return None
            cur = await self._conn.execute(
                """
                SELECT id, mission_id, goal, status, task_kind
                FROM tasks WHERE id = ?
                """,
                (tid,),
            )
            row = await cur.fetchone()
            if row is None or str(row[4]) != TASK_KIND_GOAL or str(row[3]) != "pending":
                await self._conn.commit()
                return None
            mid_raw = row[1]
            goal = str(row[2] or "")
            curu = await self._conn.execute(
                """
                UPDATE tasks SET
                    goal_dispatch_generation = IFNULL(goal_dispatch_generation, 0) + 1,
                    updated_at = datetime('now')
                WHERE id = ? AND status = 'pending' AND task_kind = ?
                """,
                (tid, TASK_KIND_GOAL),
            )
            if curu.rowcount != 1:
                await self._conn.rollback()
                return None
            curg = await self._conn.execute(
                "SELECT IFNULL(goal_dispatch_generation, 0) FROM tasks WHERE id = ?",
                (tid,),
            )
            grow = await curg.fetchone()
            gen = int(grow[0]) if grow is not None else 1
            mid = int(mid_raw) if mid_raw is not None else None
            payload = {
                "task_id": tid,
                "turn_generation": gen,
                "goal_preview": goal[:500],
            }
            idem = f"goal.run_turn:{tid}:{gen}"
            cur2 = await self._conn.execute(
                """
                INSERT INTO system_jobs (
                    kind, mission_id, payload_json, idempotency_key, status, max_attempts
                )
                VALUES (?, ?, ?, ?, 'pending', 8)
                """,
                (
                    self.SYSTEM_JOB_KIND_GOAL_RUN_TURN,
                    mid,
                    json.dumps(payload, ensure_ascii=False),
                    idem,
                ),
            )
            jid = int(cur2.lastrowid)
            await self._conn.commit()
            return jid
        except Exception:
            await self._conn.rollback()
            raise

    async def _ingest_run_inflight_exists(self, ingest_job_id: int) -> bool:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT 1 FROM system_jobs
            WHERE kind = ?
              AND json_extract(payload_json, '$.ingest_job_id') = ?
              AND status IN ('pending', 'running')
            LIMIT 1
            """,
            (self.SYSTEM_JOB_KIND_INGEST_RUN, int(ingest_job_id)),
        )
        return await cur.fetchone() is not None

    async def try_enqueue_ingest_run(
        self, ingest_job_id: int, *, mission_id: int | None = None
    ) -> int | None:
        """
        Enqueue ``ingest.run`` for a pending/failed ingest_jobs row (not completed).
        At most one pending/running ``ingest.run`` per ``ingest_job_id``.
        Returns new ``system_jobs.id`` or ``None`` if nothing to enqueue.
        """
        assert self._conn is not None
        iid = int(ingest_job_id)
        try:
            await self._conn.execute("BEGIN IMMEDIATE")
            if await self._ingest_run_inflight_exists(iid):
                await self._conn.commit()
                return None
            row = await self.get_ingest_job_row(iid)
            if row is None:
                await self._conn.commit()
                return None
            st = str(row.get("status") or "")
            if st == "completed":
                await self._conn.commit()
                return None
            payload = {"ingest_job_id": iid}
            cur2 = await self._conn.execute(
                """
                INSERT INTO system_jobs (
                    kind, mission_id, payload_json, idempotency_key, status, max_attempts
                )
                VALUES (?, ?, ?, NULL, 'pending', 8)
                """,
                (
                    self.SYSTEM_JOB_KIND_INGEST_RUN,
                    mission_id,
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
            jid = int(cur2.lastrowid)
            await self._conn.commit()
            return jid
        except Exception:
            await self._conn.rollback()
            raise

    async def ensure_pending_goal_system_jobs(self) -> int:
        """Enqueue goal.run_turn for every pending goal task missing one. Returns insert count."""
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT id FROM tasks
            WHERE task_kind = ? AND status = 'pending'
            ORDER BY id ASC
            """,
            (TASK_KIND_GOAL,),
        )
        rows = await cur.fetchall()
        n = 0
        for (tid,) in rows:
            jid = await self.try_enqueue_goal_run_turn(int(tid))
            if jid is not None:
                n += 1
        return n

    async def reclaim_expired_system_jobs(self) -> int:
        """
        Expired leases: increment attempt_count; requeue as pending or mark dead.
        Returns number of rows updated.
        """
        assert self._conn is not None
        await self._conn.execute("BEGIN IMMEDIATE")
        cur = await self._conn.execute(
            """
            UPDATE system_jobs SET
                attempt_count = attempt_count + 1,
                status = CASE
                    WHEN attempt_count + 1 >= max_attempts THEN 'dead'
                    ELSE 'pending'
                END,
                error = CASE
                    WHEN attempt_count + 1 >= max_attempts
                        THEN 'lease_expired_worker_lost'
                    ELSE COALESCE(error, '')
                END,
                lease_owner = '',
                lease_expires_at = NULL,
                updated_at = datetime('now')
            WHERE status = 'running'
              AND lease_expires_at IS NOT NULL
              AND datetime(lease_expires_at) < datetime('now')
            """
        )
        n = cur.rowcount if cur.rowcount is not None and cur.rowcount >= 0 else 0
        await self._conn.commit()
        return int(n)

    async def claim_next_system_job(
        self,
        worker_id: str,
        *,
        lease_seconds: int = 300,
    ) -> dict[str, Any] | None:
        """Atomically reclaim stale leases, then claim one pending job (compare-and-set)."""
        assert self._conn is not None
        wid = (worker_id or "worker").strip() or "worker"
        lease = max(30, int(lease_seconds))
        await self._conn.execute("BEGIN IMMEDIATE")
        await self._conn.execute(
            """
            UPDATE system_jobs SET
                attempt_count = attempt_count + 1,
                status = CASE
                    WHEN attempt_count + 1 >= max_attempts THEN 'dead'
                    ELSE 'pending'
                END,
                error = CASE
                    WHEN attempt_count + 1 >= max_attempts
                        THEN 'lease_expired_worker_lost'
                    ELSE COALESCE(error, '')
                END,
                lease_owner = '',
                lease_expires_at = NULL,
                updated_at = datetime('now')
            WHERE status = 'running'
              AND lease_expires_at IS NOT NULL
              AND datetime(lease_expires_at) < datetime('now')
            """
        )
        cur = await self._conn.execute(
            """
            SELECT id FROM system_jobs
            WHERE status = 'pending'
              AND (run_after IS NULL OR trim(run_after) = ''
                   OR datetime(run_after) <= datetime('now'))
            ORDER BY priority DESC, id ASC
            LIMIT 1
            """
        )
        row = await cur.fetchone()
        if row is None:
            await self._conn.commit()
            return None
        jid = int(row[0])
        cur2 = await self._conn.execute(
            f"""
            UPDATE system_jobs SET
                status = 'running',
                lease_owner = ?,
                lease_expires_at = datetime('now', '+{lease} seconds'),
                updated_at = datetime('now'),
                started_at = COALESCE(started_at, datetime('now'))
            WHERE id = ? AND status = 'pending'
            """,
            (wid, jid),
        )
        if cur2.rowcount != 1:
            await self._conn.commit()
            return None
        cur3 = await self._conn.execute(
            """
            SELECT id, kind, mission_id, payload_json, idempotency_key, status,
                   attempt_count, max_attempts, error, lease_owner, lease_expires_at,
                   run_after, priority, correlation_id, created_at, updated_at, started_at
            FROM system_jobs WHERE id = ?
            """,
            (jid,),
        )
        r = await cur3.fetchone()
        await self._conn.commit()
        if r is None:
            return None
        return self._system_job_row_to_dict(r)

    def _system_job_row_to_dict(self, r: Any) -> dict[str, Any]:
        raw = str(r[3] or "{}")
        try:
            payload: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            payload = {}
        return {
            "id": int(r[0]),
            "kind": str(r[1]),
            "mission_id": int(r[2]) if r[2] is not None else None,
            "payload_json": payload,
            "idempotency_key": str(r[4]) if r[4] is not None else None,
            "status": str(r[5]),
            "attempt_count": int(r[6]),
            "max_attempts": int(r[7]),
            "error": str(r[8] or ""),
            "lease_owner": str(r[9] or ""),
            "lease_expires_at": str(r[10]) if r[10] is not None else None,
            "run_after": str(r[11]) if r[11] is not None else None,
            "priority": int(r[12]),
            "correlation_id": str(r[13]) if r[13] is not None else None,
            "created_at": str(r[14]),
            "updated_at": str(r[15]),
            "started_at": str(r[16]) if r[16] is not None else None,
        }

    async def get_system_job(self, job_id: int) -> dict[str, Any] | None:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT id, kind, mission_id, payload_json, idempotency_key, status,
                   attempt_count, max_attempts, error, lease_owner, lease_expires_at,
                   run_after, priority, correlation_id, created_at, updated_at, started_at
            FROM system_jobs WHERE id = ?
            """,
            (int(job_id),),
        )
        row = await cur.fetchone()
        return None if row is None else self._system_job_row_to_dict(row)

    async def heartbeat_system_job(
        self,
        job_id: int,
        worker_id: str,
        *,
        lease_seconds: int = 300,
    ) -> bool:
        assert self._conn is not None
        wid = (worker_id or "").strip()
        lease = max(30, int(lease_seconds))
        cur = await self._conn.execute(
            f"""
            UPDATE system_jobs SET
                lease_expires_at = datetime('now', '+{lease} seconds'),
                updated_at = datetime('now')
            WHERE id = ? AND status = 'running' AND lease_owner = ?
            """,
            (int(job_id), wid),
        )
        await self._conn.commit()
        return cur.rowcount == 1

    async def complete_system_job(self, job_id: int, worker_id: str) -> bool:
        assert self._conn is not None
        wid = (worker_id or "").strip()
        cur = await self._conn.execute(
            """
            UPDATE system_jobs SET
                status = 'completed',
                lease_owner = '',
                lease_expires_at = NULL,
                error = '',
                updated_at = datetime('now')
            WHERE id = ? AND status = 'running' AND lease_owner = ?
            """,
            (int(job_id), wid),
        )
        await self._conn.commit()
        return cur.rowcount == 1

    async def fail_system_job(
        self,
        job_id: int,
        worker_id: str,
        error: str,
        *,
        terminal: bool = True,
    ) -> bool:
        assert self._conn is not None
        wid = (worker_id or "").strip()
        err = str(error or "")[:4000]
        st = "failed" if terminal else "pending"
        cur = await self._conn.execute(
            f"""
            UPDATE system_jobs SET
                status = ?,
                error = ?,
                lease_owner = '',
                lease_expires_at = NULL,
                updated_at = datetime('now')
            WHERE id = ? AND status = 'running' AND lease_owner = ?
            """,
            (st, err, int(job_id), wid),
        )
        await self._conn.commit()
        return cur.rowcount == 1

    async def cancel_system_job(self, job_id: int) -> bool:
        """Cancel a pending job (operator)."""
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            UPDATE system_jobs SET
                status = 'cancelled',
                updated_at = datetime('now'),
                lease_owner = '',
                lease_expires_at = NULL
            WHERE id = ? AND status = 'pending'
            """,
            (int(job_id),),
        )
        await self._conn.commit()
        return cur.rowcount == 1

    async def retry_system_job_clone(self, job_id: int) -> int | None:
        """Insert a new pending job with same kind/payload; new idempotency suffix."""
        assert self._conn is not None
        row = await self.get_system_job(int(job_id))
        if row is None:
            return None
        base = row.get("idempotency_key") or f"retry:{job_id}"
        new_key = f"{base}:retry:{int(datetime.now().timestamp())}"
        return await self.insert_system_job(
            kind=str(row["kind"]),
            payload_json=dict(row.get("payload_json") or {}),
            mission_id=row.get("mission_id"),
            idempotency_key=new_key,
            priority=int(row.get("priority") or 0),
            max_attempts=int(row.get("max_attempts") or 8),
        )

    async def list_system_jobs(
        self,
        *,
        limit: int = 100,
        status: str | None = None,
        mission_id: int | None = None,
        kind: str | None = None,
    ) -> list[dict[str, Any]]:
        assert self._conn is not None
        lim = max(1, min(int(limit), 500))
        where: list[str] = ["1=1"]
        args: list[Any] = []
        if status is not None:
            where.append("status = ?")
            args.append(str(status).strip().lower())
        if mission_id is not None:
            where.append("mission_id = ?")
            args.append(int(mission_id))
        if kind is not None:
            where.append("kind = ?")
            args.append(str(kind).strip())
        wsql = " AND ".join(where)
        cur = await self._conn.execute(
            f"""
            SELECT id, kind, mission_id, payload_json, idempotency_key, status,
                   attempt_count, max_attempts, error, lease_owner, lease_expires_at,
                   run_after, priority, correlation_id, created_at, updated_at, started_at
            FROM system_jobs
            WHERE {wsql}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*args, lim),
        )
        rows = await cur.fetchall()
        return [self._system_job_row_to_dict(r) for r in rows]

    async def get_ingest_job_row(self, job_id: int) -> dict[str, Any] | None:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT id, kind, params_json, idempotency_key, status, error,
                   started_at, completed_at, created_at
            FROM ingest_jobs WHERE id = ?
            """,
            (int(job_id),),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        raw = str(row[2] or "{}")
        try:
            params: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            params = {}
        return {
            "id": int(row[0]),
            "kind": str(row[1]),
            "params_json": params,
            "idempotency_key": str(row[3]) if row[3] is not None else None,
            "status": str(row[4]),
            "error": str(row[5] or ""),
            "started_at": str(row[6]) if row[6] is not None else None,
            "completed_at": str(row[7]) if row[7] is not None else None,
            "created_at": str(row[8]),
        }
