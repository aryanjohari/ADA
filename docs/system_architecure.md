# ADA: System Architecture (Phase 1 MVP)

**Purpose:** Defines the structural boundaries, database schemas, and execution loop for a headless, edge-based autonomous cognitive engine.

## 1. The Core Paradigm
ADA operates as an asynchronous background daemon. It is completely decoupled from human UI. It operates on a deterministic State-Graph model: it wakes up, polls a database for pending tasks, executes them using a streaming LLM harness, logs its memory, and goes back to sleep.

## 2. Memory Stack (File System)
The agent's consciousness is split into static and dynamic files located in the `memory/` directory.
* **`soul.md` (Tier 1 - Immutable):** The core persona, prime directives, and strict execution constraints. Read at the start of every single execution loop. Never modified by the agent.
* **`master.md` (Tier 2 - Dynamic):** The agent's aggregated worldview and compressed learnings. Read to gain context on long-term operations.

## 3. State Machine (SQLite Database)
All active state and conversational history live in a single local SQLite database: `state.db`.

### Table: `tasks` (The Clipboard)
The task queue that dictates what the agent must do.
* `id` (Primary Key)
* `goal` (Text: The objective)
* `status` (Text: 'pending', 'executing', 'completed', 'failed')
* `current_output` (Text: The final response or error)

### Table: `messages` (The Transcript)
The conversational chain required by the Claude Code logic to maintain context and allow for stream resumption/tombstoning.
* `uuid` (Primary Key)
* `session_id` (Foreign Key -> tasks.id)
* `parent_uuid` (Self-referential to maintain the chain)
* `role` ('user', 'assistant', 'tool')
* `content_json` (The raw SDK payload)
* `tombstone` (Boolean: 1 if stream failed, 0 if active)

## 4. The Execution Engine (Python Asyncio)
The `main.py` daemon orchestrates the flow without holding state in memory longer than necessary.
1. **Poll:** `asyncio` loop queries `tasks` where `status = 'pending'`.
2. **Initialize:** Marks task as `executing`. Loads `soul.md`.
3. **Execute:** Passes the goal to `orchestrator.py` (which implements the `claude_logic.md` streaming and tombstone rules using the Gemini SDK).
4. **Persist:** Streams chunks and saves them to the `messages` table.
5. **Complete:** Writes the final output to `tasks.current_output` and updates status to `completed`.

## 5. MVP Constraints
* No external tools (search, scrape, etc.) are permitted in Phase 1. 
* No vector databases (ChromaDB) are permitted in Phase 1.
* The system is strictly a cognitive router: it reads a task, thinks using Gemini, and writes the answer.