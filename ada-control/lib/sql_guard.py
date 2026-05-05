"""Single-statement read-only SQL guard for the SELECT sandbox."""

from __future__ import annotations

import re

_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|ATTACH|DETACH|REPLACE|VACUUM"
    r"|BEGIN\b|COMMIT\b|ROLLBACK\b|SAVEPOINT\b|RELEASE\b)\b",
    re.IGNORECASE | re.MULTILINE,
)


def validate_select_only(sql: str) -> tuple[bool, str]:
    raw = (sql or "").strip()
    if not raw:
        return False, "empty SQL"
    if ";" in raw:
        return False, "multiple statements (;) are not allowed"
    if _FORBIDDEN.search(raw):
        return False, "only single SELECT/WITH-read queries are allowed"
    lowered = raw.lstrip().lower()
    if not (lowered.startswith("select ") or lowered.startswith("select\n") or lowered.startswith("with ")):
        return False, "query must begin with SELECT or WITH (CTE leading to SELECT)"
    return True, ""


def normalize_sql_preview(sql: str, *, max_chars: int = 12_000) -> str:
    s = sql.strip()
    if len(s) > max_chars:
        return s[:max_chars] + "\n… (truncated)"
    return s
