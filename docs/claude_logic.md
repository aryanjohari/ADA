# claude_logic.md

**Purpose:** Normative specification for the Python asyncio harness so that **every behavioral detail** implied by Claude Code's QueryEngine / query orchestrator / streaming tool executor is explicitly captured. This document is the **single source of truth** for implementers; **ARCHITECTURE.md** defines module boundaries and data flow at a high level.

**Audience:** Engineers implementing or reviewing the Raspberry Pi headless agent.

---

## 1. Concepts and vocabulary

| Term | Definition |
|------|------------|
| **Turn** | One user submission until the model returns an end-turn (no further tool calls required) or an unrecoverable error |
| **Trajectory** | Ordered sequence of messages in one turn: user -> (assistant fragments + tool results)* -> final assistant |
| **Message** | One row in `messages` with a unique `uuid` and optional `parent_uuid` |
| **Chain** | Transcript is a **tree** logically, rendered as a **linear chain** via `parent_uuid` (Claude Code: parentUuid discipline) |
| **Tombstone** | Logical deletion of a message uuid after a failed stream or orphan; must not participate in API replay |
| **Soul** | Long-horizon narrative memory in `memory/soul.md`, distinct from SQLite transcript |

---

## 2. UUIDs and identity

- Generate with `uuid.uuid4()`; store as lowercase hex string.
- **Stable across retries** only for messages already committed to SQLite. Never reuse a uuid for a different semantic message.
- **Tool use id** (GenAI function call id): map SDK call id to internal `tool_call_id`; persist in `content_json` for pairing `function_response` to call.

---

## 3. Roles and `content_json` shapes

Persisted `role` values: `user`, `assistant`, `tool`, `system`.

### 3.1 User message

```json
{
  "parts": [
    { "type": "text", "text": "..." }
  ]
}
```

Multimodal (optional on Pi): `inline_data` or file_uri per GenAI schema, still one row.

### 3.2 Assistant message

```json
{
  "parts": [
    { "type": "text", "text": "..." },
    { "type": "function_call", "name": "tool_name", "args": { ... } }
  ]
}
```

**Rule:** While streaming, **append parts** to the **same in-memory assistant shell** until the model completes that assistant "slice" (before any tool results are inserted). The shell is one `uuid` for that slice.

### 3.3 Tool / function response message

```json
{
  "parts": [
    {
      "type": "function_response",
      "name": "tool_name",
      "response": { "result": "..." },
      "tool_call_id": "sdk-id-or-synthetic"
    }
  ]
}
```

`parent_uuid` **must** point to the **assistant** message that contained the matching `function_call`.

### 3.4 System row (optional)

Compact boundaries, session metadata, or injected soul hash markers. Usually **not** sent back to the API as a full message; filter in `load_chain_for_api`.

---

## 4. Parent chain rules (strict)

1. The **first message** of a session has `parent_uuid = NULL`.
2. Every subsequent message must set `parent_uuid` to the **chain head** at insert time (last committed message in this session that is not tombstoned).
3. **User** message after turn N completes: `parent_uuid` = last non-tombstoned message (often last assistant of previous turn).
4. **Assistant shell** for current turn: `parent_uuid` = user message of this turn (or previous head if continuing after tool results).
5. **Function response** rows: `parent_uuid` = assistant uuid that holds the call (not the previous tool result unless model issued parallel calls from same assistant; then all responses still point to **that same assistant**).

**Fork prevention:** If two writers race, SQLite `BEGIN IMMEDIATE` per session serializes commits (QueryEngine only).

---

## 5. QueryEngine persistence semantics (mirror Claude Code)

### 5.1 User message

- **Always await** `persist_user` before starting the GenAI stream for that turn.
- Ensures kill-early safety: if the process dies after send, resume can find the user prompt.

### 5.2 Assistant streaming

- Maintain one **mutable** `AssistantShell` object in memory during streaming (same id as eventual row).
- **Throttle disk writes:** schedule `persist_assistant_append` with debounce (e.g. 100 ms) coalescing part updates **or** write only on part boundaries.
- **Terminal metadata:** On stream end, set `usage`, `finish_reason`, `model` on the **same shell object** so the serialized row reflects finals (Claude: mutate last message in place for lazy serializer).

### 5.3 Fire-and-forget vs await

| Event | Await? | Rationale |
|-------|--------|-----------|
| User insert | Yes | Chain anchor for resume |
| Soul-critical system marker | Yes | If compaction depends on it |
| Assistant partial | No (task + flush at end) | Avoid blocking `async for` |
| Tool result | Yes (per result or batched) | Order vs next API call |

On Pi, **await tool results** before next `generate_content` if the SDK requires strict ordering in `contents`.

### 5.4 Tombstone application

- Input: list of `uuid` (assistant shells and any orphan tool rows).
- SQL: `UPDATE messages SET tombstone = 1 WHERE uuid IN (...) AND session_id = ?`
- **API load:** `load_chain_for_api` **excludes** `tombstone = 1`.
- **Next insert parent:** last row where `tombstone = 0` ordered by `created_at` / monotonic sequence.

Optional: separate `sequence INTEGER` monotonic per session to avoid timestamp ties on Pi.

---

## 6. Query Orchestrator: streaming loop (normative)

### 6.1 Loop structure

```text
async def orchestrate_turn(...):
    executor = StreamingToolExecutor(...)
    fallback_generation = 0
    try:
        async for chunk in adapter.stream_turn(...):
            events = normalize(chunk)
            for e in events:
                if e.type == "assistant_delta":
                    yield e  # -> QueryEngine schedules persist
                elif e.type == "tool_invocation_complete":
                    async for tr in executor.run(e):
                        yield tr
                elif e.type == "turn_signal":
                    ...
    except StreamFailed:
        executor.discard()
        await query_engine.tombstone_attempt(...)
        # retry policy
```

### 6.2 Normalization stages

1. **Raw chunk** -> extract `candidates[0].content.parts` deltas (SDK-version dependent).
2. **Accumulate** `function_call` arguments until the call is complete (some APIs emit arg string in pieces).
3. Emit `tool_invocation_complete` **once per call** with final `name`, `args`, `id`.

### 6.3 Continuation (multi-hop within one turn)

When the model emits tool calls and **stop_reason** indicates tool use:

1. Persist assistant row (with function_call parts).
2. Run tools; persist function_response rows.
3. Build new `contents` from `load_chain_for_api` including new tool results.
4. Call **stream** again (same `QueryEngine` session) without extra user text.

**Max depth:** configurable `max_tool_rounds` (e.g. 50) to prevent loops.

---

## 7. StreamingToolExecutor (full contract)

### 7.1 States

Per invocation `i`:

- `queued` - submitted, waiting for concurrency / exclusivity
- `running` - `asyncio.Task` active
- `completed` - result available to yield
- `discarded` - result must never be persisted

### 7.2 Concurrency

- **Partition invocations** into batches like Claude `toolOrchestration.ts`:
  - Consecutive **safe** tools -> parallel with semaphore `max_parallel`
  - **Unsafe** tool -> exclusive: no other tool runs until it completes
- **Ordering:** Submission order is preserved in the **output queue**. Parallel execution may finish out of order; **reorder** before yield to submission order.

### 7.3 submit() vs run()

- `submit(invocation)` is non-blocking; pushes to internal queue.
- `drain()` or inline: process queue until empty for current stream segment.

### 7.4 discard()

- Set `discarded = True` on executor.
- Cancel all running tasks: `task.cancel()` with `asyncio.CancelledError` handled.
- **Synthetic errors** for cancelled invocations: optional `function_response` with `is_error` marking, **only if** the assistant row was already persisted and API needs pairing; otherwise tombstone assistant and **omit** results from API replay.

### 7.5 Permission hook

Optional `can_use_tool(tool, args) -> bool | Awaitable[bool]` mirroring Claude `canUseTool`. Default on headless Pi: allowlist in config.

---

## 8. Fallback and retries (aligned with Claude Code)

### 8.1 Triggers

- Network / SDK exception
- Empty or truncated stream (no candidate / no finish_reason)
- Stream idle timeout (watchdog coroutine resetting on each chunk)

### 8.2 Sequence

1. `executor.discard()`
2. `query_engine.tombstone_messages(generation_attempt_uuids)`
3. Increment `fallback_generation`; optionally switch model or `max_output_tokens`
4. If retrying: rebuild `contents` from DB (no tombstoned rows)

### 8.3 Non-streaming fallback

Optional second path: single `generate_content` (non-stream) after stream fails, **same** normalization to tool calls. Still use same executor and `QueryEngine` persistence rules.

---

## 9. Backfill / derived tool fields (Claude `backfillObservableInput`)

- **Rule:** The object used for **API round-trip** must not gain extra keys that change the canonical request unless the model produced them.
- If a tool expands paths or adds defaults for logging only:
  - Apply expansion on a **copy** when persisting for display/logs.
  - For re-invocation, prefer **original** args from assistant `function_call`.

---

## 10. `state` table: recommended keys

| Key | Meaning |
|-----|---------|
| `session.active_model` | Last model id |
| `session.total_input_tokens` | Cumulative estimate |
| `session.total_output_tokens` | Cumulative |
| `session.last_finish_reason` | Debug |
| `soul.last_merged_at` | ISO timestamp |
| `soul.byte_length` | Sanity check |
| `turn.current_id` / `turn.fallback_generation` | Resilience |

**Rule:** Orchestrator **never** writes `state`; only `QueryEngine`.

---

## 11. `memory/soul.md` contract

### 11.1 Purpose

- Long-horizon preferences, project facts, tone; **not** a full transcript.
- Human-editable; treat as **untrusted text** for prompting (escape / block markers).

### 11.2 Suggested format

```markdown
# Soul
Updated: 2026-04-06

## Principles
- ...

## Project facts
- ...
```

### 11.3 Integration

- At turn start, `QueryEngine` loads soul (cached); injects into **system instruction** fragment with delimiters:

```text
<user_soul>
... soul.md content ...
</user_soul>
```

- Tools may append to soul (`append_soul_section`) via QueryEngine: **single writer**, file lock `fcntl` or `asyncio` thread executor for `aiofiles` + rename.

### 11.4 Consistency with SQLite

- Optionally append a `system` row: `{"parts":[{"type":"text","text":"soul updated hash=..."}]}` for debugging.

---

## 12. GenAI contents assembly

Order for `generate_content` `contents`:

1. Prior turns: compact user/assistant/tool from `load_chain_for_api` (excluding tombstones, optional compaction).
2. Current turn: newest user message + any tool results not yet answered.

**Function calling:** Use `tools` and `tool_config` per SDK (e.g. `AUTO` mode).

**System instruction:** Static harness instructions + soul injection + optional datetime/workdir for Pi.

---

## 13. Testing obligations

| Test | Assert |
|------|--------|
| Chain after 3 tool rounds | `parent_uuid` chain valid |
| Stream fail mid-assistant | Tombstone + no orphan tool_result in API load |
| Parallel safe tools | Results persisted in submission order |
| Exclusive unsafe tool | No overlap windows |
| discard() during run | No persisted result after tombstone |
| Soul file locked | No interleaving writes |

---

## 14. Checklist: Claude Code parity

- [ ] Async generator / async iterator streaming loop separate from SQLite
- [ ] `QueryEngine` owns all commits + tombstones + soul DB coordination
- [ ] Mid-stream tool execution with ordered yields
- [ ] `discard()` on fallback before retry
- [ ] Mutable assistant shell for in-place final usage metadata
- [ ] Explicit continuation loop for tool rounds
- [ ] parent chain discipline for resume

---

## 15. Document map

| File | Role |
|------|------|
| `ARCHITECTURE.md` | Layers, boundaries, data flow, schema sketch |
| `claude_logic.md` | This file: all normative rules and edge cases |

---

*End of claude_logic.md*
