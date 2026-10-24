# SQLite schema digest (operator-maintained)

High-level reference for the ADA harness database (`state.db` / `ADA_DATA_DIR`). Update when DDL changes.

## `tasks`

- One row per **session**: interactive chat session or queued **goal** task.
- **id** — primary key; used as `session_id` elsewhere.
- **goal** — user text (chat: `"Interactive session"`; goals: full goal string from `ada goal add`).
- **status** — e.g. `pending`, `executing`, `completed`, `failed`.
- **current_output** — last assistant output / error summary (harness).
- **plan_json** — JSON string; durable scratchpad for `read_task_plan` / `write_task_plan` (daemon goals often use this as a state machine).
- **task_kind** — `chat` or `goal`.
- **created_at** / **updated_at** — timestamps.

## `messages`

- **Transcript** for Gemini: user, assistant, and tool rows linked by `parent_uuid` and `session_id`.
- **content_json** — structured parts (text, `function_call`, `function_response`).
- **tombstone** — soft-delete for failed streams / retries.
- **sequence** — ordering within a session.

## `web_sources` (Phase B)

Bounded rows for web tool usage; **no** full-page blobs in this table.

| Column | Role |
|--------|------|
| `session_id` | FK → `tasks(id)` CASCADE |
| `url` | Normalized HTTPS URL (capped) |
| `source_kind` | `search_hit` or `page_fetch` |
| `query_text` | Search query for `search_hit`; NULL for fetches |
| `content_excerpt` | Snippet or extracted text (capped) |
| `content_sha256` | Dedup hint (hash of kind + url + excerpt) |
| `fetched_at` | When inserted |

## How web rows are written (no second HTTP)

1. Model calls **`web_search`** or **`fetch_url_text`**; executor returns JSON (results / pages or `error`).
2. Tool result is persisted to **`messages`** as usual.
3. On success, the harness calls **`record_web_tool_artifacts`**: maps the response to bounded inserts into **`web_sources`** (same session). Inserts use only the tool response + args (e.g. search query); the harness does not re-fetch URLs for this table.

Optional: **`list_session_web_sources`** (when `ADA_ENABLE_WEB_SOURCES_TOOL=1`) returns recent rows for the **current** task/session from this table.
