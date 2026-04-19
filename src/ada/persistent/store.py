"""PersistentState — SQLite transcript, tasks, state KV, usage (claude_logic §2.1)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import aiosqlite

TaskKind = Literal["chat", "goal"]
KnowledgeKind = Literal["api", "rss", "web"]
TASK_KIND_CHAT: TaskKind = "chat"
TASK_KIND_GOAL: TaskKind = "goal"


@dataclass(frozen=True)
class KnowledgeItemInsertResult:
    """Result of insert_knowledge_item (dedupe may skip insert)."""

    id: int
    inserted: bool

from ada.knowledge_embeddings import blob_to_float32_list, cosine_similarity
from ada.knowledge_search import build_fts_match_query, reciprocal_rank_fusion
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
                    kind TEXT NOT NULL CHECK (kind IN ('api', 'rss', 'web')),
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
                    content_hash TEXT NOT NULL
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
    def _knowledge_fts_doc_select_expr(alias: str = "") -> str:
        """SQL expression for indexed doc text (keep in sync with FTS triggers)."""
        p = f"{alias}." if alias else ""
        return (
            f"{p}content_excerpt || ' ' || {p}tags_json || ' ' || "
            f"COALESCE(json_extract({p}payload_json, '$.link'), '') || ' ' || "
            f"COALESCE(json_extract({p}payload_json, '$.title'), '') || ' ' || "
            f"COALESCE(json_extract({p}payload_json, '$.feed_url'), '')"
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
        expr = self._knowledge_fts_doc_select_expr()
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
        expr = self._knowledge_fts_doc_select_expr()
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
            SELECT role, content_json FROM messages
            WHERE session_id = ? AND tombstone = 0 AND role != ?
            ORDER BY sequence ASC
            """,
            (session_id, ROLE_SYSTEM),
        )
        rows = await cur.fetchall()
        out: list[dict[str, Any]] = []
        for role, content_json in rows:
            payload = json.loads(content_json)
            out.append({"role": role, **payload})
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
    ) -> int:
        if task_kind not in ("chat", "goal"):
            raise ValueError(f"invalid task_kind: {task_kind!r}")
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            INSERT INTO tasks (goal, status, current_output, task_kind)
            VALUES (?, ?, '', ?)
            """,
            (goal, status, task_kind),
        )
        await self._conn.commit()
        return int(cur.lastrowid)

    async def fetch_pending_task(self) -> tuple[int, str] | None:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT id, goal FROM tasks
            WHERE status = 'pending' AND task_kind = ?
            ORDER BY id ASC
            LIMIT 1
            """,
            (TASK_KIND_GOAL,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        return int(row[0]), str(row[1])

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
    ) -> list[dict[str, Any]]:
        assert self._conn is not None
        limit = max(1, min(limit, 500))
        if status is not None:
            cur = await self._conn.execute(
                """
                SELECT id, goal, status, plan_json, created_at, updated_at
                FROM tasks
                WHERE task_kind = ? AND status = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (TASK_KIND_GOAL, status, limit),
            )
        else:
            cur = await self._conn.execute(
                """
                SELECT id, goal, status, plan_json, created_at, updated_at
                FROM tasks
                WHERE task_kind = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (TASK_KIND_GOAL, limit),
            )
        rows = await cur.fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            out.append(
                {
                    "id": int(row[0]),
                    "goal": str(row[1]),
                    "status": str(row[2]),
                    "plan_json": str(row[3]),
                    "created_at": str(row[4]),
                    "updated_at": str(row[5]),
                }
            )
        return out

    async def get_goal_task(self, task_id: int) -> dict[str, Any]:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT id, goal, status, plan_json, current_output, task_kind, created_at, updated_at
            FROM tasks WHERE id = ?
            """,
            (task_id,),
        )
        row = await cur.fetchone()
        if not row:
            raise LookupError(f"no task with id={task_id}")
        if str(row[5]) != TASK_KIND_GOAL:
            raise ValueError(f"task {task_id} is not a goal task (task_kind={row[5]!r})")
        return {
            "id": int(row[0]),
            "goal": str(row[1]),
            "status": str(row[2]),
            "plan_json": str(row[3]),
            "current_output": str(row[4]),
            "task_kind": str(row[5]),
            "created_at": str(row[6]),
            "updated_at": str(row[7]),
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

    async def insert_knowledge_source(
        self,
        kind: KnowledgeKind,
        *,
        label: str | None = None,
        base_url: str = "",
    ) -> int:
        if kind not in ("api", "rss", "web"):
            raise ValueError(f"invalid knowledge source kind: {kind!r}")
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            INSERT INTO knowledge_sources (kind, label, base_url)
            VALUES (?, ?, ?)
            """,
            (kind, label, base_url),
        )
        await self._conn.commit()
        return int(cur.lastrowid)

    async def list_knowledge_sources(
        self, *, kind: str | None = None
    ) -> list[dict[str, Any]]:
        assert self._conn is not None
        if kind is not None:
            cur = await self._conn.execute(
                """
                SELECT id, kind, label, base_url, created_at
                FROM knowledge_sources
                WHERE kind = ?
                ORDER BY id ASC
                """,
                (kind,),
            )
        else:
            cur = await self._conn.execute(
                """
                SELECT id, kind, label, base_url, created_at
                FROM knowledge_sources
                ORDER BY id ASC
                """
            )
        rows = await cur.fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            out.append(
                {
                    "id": int(row[0]),
                    "kind": str(row[1]),
                    "label": row[2],
                    "base_url": str(row[3]),
                    "created_at": str(row[4]),
                }
            )
        return out

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
    ) -> KnowledgeItemInsertResult:
        assert self._conn is not None
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
                content_excerpt, payload_json, content_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                external_id,
                published_at,
                tags_json,
                content_excerpt,
                payload_json,
                content_hash,
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
        ) = row
        payload: dict[str, Any] | None
        if payload_json is None:
            payload = None
        else:
            payload = json.loads(str(payload_json))
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
        }

    async def get_knowledge_item(self, item_id: int) -> dict[str, Any]:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT id, source_id, external_id, published_at, ingested_at,
                   tags_json, content_excerpt, payload_json, content_hash
            FROM knowledge_items WHERE id = ?
            """,
            (item_id,),
        )
        row = await cur.fetchone()
        if not row:
            raise LookupError(f"no knowledge item with id={item_id}")
        return self._row_to_knowledge_item(row)

    async def list_knowledge_items(
        self,
        *,
        source_id: int | None = None,
        limit: int = 100,
        ingested_after: str | None = None,
        ingested_before: str | None = None,
    ) -> list[dict[str, Any]]:
        assert self._conn is not None
        lim = max(1, min(limit, 500))
        conds: list[str] = []
        args: list[Any] = []
        if source_id is not None:
            conds.append("source_id = ?")
            args.append(source_id)
        if ingested_after is not None:
            conds.append("datetime(ingested_at) >= datetime(?)")
            args.append(ingested_after)
        if ingested_before is not None:
            conds.append("datetime(ingested_at) <= datetime(?)")
            args.append(ingested_before)
        where = f"WHERE {' AND '.join(conds)}" if conds else ""
        args.append(lim)
        cur = await self._conn.execute(
            f"""
            SELECT id, source_id, external_id, published_at, ingested_at,
                   tags_json, content_excerpt, payload_json, content_hash
            FROM knowledge_items
            {where}
            ORDER BY datetime(ingested_at) DESC
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

    def _knowledge_filter_sql(
        self,
        *,
        table_alias: str,
        tag: str | None,
        ingested_after: str | None,
        ingested_before: str | None,
    ) -> tuple[str, list[Any]]:
        conds: list[str] = []
        args: list[Any] = []
        prefix = f"{table_alias}." if table_alias else ""
        if tag is not None:
            conds.append(
                f"EXISTS (SELECT 1 FROM json_each({prefix}tags_json) j WHERE j.value = ?)"
            )
            args.append(tag)
        if ingested_after is not None:
            conds.append(f"datetime({prefix}ingested_at) >= datetime(?)")
            args.append(ingested_after)
        if ingested_before is not None:
            conds.append(f"datetime({prefix}ingested_at) <= datetime(?)")
            args.append(ingested_before)
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
    ) -> list[dict[str, Any]]:
        mq = build_fts_match_query(query)
        lim = max(1, min(limit, 500))
        assert self._conn is not None
        extra_fts, args_fts = self._knowledge_filter_sql(
            table_alias="ki",
            tag=tag,
            ingested_after=ingested_after,
            ingested_before=ingested_before,
        )
        if not mq:
            return await self._search_knowledge_items_like(
                query,
                limit=lim,
                tag=tag,
                ingested_after=ingested_after,
                ingested_before=ingested_before,
            )
        if prefer_fts and await self._knowledge_fts_table_exists():
            try:
                sql = f"""
                    SELECT ki.id, ki.source_id, ki.external_id, ki.published_at, ki.ingested_at,
                           ki.tags_json, ki.content_excerpt, ki.payload_json, ki.content_hash
                    FROM knowledge_items ki
                    INNER JOIN knowledge_items_fts ON ki.id = knowledge_items_fts.rowid
                    WHERE knowledge_items_fts MATCH ?{extra_fts}
                    ORDER BY bm25(knowledge_items_fts) ASC, datetime(ki.ingested_at) DESC
                    LIMIT ?
                    """
                params: list[Any] = [mq, *args_fts, lim]
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
    ) -> list[dict[str, Any]]:
        assert self._conn is not None
        extra, args_extra = self._knowledge_filter_sql(
            table_alias="ki",
            tag=tag,
            ingested_after=ingested_after,
            ingested_before=ingested_before,
        )
        sql = f"""
            SELECT e.item_id, e.embedding, e.dim
            FROM knowledge_item_embeddings e
            INNER JOIN knowledge_items ki ON ki.id = e.item_id
            WHERE e.model = ?{extra}
            """
        params: list[Any] = [embedding_model, *args_extra]
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
        return await self._knowledge_items_by_ids_ordered(ids)

    async def _knowledge_items_by_ids_ordered(
        self, ids: list[int]
    ) -> list[dict[str, Any]]:
        if not ids:
            return []
        assert self._conn is not None
        ph = ",".join("?" * len(ids))
        cur = await self._conn.execute(
            f"""
            SELECT id, source_id, external_id, published_at, ingested_at,
                   tags_json, content_excerpt, payload_json, content_hash
            FROM knowledge_items WHERE id IN ({ph})
            """,
            ids,
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
                )
            return await self._search_knowledge_items_lexical(
                query,
                limit=lim,
                tag=tag,
                ingested_after=ingested_after,
                ingested_before=ingested_before,
                prefer_fts=prefer_fts,
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
                )
                sem = await self._search_knowledge_items_semantic(
                    query_embedding,
                    embedding_model=embedding_model,
                    limit=arm,
                    min_cosine=embedding_min_cosine,
                    tag=tag,
                    ingested_after=ingested_after,
                    ingested_before=ingested_before,
                )
                lex_ids = [x["id"] for x in lex]
                sem_ids = [x["id"] for x in sem]
                fused = reciprocal_rank_fusion([lex_ids, sem_ids], k=60)
                pick = fused[:lim]
                return await self._knowledge_items_by_ids_ordered(pick)
            return await self._search_knowledge_items_lexical(
                query,
                limit=lim,
                tag=tag,
                ingested_after=ingested_after,
                ingested_before=ingested_before,
                prefer_fts=prefer_fts,
            )

        return await self._search_knowledge_items_lexical(
            query,
            limit=lim,
            tag=tag,
            ingested_after=ingested_after,
            ingested_before=ingested_before,
            prefer_fts=prefer_fts,
        )

    async def _search_knowledge_items_like(
        self,
        query: str,
        *,
        limit: int,
        tag: str | None,
        ingested_after: str | None,
        ingested_before: str | None,
    ) -> list[dict[str, Any]]:
        assert self._conn is not None
        token = query.strip()
        if not token:
            return []
        esc = token.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{esc}%"
        extra, args_extra = self._knowledge_filter_sql(
            table_alias="",
            tag=tag,
            ingested_after=ingested_after,
            ingested_before=ingested_before,
        )
        sql = f"""
            SELECT id, source_id, external_id, published_at, ingested_at,
                   tags_json, content_excerpt, payload_json, content_hash
            FROM knowledge_items
            WHERE (content_excerpt LIKE ? ESCAPE '\\' OR tags_json LIKE ? ESCAPE '\\')
            {extra}
            ORDER BY datetime(ingested_at) DESC
            LIMIT ?
            """
        params = [pattern, pattern, *args_extra, limit]
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

    async def delete_knowledge_source(self, source_id: int) -> None:
        """Delete a registered source and cascade knowledge_items (not synthesis refs)."""
        assert self._conn is not None
        await self._conn.execute(
            "DELETE FROM knowledge_sources WHERE id = ?",
            (source_id,),
        )
        await self._conn.commit()
