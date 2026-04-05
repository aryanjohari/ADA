from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def schema_sql_path() -> Path:
    import ada

    return Path(ada.__path__[0]) / "db" / "schema.sql"
