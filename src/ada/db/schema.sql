-- ADA schema: missions, tasks, messages (transcript), state (KV), usage_ledger,
-- web_sources, knowledge_sources / knowledge_items / knowledge_synthesis,
-- market_metrics / synthesis_edges (Business Kernel triage)

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS missions (
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
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    current_output TEXT NOT NULL DEFAULT '',
    plan_json TEXT NOT NULL DEFAULT '{}',
    task_kind TEXT NOT NULL DEFAULT 'goal',
    mission_id INTEGER REFERENCES missions(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- idx_tasks_mission_id: created in PersistentState._ensure_missions_schema (legacy DBs lack column until ALTER).

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
    kind TEXT NOT NULL CHECK (kind IN ('api', 'rss', 'web', 'brand')),
    label TEXT,
    base_url TEXT NOT NULL DEFAULT '',
    config_json TEXT NOT NULL DEFAULT '{}',
    mission_id INTEGER REFERENCES missions(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- idx_knowledge_sources_mission: created in PersistentState._ensure_knowledge_sources_mission_id

-- Phase 1 ingest audit (roadmap §12.1)
CREATE TABLE IF NOT EXISTS ingest_jobs (
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
);

CREATE INDEX IF NOT EXISTS idx_ingest_jobs_status_created
    ON ingest_jobs(status, created_at);

CREATE TABLE IF NOT EXISTS ingest_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingest_job_id INTEGER REFERENCES ingest_jobs(id) ON DELETE SET NULL,
    source TEXT NOT NULL,
    uri TEXT NOT NULL DEFAULT '',
    content_sha256 TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    meta_json TEXT NOT NULL DEFAULT '{}',
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ingest_raw_sha ON ingest_raw(content_sha256);

CREATE TABLE IF NOT EXISTS analytics_providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    account_ref TEXT NOT NULL DEFAULT '',
    property_ref TEXT NOT NULL,
    config_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(provider, property_ref)
);

CREATE TABLE IF NOT EXISTS analytics_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id INTEGER NOT NULL REFERENCES analytics_providers(id) ON DELETE CASCADE,
    ingest_job_id INTEGER REFERENCES ingest_jobs(id) ON DELETE SET NULL,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    response_version TEXT NOT NULL DEFAULT 'gsc.v1',
    row_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(provider_id, request_hash)
);

CREATE INDEX IF NOT EXISTS idx_analytics_snapshots_provider_window
    ON analytics_snapshots(provider_id, window_start, window_end);

CREATE TABLE IF NOT EXISTS gsc_search_analytics_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id INTEGER NOT NULL REFERENCES analytics_providers(id) ON DELETE CASCADE,
    snapshot_id INTEGER NOT NULL REFERENCES analytics_snapshots(id) ON DELETE CASCADE,
    data_date TEXT NOT NULL,
    query TEXT NOT NULL DEFAULT '',
    page TEXT NOT NULL DEFAULT '',
    country TEXT NOT NULL DEFAULT '',
    device TEXT NOT NULL DEFAULT '',
    clicks REAL NOT NULL DEFAULT 0,
    impressions REAL NOT NULL DEFAULT 0,
    ctr REAL NOT NULL DEFAULT 0,
    position REAL NOT NULL DEFAULT 0,
    row_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(provider_id, data_date, query, page, country, device)
);

CREATE INDEX IF NOT EXISTS idx_gsc_rows_date_property
    ON gsc_search_analytics_rows(provider_id, data_date);
CREATE INDEX IF NOT EXISTS idx_gsc_rows_query
    ON gsc_search_analytics_rows(provider_id, query);

CREATE TABLE IF NOT EXISTS campaign_opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_provider TEXT NOT NULL,
    source_row_ref TEXT NOT NULL,
    score_version TEXT NOT NULL,
    score_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'approved', 'rejected', 'applied')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(source_provider, source_row_ref, score_version)
);

CREATE INDEX IF NOT EXISTS idx_opportunities_status_score
    ON campaign_opportunities(status, created_at DESC);

CREATE TABLE IF NOT EXISTS approval_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_type TEXT NOT NULL,
    artifact_ref TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('requested', 'approved', 'rejected', 'expired')),
    requested_by TEXT NOT NULL DEFAULT '',
    approved_by TEXT NOT NULL DEFAULT '',
    reason TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL DEFAULT '{}',
    requested_at TEXT NOT NULL DEFAULT (datetime('now')),
    decided_at TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(artifact_type, artifact_ref)
);

CREATE INDEX IF NOT EXISTS idx_approval_artifact_status
    ON approval_records(artifact_type, status, updated_at DESC);

CREATE TABLE IF NOT EXISTS source_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    config_json TEXT NOT NULL DEFAULT '{}',
    host_allowlist_json TEXT NOT NULL DEFAULT '[]',
    maps_to_kind TEXT NOT NULL DEFAULT '',
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
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
    content_hash TEXT NOT NULL,
    relevance_score REAL,
    impact_score INTEGER CHECK (impact_score IS NULL OR (impact_score >= 1 AND impact_score <= 10)),
    triage_primary_category TEXT,
    triage_secondary_categories_json TEXT NOT NULL DEFAULT '[]',
    expires_at TEXT,
    tombstoned INTEGER NOT NULL DEFAULT 0 CHECK (tombstoned IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_knowledge_items_source_ingested
    ON knowledge_items(source_id, ingested_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_items_source_external
    ON knowledge_items(source_id, external_id)
    WHERE external_id IS NOT NULL;

-- idx_knowledge_items_triage_primary_ingested: created in PersistentState._ensure_triage_category_columns

-- Partial indexes on impact_score are created in PersistentState._ensure_impact_score_and_kernel_indexes
-- so executescript succeeds on DBs that still need ALTER ADD COLUMN impact_score.

CREATE TABLE IF NOT EXISTS knowledge_synthesis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    body TEXT NOT NULL,
    ref_item_ids_json TEXT NOT NULL DEFAULT '[]',
    task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS market_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT NOT NULL,
    numeric_value REAL NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT (datetime('now')),
    api_source TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_market_metrics_recorded
    ON market_metrics(recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_market_metrics_name_recorded
    ON market_metrics(metric_name, recorded_at DESC);

CREATE TABLE IF NOT EXISTS synthesis_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    knowledge_id INTEGER NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
    metric_id INTEGER NOT NULL REFERENCES market_metrics(id) ON DELETE CASCADE,
    causality_notes TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_synthesis_edges_knowledge
    ON synthesis_edges(knowledge_id);

CREATE INDEX IF NOT EXISTS idx_synthesis_edges_metric
    ON synthesis_edges(metric_id);

-- Phase 2 graph-lite memory: entities, edges, and evidence links.
CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    last_enriched_at TEXT,
    mission_id INTEGER REFERENCES missions(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_entities_normalized
    ON entities(normalized_name);

-- Partial uniques (mission-scoped): PersistentState._ensure_entities_mission_scope

CREATE TABLE IF NOT EXISTS graph_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    src_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    dst_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    edge_type TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'superseded', 'invalid')),
    source_url TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    superseded_by INTEGER REFERENCES graph_edges(id)
);

CREATE INDEX IF NOT EXISTS idx_graph_edges_src
    ON graph_edges(src_entity_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_dst
    ON graph_edges(dst_entity_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_type
    ON graph_edges(edge_type);

CREATE TABLE IF NOT EXISTS edge_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    edge_id INTEGER NOT NULL REFERENCES graph_edges(id) ON DELETE CASCADE,
    knowledge_id INTEGER NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
    span_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (edge_id, knowledge_id)
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

-- Phase 3: workflows (parent goal + ordered child steps; see docs/ROADMAP_APEX_OS.md §12.4)
CREATE TABLE IF NOT EXISTS workflows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    goal_text TEXT NOT NULL,
    params_json TEXT NOT NULL DEFAULT '{}',
    idempotency_key TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    parent_task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
    mission_id INTEGER REFERENCES missions(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (kind, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_workflows_parent ON workflows(parent_task_id);
-- idx_workflows_mission_id: created in PersistentState._ensure_missions_schema so legacy DBs
-- migrate before the index runs (executescript order would fail on pre-mission workflows rows).

CREATE TABLE IF NOT EXISTS workflow_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id INTEGER NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    step_index INTEGER NOT NULL,
    step_type TEXT NOT NULL CHECK (step_type IN (
        'FETCH', 'EXTRACT', 'SYNTHESIZE', 'ENRICH', 'GATE', 'DRAFT', 'DEPLOY'
    )),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'skipped')),
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
);

CREATE INDEX IF NOT EXISTS idx_workflow_steps_workflow ON workflow_steps(workflow_id, step_index);
