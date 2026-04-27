"""CLI helper for deterministic keyword cluster selection."""

from __future__ import annotations

import json
from pathlib import Path

import ada
from ada.analytics.keyword_select import select_keyword_cluster
from ada.config import Settings
from ada.profile_runtime import enforce_profile_identity
from ada.query_engine import QueryEngine


async def run_keyword_select_cli(
    settings: Settings,
    *,
    entity_id: int,
    site: str,
    start_date: str,
    end_date: str,
) -> int:
    schema_path = Path(ada.__path__[0]) / "db" / "schema.sql"
    qe = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    await enforce_profile_identity(qe, settings)
    try:
        out = await select_keyword_cluster(
            qe,
            site=site,
            start_date=start_date,
            end_date=end_date,
            limit=settings.gsc_plan_max_items,
        )
    finally:
        await qe.close()
    payload = {
        "entity_id": int(entity_id),
        "target_keyword_cluster": out.keyword_cluster,
        "keyword_source": out.keyword_source,
        "fallback_reason": out.fallback_reason,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if out.keyword_cluster else 1
