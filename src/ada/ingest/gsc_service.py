"""GSC ingestion service with idempotent persistence and audit logging."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable

from ada.config import Settings
from ada.ingest.gsc_client import GSCClient
from ada.ingest.gsc_errors import GSCError
from ada.ingest.gsc_models import GSCQueryRequest, GSCResponseRow
from ada.query_engine import QueryEngine


@dataclass
class GSCIngestResult:
    job_id: int
    provider_id: int
    snapshots: int
    rows_seen: int
    rows_written: int
    error: str = ""


def _iter_windows(start: date, end: date, *, max_days: int) -> Iterable[tuple[date, date]]:
    cursor = start
    while cursor <= end:
        w_end = min(end, cursor + timedelta(days=max_days - 1))
        yield cursor, w_end
        cursor = w_end + timedelta(days=1)


def _row_hash(dimensions: dict[str, str], row: GSCResponseRow) -> str:
    blob = json.dumps(
        {
            "date": dimensions.get("date", ""),
            "query": dimensions.get("query", ""),
            "page": dimensions.get("page", ""),
            "country": dimensions.get("country", ""),
            "device": dimensions.get("device", ""),
            "clicks": row.clicks,
            "impressions": row.impressions,
            "ctr": row.ctr,
            "position": row.position,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


async def ingest_gsc_search_analytics(
    qe: QueryEngine,
    settings: Settings,
    *,
    site_url: str,
    start_date: date,
    end_date: date,
    dimensions: list[str],
    row_limit: int,
    dry_run: bool,
    idempotency_key: str | None = None,
) -> GSCIngestResult:
    if start_date > end_date:
        return GSCIngestResult(0, 0, 0, 0, 0, error="start_date cannot be after end_date")
    provider_id = 0
    if not dry_run:
        provider_id = await qe.ensure_analytics_provider(
            provider="gsc",
            property_ref=site_url,
            config_json={"dimensions": dimensions, "schema_version": "gsc.v1"},
        )
    params = {
        "site_url": site_url,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "dimensions": dimensions,
        "row_limit": row_limit,
        "dry_run": dry_run,
    }
    job_id = await qe.create_ingest_job(
        "gsc_search_analytics_v1", params, idempotency_key=idempotency_key
    )
    await qe.update_ingest_job(job_id, status="running", set_started=True)
    await qe.append_action_log(
        "gsc_ingest_started",
        {"ingest_job_id": job_id, "site_url": site_url, "params": params},
        session_id=None,
    )
    client = GSCClient(settings)
    deadline = time.monotonic() + settings.gsc_timeout_total_sec
    rows_seen = 0
    rows_written = 0
    snapshots = 0
    try:
        for win_start, win_end in _iter_windows(
            start_date, end_date, max_days=settings.gsc_max_days_per_request
        ):
            start_row = 0
            while True:
                req = GSCQueryRequest(
                    site_url=site_url,
                    start_date=win_start,
                    end_date=win_end,
                    dimensions=dimensions,
                    row_limit=min(row_limit, settings.gsc_page_size),
                    start_row=start_row,
                )
                resp = await client.query(req, budget_deadline_monotonic=deadline)
                rows = resp.rows
                rows_seen += len(rows)
                request_hash = hashlib.sha256(
                    json.dumps(
                        {
                            "site_url": site_url,
                            "start_date": win_start.isoformat(),
                            "end_date": win_end.isoformat(),
                            "dimensions": dimensions,
                            "row_limit": req.row_limit,
                            "start_row": start_row,
                            "schema_version": "gsc.v1",
                        },
                        sort_keys=True,
                    ).encode("utf-8")
                ).hexdigest()
                if dry_run:
                    snapshots += 1
                else:
                    raw_body = json.dumps(
                        {
                            "window_start": win_start.isoformat(),
                            "window_end": win_end.isoformat(),
                            "start_row": start_row,
                            "rows": [r.model_dump() for r in rows],
                        },
                        ensure_ascii=False,
                    )
                    await qe.insert_ingest_raw(
                        ingest_job_id=job_id,
                        source="gsc_search_analytics",
                        uri=f"{site_url}:{win_start.isoformat()}:{win_end.isoformat()}:{start_row}",
                        body=raw_body,
                        meta_json={"dimensions": dimensions, "schema_version": "gsc.v1"},
                    )
                    snapshot_id = await qe.upsert_analytics_snapshot(
                        provider_id=provider_id,
                        ingest_job_id=job_id,
                        window_start=win_start.isoformat(),
                        window_end=win_end.isoformat(),
                        request_hash=request_hash,
                        response_version="gsc.v1",
                        row_count=len(rows),
                    )
                    snapshots += 1
                    for row in rows:
                        dim_map = row.to_dimension_map(dimensions)
                        await qe.upsert_gsc_search_analytics_row(
                            provider_id=provider_id,
                            snapshot_id=snapshot_id,
                            data_date=dim_map.get("date", win_start.isoformat()),
                            query=dim_map.get("query", ""),
                            page=dim_map.get("page", ""),
                            country=dim_map.get("country", ""),
                            device=dim_map.get("device", ""),
                            clicks=float(row.clicks),
                            impressions=float(row.impressions),
                            ctr=float(row.ctr),
                            position=float(row.position),
                            row_hash=_row_hash(dim_map, row),
                        )
                        rows_written += 1
                if len(rows) < req.row_limit:
                    break
                start_row += req.row_limit
                if rows_seen >= settings.gsc_max_rows_per_run:
                    raise ValueError(
                        f"GSC ingestion exceeded ADA_GSC_MAX_ROWS_PER_RUN={settings.gsc_max_rows_per_run}"
                    )
        await qe.update_ingest_job(job_id, status="completed", set_completed=True)
        await qe.append_action_log(
            "gsc_ingest_completed",
            {
                "ingest_job_id": job_id,
                "site_url": site_url,
                "snapshots": snapshots,
                "rows_seen": rows_seen,
                "rows_written": rows_written,
                "dry_run": dry_run,
            },
            session_id=None,
        )
        return GSCIngestResult(job_id, provider_id, snapshots, rows_seen, rows_written)
    except GSCError as e:
        err = f"{e.error_code}: {e}"
        await qe.update_ingest_job(job_id, status="failed", error=err[:2000], set_completed=True)
        await qe.append_action_log(
            "gsc_ingest_failed",
            {
                "ingest_job_id": job_id,
                "error_code": e.error_code,
                "error": str(e),
                "site_url": site_url,
            },
            session_id=None,
        )
        return GSCIngestResult(job_id, provider_id, snapshots, rows_seen, rows_written, error=err)
    except Exception as e:
        err = str(e)
        await qe.update_ingest_job(job_id, status="failed", error=err[:2000], set_completed=True)
        await qe.append_action_log(
            "gsc_ingest_failed",
            {"ingest_job_id": job_id, "error_code": "unknown", "error": err, "site_url": site_url},
            session_id=None,
        )
        return GSCIngestResult(job_id, provider_id, snapshots, rows_seen, rows_written, error=err)


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()
