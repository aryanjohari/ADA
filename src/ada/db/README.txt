This folder holds DDL only. QueryEngine opens the SQLite path from config
and applies schema.sql once at startup (idempotent CREATE IF NOT EXISTS).

Tables include tasks/messages/transcript, state, usage_ledger, action_log,
web_sources, knowledge_sources / knowledge_items / knowledge_synthesis, and
the knowledge_items_fts virtual table (FTS5) for search.
