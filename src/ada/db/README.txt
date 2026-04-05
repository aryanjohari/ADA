This folder holds DDL only. QueryEngine opens the SQLite path from config
and applies schema.sql once at startup (idempotent CREATE IF NOT EXISTS).
