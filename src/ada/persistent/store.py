"""PersistentState — SQLite transcript, tasks, state KV, usage (claude_logic §2.1)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import aiosqlite

TaskKind = Literal["chat", "goal"]
TASK_KIND_CHAT: TaskKind = "chat"
TASK_KIND_GOAL: TaskKind = "goal"

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
            SELECT id, goal, status, plan_json, task_kind, created_at, updated_at
            FROM tasks WHERE id = ?
            """,
            (task_id,),
        )
        row = await cur.fetchone()
        if not row:
            raise LookupError(f"no task with id={task_id}")
        if str(row[4]) != TASK_KIND_GOAL:
            raise ValueError(f"task {task_id} is not a goal task (task_kind={row[4]!r})")
        return {
            "id": int(row[0]),
            "goal": str(row[1]),
            "status": str(row[2]),
            "plan_json": str(row[3]),
            "task_kind": str(row[4]),
            "created_at": str(row[5]),
            "updated_at": str(row[6]),
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
