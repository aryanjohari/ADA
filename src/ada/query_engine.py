"""SQLite transcript + state (claude_logic §5, §10)."""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiosqlite

# Roles persisted (claude_logic §3)
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_TOOL = "tool"
ROLE_SYSTEM = "system"


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _pack_user_text(text: str) -> str:
    payload = {"parts": [{"type": "text", "text": text}]}
    return json.dumps(payload, ensure_ascii=False)


def _pack_assistant_text(text: str, extra: dict[str, Any] | None = None) -> str:
    base: dict[str, Any] = {"parts": [{"type": "text", "text": text}]}
    if extra:
        base.update(extra)
    return json.dumps(base, ensure_ascii=False)


def _pack_assistant_full(
    *,
    text: str,
    function_calls: list[dict[str, Any]] | None,
    meta: dict[str, Any] | None,
) -> str:
    parts: list[dict[str, Any]] = []
    if text.strip():
        parts.append({"type": "text", "text": text})
    if function_calls:
        for fc in function_calls:
            parts.append(
                {
                    "type": "function_call",
                    "name": fc.get("name") or "",
                    "args": fc.get("args") or {},
                    "id": fc.get("id"),
                }
            )
    if not parts:
        parts.append({"type": "text", "text": ""})
    base: dict[str, Any] = {"parts": parts}
    if meta:
        base["meta"] = meta
    return json.dumps(base, ensure_ascii=False)


@dataclass
class QueryEngine:
    db_path: Path
    schema_path: Path
    debounce_ms: int = 100

    _conn: aiosqlite.Connection | None = field(default=None, repr=False)
    _debounce_tasks: dict[str, asyncio.Task[None]] = field(
        default_factory=dict, repr=False
    )

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
        """Add columns / tables for DBs created before schema bumps."""
        assert self._conn is not None
        cur = await self._conn.execute("PRAGMA table_info(tasks)")
        cols = {str(row[1]) for row in await cur.fetchall()}
        if "plan_json" not in cols:
            await self._conn.execute(
                "ALTER TABLE tasks ADD COLUMN plan_json TEXT NOT NULL DEFAULT '{}'"
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
        """Await before starting the model stream (§5.1)."""
        assert self._conn is not None
        mid = _new_uuid()
        parent = await self.chain_head_uuid(session_id)
        seq = await self._next_sequence(session_id)
        await self._conn.execute(
            """
            INSERT INTO messages (uuid, session_id, parent_uuid, role, content_json, tombstone, sequence)
            VALUES (?, ?, ?, ?, ?, 0, ?)
            """,
            (mid, session_id, parent, ROLE_USER, _pack_user_text(text), seq),
        )
        await self._conn.commit()
        return mid

    async def persist_assistant_begin(self, session_id: int, parent_uuid: str) -> str:
        assert self._conn is not None
        mid = _new_uuid()
        seq = await self._next_sequence(session_id)
        await self._conn.execute(
            """
            INSERT INTO messages (uuid, session_id, parent_uuid, role, content_json, tombstone, sequence)
            VALUES (?, ?, ?, ?, ?, 0, ?)
            """,
            (mid, session_id, parent_uuid, ROLE_ASSISTANT, _pack_assistant_text(""), seq),
        )
        await self._conn.commit()
        return mid

    async def _flush_assistant_text(self, assistant_uuid: str, full_text: str) -> None:
        assert self._conn is not None
        await self._conn.execute(
            "UPDATE messages SET content_json = ? WHERE uuid = ?",
            (_pack_assistant_text(full_text), assistant_uuid),
        )
        await self._conn.commit()

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
        assert self._conn is not None
        t = self._debounce_tasks.pop(assistant_uuid, None)
        if t and not t.done():
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
        if function_calls:
            payload = _pack_assistant_full(
                text=final_text,
                function_calls=function_calls,
                meta=meta,
            )
        elif meta:
            payload = _pack_assistant_text(final_text, {"meta": meta})
        else:
            payload = _pack_assistant_text(final_text)
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
        mid = _new_uuid()
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

    async def record_usage(
        self,
        session_id: int,
        *,
        model: str | None,
        input_tokens: int | None,
        output_tokens: int | None,
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

    async def tombstone(self, uuids: Sequence[str], session_id: int) -> None:
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

    async def load_chain_for_api(self, session_id: int) -> list[dict[str, Any]]:
        """Rows for Gemini assembly — omit tombstones and system (§5.4, §12)."""
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

    async def insert_task(self, goal: str, status: str = "pending") -> int:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            INSERT INTO tasks (goal, status, current_output)
            VALUES (?, ?, '')
            """,
            (goal, status),
        )
        await self._conn.commit()
        return int(cur.lastrowid)

    async def fetch_pending_task(self) -> tuple[int, str] | None:
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT id, goal FROM tasks
            WHERE status = 'pending'
            ORDER BY id ASC
            LIMIT 1
            """
        )
        row = await cur.fetchone()
        if not row:
            return None
        return int(row[0]), str(row[1])

    async def latest_cli_session_task_id(self) -> int | None:
        """Most recent interactive CLI task (for session reuse)."""
        assert self._conn is not None
        cur = await self._conn.execute(
            """
            SELECT id FROM tasks
            WHERE goal = 'Interactive session'
            ORDER BY id DESC
            LIMIT 1
            """
        )
        row = await cur.fetchone()
        return int(row[0]) if row else None
