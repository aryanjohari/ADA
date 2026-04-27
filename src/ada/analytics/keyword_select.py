"""Deterministic keyword cluster selection from GSC slices."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ada.query_engine import QueryEngine


@dataclass(frozen=True)
class KeywordSelectResult:
    keyword_cluster: str | None
    keyword_source: dict[str, Any]
    fallback_reason: str | None


async def select_keyword_cluster(
    qe: QueryEngine,
    *,
    site: str,
    start_date: str,
    end_date: str,
    limit: int = 20,
) -> KeywordSelectResult:
    top_queries = await qe.list_gsc_top_queries_safe(
        site=site, start_date=start_date, end_date=end_date, limit=limit
    )
    if not top_queries.get("tables_present"):
        return KeywordSelectResult(
            keyword_cluster=None,
            keyword_source={
                "kind": "gsc",
                "site": site,
                "start_date": start_date,
                "end_date": end_date,
                "table": "gsc_search_analytics_rows",
            },
            fallback_reason="gsc_table_missing",
        )
    rows = top_queries.get("rows") or []
    if not rows:
        return KeywordSelectResult(
            keyword_cluster=None,
            keyword_source={
                "kind": "gsc",
                "site": site,
                "start_date": start_date,
                "end_date": end_date,
                "table": "gsc_search_analytics_rows",
            },
            fallback_reason="gsc_no_rows",
        )
    best = str(rows[0].get("query") or "").strip() or None
    return KeywordSelectResult(
        keyword_cluster=best,
        keyword_source={
            "kind": "gsc",
            "site": site,
            "start_date": start_date,
            "end_date": end_date,
            "table": "gsc_search_analytics_rows",
            "rows_considered": len(rows),
        },
        fallback_reason=None if best else "gsc_empty_query",
    )
