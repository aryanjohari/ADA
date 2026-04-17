-- Snapshot without web_sources (for migration tests)

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    current_output TEXT NOT NULL DEFAULT '',
    plan_json TEXT NOT NULL DEFAULT '{}',
    task_kind TEXT NOT NULL DEFAULT 'goal',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    uuid TEXT PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    parent_uuid TEXT REFERENCES messages(uuid) ON DELETE SET NULL,
    role TEXT NOT NULL,
    content_json TEXT NOT NULL,
    tombstone INTEGER NOT NULL DEFAULT 0 CHECK (tombstone IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    sequence INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_session_seq
    ON messages(session_id, sequence);

CREATE INDEX IF NOT EXISTS idx_messages_session_tombstone
    ON messages(session_id, tombstone);

CREATE TABLE IF NOT EXISTS state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS usage_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    recorded_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_usage_session
    ON usage_ledger(session_id, recorded_at);

CREATE TABLE IF NOT EXISTS action_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_action_log_created
    ON action_log(created_at);

CREATE INDEX IF NOT EXISTS idx_action_log_session
    ON action_log(session_id, created_at);
