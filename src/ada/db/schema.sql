-- ADA schema: tasks, messages (transcript), state (KV), usage_ledger,
-- web_sources, knowledge_sources / knowledge_items / knowledge_synthesis

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

CREATE TABLE IF NOT EXISTS web_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    source_kind TEXT NOT NULL CHECK (source_kind IN ('search_hit', 'page_fetch')),
    query_text TEXT,
    content_excerpt TEXT NOT NULL DEFAULT '',
    content_sha256 TEXT,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_web_sources_session_fetched
    ON web_sources(session_id, fetched_at DESC);

-- Knowledge layer: registered sources, ingested items, synthesis with soft refs.
-- knowledge_items_fts: contentless FTS5 (rowid = knowledge_items.id), triggers keep doc in sync.

CREATE TABLE IF NOT EXISTS knowledge_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL CHECK (kind IN ('api', 'rss', 'web')),
    label TEXT,
    base_url TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS knowledge_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES knowledge_sources(id) ON DELETE CASCADE,
    external_id TEXT,
    published_at TEXT,
    ingested_at TEXT NOT NULL DEFAULT (datetime('now')),
    tags_json TEXT NOT NULL DEFAULT '[]',
    content_excerpt TEXT NOT NULL DEFAULT '',
    payload_json TEXT,
    content_hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_knowledge_items_source_ingested
    ON knowledge_items(source_id, ingested_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_items_source_external
    ON knowledge_items(source_id, external_id)
    WHERE external_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS knowledge_synthesis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    body TEXT NOT NULL,
    ref_item_ids_json TEXT NOT NULL DEFAULT '[]',
    task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Optional Gemini embeddings for semantic / hybrid search (see ada/knowledge_embeddings.py).
CREATE TABLE IF NOT EXISTS knowledge_item_embeddings (
    item_id INTEGER NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
    model TEXT NOT NULL,
    dim INTEGER NOT NULL,
    embedding BLOB NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (item_id, model)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_embeddings_model
    ON knowledge_item_embeddings(model);

-- Contentless FTS5: rowid aligns with knowledge_items.id; maintained by triggers.
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
