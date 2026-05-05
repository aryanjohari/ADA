"""Tests for ada-control SQL sandbox guard."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.sql_guard import validate_select_only  # noqa: E402


@pytest.mark.parametrize(
    "sql,ok",
    [
        ("SELECT * FROM missions LIMIT 1", True),
        ("with x as (select 1) select * from x", True),
        ("INSERT INTO tasks VALUES (1)", False),
        ("SELECT 1; SELECT 2", False),
        ("PRAGMA wal_checkpoint", False),
        ("UPDATE tasks SET status='x'", False),
    ],
)
def test_validate_select_only(sql, ok):
    good, _ = validate_select_only(sql)
    assert good is ok


def test_empty_rejected():
    good, err = validate_select_only("  ")
    assert good is False and "empty" in err
