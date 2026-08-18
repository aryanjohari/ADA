"""DDL for life_logs.db and food_reference.db (M19a §4)."""

LIFE_LOGS_DDL: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS schema_migrations (
      version INTEGER PRIMARY KEY,
      applied_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS meals (
      meal_id           TEXT PRIMARY KEY,
      local_day         TEXT NOT NULL,
      logged_at         TEXT NOT NULL,
      meal_slot         TEXT,
      note              TEXT,
      revision          INTEGER NOT NULL DEFAULT 1,
      supersedes_meal_id TEXT REFERENCES meals(meal_id),
      source_verb       TEXT NOT NULL,
      receipt_id        TEXT NOT NULL,
      created_at        TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_meals_local_day ON meals(local_day, logged_at)",
    """
    CREATE TABLE IF NOT EXISTS meal_foods (
      line_id           TEXT PRIMARY KEY,
      meal_id           TEXT NOT NULL REFERENCES meals(meal_id),
      sort_order        INTEGER NOT NULL,
      display_name      TEXT NOT NULL,
      ref_id            TEXT,
      preset_id         TEXT,
      serving_qty       REAL NOT NULL,
      serving_unit      TEXT NOT NULL,
      serving_grams     REAL,
      provenance        TEXT NOT NULL,
      snapshot_json     TEXT NOT NULL,
      revision          INTEGER NOT NULL DEFAULT 1,
      supersedes_line_id TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_meal_foods_meal ON meal_foods(meal_id)",
    """
    CREATE TABLE IF NOT EXISTS nutrition_day_rollup (
      local_day         TEXT PRIMARY KEY,
      computed_at       TEXT NOT NULL,
      totals_json       TEXT NOT NULL,
      target_snapshot_json TEXT,
      meal_count        INTEGER NOT NULL,
      honest_partial    INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS gym_sessions (
      session_id        TEXT PRIMARY KEY,
      started_at        TEXT NOT NULL,
      ended_at          TEXT,
      split_day         TEXT,
      session_notes     TEXT,
      status            TEXT NOT NULL,
      receipt_id        TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_gym_sessions_started ON gym_sessions(started_at)",
    """
    CREATE TABLE IF NOT EXISTS exercise_catalog (
      exercise_id       TEXT PRIMARY KEY,
      canonical_name    TEXT NOT NULL,
      aliases_json      TEXT,
      body_parts_json   TEXT NOT NULL,
      equipment_json    TEXT,
      movement          TEXT,
      source            TEXT NOT NULL,
      external_id       TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_exercise_name ON exercise_catalog(canonical_name)",
    """
    CREATE TABLE IF NOT EXISTS gym_sets (
      set_id            TEXT PRIMARY KEY,
      session_id        TEXT NOT NULL REFERENCES gym_sessions(session_id),
      sort_order        INTEGER NOT NULL,
      exercise_id       TEXT NOT NULL,
      exercise_name_raw TEXT NOT NULL,
      set_type          TEXT,
      load_kg           REAL,
      reps              INTEGER,
      rir               REAL,
      rpe               REAL,
      tempo             TEXT,
      rest_s            INTEGER,
      notes             TEXT,
      revision          INTEGER NOT NULL DEFAULT 1,
      supersedes_set_id TEXT,
      logged_at         TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_gym_sets_session ON gym_sets(session_id, sort_order)",
    """
    CREATE TABLE IF NOT EXISTS time_blocks (
      block_id          TEXT PRIMARY KEY,
      kind              TEXT NOT NULL,
      label             TEXT,
      started_at        TEXT NOT NULL,
      ended_at          TEXT,
      duration_s        INTEGER,
      status            TEXT NOT NULL,
      auto_stopped_by   TEXT,
      receipt_id        TEXT NOT NULL
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_time_one_running
    ON time_blocks(status) WHERE status = 'running'
    """,
    "CREATE INDEX IF NOT EXISTS idx_time_started ON time_blocks(started_at)",
    """
    CREATE TABLE IF NOT EXISTS habit_definitions (
      habit_id          TEXT PRIMARY KEY,
      display_name      TEXT NOT NULL,
      aliases_json      TEXT,
      anchor_hint       TEXT,
      schedule_json     TEXT,
      active            INTEGER NOT NULL DEFAULT 1,
      source            TEXT NOT NULL,
      receipt_id        TEXT,
      created_at        TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS habit_events (
      event_id          TEXT PRIMARY KEY,
      habit_id          TEXT NOT NULL REFERENCES habit_definitions(habit_id),
      local_day         TEXT NOT NULL,
      logged_at         TEXT NOT NULL,
      kind              TEXT NOT NULL,
      note              TEXT,
      supersedes_event_id TEXT,
      receipt_id        TEXT NOT NULL,
      source_verb       TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_habit_events_day ON habit_events(habit_id, local_day)",
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_habit_one_done_per_day
    ON habit_events(habit_id, local_day)
    WHERE kind = 'done' AND supersedes_event_id IS NULL
    """,
    """
    CREATE TABLE IF NOT EXISTS routine_definitions (
      routine_id        TEXT PRIMARY KEY,
      display_name      TEXT NOT NULL,
      steps_json        TEXT NOT NULL,
      eod_sweep         INTEGER NOT NULL DEFAULT 0,
      active            INTEGER NOT NULL DEFAULT 1,
      source            TEXT NOT NULL,
      created_at        TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS routine_runs (
      run_id            TEXT PRIMARY KEY,
      routine_id        TEXT NOT NULL REFERENCES routine_definitions(routine_id),
      local_day         TEXT NOT NULL,
      logged_at         TEXT NOT NULL,
      steps_done_json   TEXT NOT NULL,
      receipt_id        TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_routine_runs_day ON routine_runs(local_day)",
)

FOOD_REFERENCE_DDL: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS schema_migrations (
      version INTEGER PRIMARY KEY,
      applied_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS foods (
      food_ref_id       TEXT PRIMARY KEY,
      source            TEXT NOT NULL,
      external_id       TEXT,
      barcode           TEXT,
      name              TEXT NOT NULL,
      brand             TEXT,
      default_serving_g REAL,
      nutrients_per_100g_json TEXT,
      meta_json         TEXT,
      imported_at       TEXT NOT NULL,
      UNIQUE(source, external_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_foods_name ON foods(name)",
    "CREATE INDEX IF NOT EXISTS idx_foods_barcode ON foods(barcode)",
)
