"""DataForSEO Google Ads search volume batch → ingest_raw (no LLM)."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from ada.config import Settings
from ada.ingest.common import assert_gov_api_url_allowed
from ada.query_engine import QueryEngine

log = logging.getLogger("ada.ingest.keywords")

DATAFORSEO_BASE = "https://api.dataforseo.com"
SEARCH_VOLUME_LIVE = "/v3/keywords_data/google_ads/search_volume/live"
TASK_POST = "/v3/keywords_data/google_ads/search_volume/task_post"
TASK_GET_PREFIX = "/v3/keywords_data/google_ads/search_volume/task_get/"


@dataclass
class IngestKeywordsResult:
    job_id: int
    raw_row_id: int
    terms_submitted: int = 0
    error: str = ""


def _basic_auth_header(login: str, password: str) -> dict[str, str]:
    import base64

    token = base64.b64encode(f"{login}:{password}".encode()).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def _parse_keyword_list(settings: Settings) -> list[str]:
    raw = settings.ada_keyword_terms.strip()
    if not raw:
        return []
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    cap = settings.ada_keyword_max_terms_per_run
    return parts[:cap]


async def ingest_keywords_batch(
    qe: QueryEngine,
    settings: Settings,
    *,
    keywords: list[str] | None = None,
    idempotency_key: str | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> IngestKeywordsResult:
    """
    POST DataForSEO; persist full JSON to ingest_raw before any filtering.
    """
    terms = keywords if keywords is not None else _parse_keyword_list(settings)
    terms = [t.strip() for t in terms if t.strip()][: settings.ada_keyword_max_terms_per_run]
    if not terms:
        return IngestKeywordsResult(job_id=0, raw_row_id=0, error="no keywords (set ADA_KEYWORD_TERMS)")

    if not settings.dataforseo_login or not settings.dataforseo_password:
        return IngestKeywordsResult(
            job_id=0, raw_row_id=0, error="DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD required"
        )

    try:
        assert_gov_api_url_allowed(
            f"{DATAFORSEO_BASE}/", settings.gov_api_host_allowlist
        )
    except ValueError as e:
        return IngestKeywordsResult(job_id=0, raw_row_id=0, error=str(e))

    job_id = await qe.create_ingest_job(
        "keyword_batch",
        {
            "keywords": terms,
            "language_code": settings.ada_keyword_language_code,
            "location_code": settings.ada_keyword_location_code,
        },
        idempotency_key=idempotency_key,
    )
    await qe.update_ingest_job(
        job_id, status="running", set_started=True
    )

    headers = _basic_auth_header(
        settings.dataforseo_login,
        settings.dataforseo_password,
    )
    headers["Content-Type"] = "application/json"

    own_client = http_client is None
    client = http_client or httpx.AsyncClient(
        timeout=120.0,
        follow_redirects=True,
        headers=headers,
    )
    try:
        if settings.ada_dataforseo_use_live:
            body_text, uri = await _post_live(client, terms, settings)
        else:
            body_text, uri = await _post_task_standard(client, terms, settings)
        raw_id = await qe.insert_ingest_raw(
            ingest_job_id=job_id,
            source="dataforseo_keywords_google_ads",
            uri=uri,
            body=body_text,
            meta_json={"term_count": len(terms)},
        )
        await qe.update_ingest_job(
            job_id, status="completed", set_completed=True
        )
        return IngestKeywordsResult(
            job_id=job_id, raw_row_id=raw_id, terms_submitted=len(terms)
        )
    except Exception as e:
        err = str(e)
        log.warning("ingest keywords: %s", err)
        await qe.update_ingest_job(
            job_id,
            status="failed",
            error=err[:2000],
            set_completed=True,
        )
        return IngestKeywordsResult(job_id=job_id, raw_row_id=0, error=err)
    finally:
        if own_client:
            await client.aclose()


async def _post_live(
    client: httpx.AsyncClient, terms: list[str], settings: Settings
) -> tuple[str, str]:
    url = f"{DATAFORSEO_BASE}{SEARCH_VOLUME_LIVE}"
    payload: list[dict[str, Any]] = [
        {
            "language_code": settings.ada_keyword_language_code,
            "location_code": settings.ada_keyword_location_code,
            "keywords": terms,
        }
    ]
    r = await client.post(url, json=payload)
    r.raise_for_status()
    return r.text, url


async def _post_task_standard(
    client: httpx.AsyncClient, terms: list[str], settings: Settings
) -> tuple[str, str]:
    post_url = f"{DATAFORSEO_BASE}{TASK_POST}"
    payload: list[dict[str, Any]] = [
        {
            "language_code": settings.ada_keyword_language_code,
            "location_code": settings.ada_keyword_location_code,
            "keywords": terms,
        }
    ]
    r = await client.post(post_url, json=payload)
    r.raise_for_status()
    data = r.json()
    task_id = _extract_task_id(data)
    if not task_id:
        return r.text, post_url

    get_url = f"{DATAFORSEO_BASE}{TASK_GET_PREFIX}{task_id}"
    for _ in range(60):
        gr = await client.get(get_url)
        gr.raise_for_status()
        gtext = gr.text
        gdata = json.loads(gtext)
        tasks = (gdata.get("tasks") or []) if isinstance(gdata, dict) else []
        if tasks:
            st = tasks[0].get("status_code")
            if st == 20000:
                return gtext, get_url
            if st is not None and int(st) >= 40000:
                return gtext, get_url
        await asyncio.sleep(2.0)
    raise TimeoutError("DataForSEO task_get did not complete in time")


def _extract_task_id(data: dict[str, Any]) -> str | None:
    tasks = data.get("tasks") or []
    if not tasks:
        return None
    tid = tasks[0].get("id")
    return str(tid) if tid else None


async def run_ingest_keywords_cli(settings: Settings) -> int:
    from pathlib import Path

    import ada

    settings.ensure_data_dir()
    schema_path = Path(ada.__path__[0]) / "db" / "schema.sql"
    qe = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    try:
        from datetime import datetime, timezone

        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        res = await ingest_keywords_batch(
            qe,
            settings,
            idempotency_key=f"keyword-batch-{day}",
        )
        if res.error:
            print(f"ingest-keywords: error: {res.error}", flush=True)
            return 1
        print(
            f"ingest-keywords: job_id={res.job_id} raw_id={res.raw_row_id} "
            f"terms={res.terms_submitted}",
            flush=True,
        )
        return 0
    finally:
        await qe.close()
