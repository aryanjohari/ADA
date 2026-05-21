"""`ada ingest-gsc` CLI."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone

UTC = timezone.utc
from pathlib import Path

from ada.config import Settings
from ada.ingest.gsc_service import ingest_gsc_search_analytics, parse_date
from ada.mission_defaults_resolve import (
    effective_gsc_site_url,
    mission_defaults_for_slug,
)
from ada.profile_runtime import enforce_profile_identity
from ada.query_engine import QueryEngine


def build_ingest_gsc_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    gsc = subparsers.add_parser(
        "ingest-gsc",
        help="Google Search Console Search Analytics ingestion",
    )
    gsc_sub = gsc.add_subparsers(dest="gsc_cmd", required=False)
    gsc.add_argument("--site", default=None, metavar="SITE", help="GSC property URL or sc-domain property")
    gsc.add_argument("--start-date", default=None, metavar="YYYY-MM-DD")
    gsc.add_argument("--end-date", default=None, metavar="YYYY-MM-DD")
    gsc.add_argument("--days", type=int, default=7, metavar="N", help="Relative date range ending today UTC")
    gsc.add_argument("--dimensions", default="date,query,page,country,device", metavar="CSV")
    gsc.add_argument("--row-limit", type=int, default=25000, metavar="N")
    gsc.add_argument("--dry-run", action="store_true")
    gsc.add_argument(
        "--mission",
        default=None,
        metavar="SLUG",
        help="Resolve GSC site URL from mission defaults_json over env",
    )
    verify = gsc_sub.add_parser("verify", help="Validate auth + fetch one day")
    verify.add_argument("--site", default=None, metavar="SITE")
    verify.add_argument("--date", required=True, metavar="YYYY-MM-DD")


async def run_ingest_gsc_cli(settings: Settings, args: argparse.Namespace) -> int:
    if not settings.enable_gsc_ingest:
        print("ingest-gsc: ADA_ENABLE_GSC_INGEST=1 required", flush=True)
        return 2
    settings.ensure_data_dir()
    schema_path = Path(__file__).resolve().parent.parent / "db" / "schema.sql"
    qe = QueryEngine(settings.state_db_path, schema_path, debounce_ms=settings.persist_debounce_ms)
    await qe.connect()
    await enforce_profile_identity(qe, settings)
    mission_slug = getattr(args, "mission", None)
    mdefaults = await mission_defaults_for_slug(qe, mission_slug)
    try:
        if getattr(args, "gsc_cmd", None) == "verify":
            site = (
                args.site
                or effective_gsc_site_url(
                    mission_defaults=mdefaults, env_site=settings.gsc_site_url
                )
                or ""
            ).strip()
            if not site:
                print("ingest-gsc verify: --site or GSC_SITE_URL required", flush=True)
                return 2
            day = parse_date(args.date)
            result = await ingest_gsc_search_analytics(
                qe,
                settings,
                site_url=site,
                start_date=day,
                end_date=day,
                dimensions=["date", "query"],
                row_limit=10,
                dry_run=True,
                idempotency_key=f"gsc-verify-{site}-{day.isoformat()}",
            )
            if result.error:
                print(f"ingest-gsc verify: error: {result.error}", flush=True)
                return 1
            print(json.dumps({"ok": True, "rows_seen": result.rows_seen}, indent=2))
            return 0

        site = (
            getattr(args, "site", None)
            or effective_gsc_site_url(
                mission_defaults=mdefaults, env_site=settings.gsc_site_url
            )
            or ""
        ).strip()
        if not site:
            print("ingest-gsc: --site or GSC_SITE_URL required", flush=True)
            return 2
        if args.start_date and args.end_date:
            start_date = parse_date(args.start_date)
            end_date = parse_date(args.end_date)
        else:
            end_date = datetime.now(UTC).date()
            start_date = end_date - timedelta(days=max(1, int(args.days)) - 1)
        dimensions = [d.strip().lower() for d in str(args.dimensions).split(",") if d.strip()]
        dry_run = bool(args.dry_run or settings.gsc_dry_run_default)
        idem = (
            f"gsc:{site}:{start_date.isoformat()}:{end_date.isoformat()}:"
            f"{','.join(dimensions)}:{int(args.row_limit)}"
        )
        result = await ingest_gsc_search_analytics(
            qe,
            settings,
            site_url=site,
            start_date=start_date,
            end_date=end_date,
            dimensions=dimensions,
            row_limit=max(1, int(args.row_limit)),
            dry_run=dry_run,
            idempotency_key=idem,
        )
        if result.error:
            print(f"ingest-gsc: error: {result.error}", flush=True)
            return 1
        print(
            json.dumps(
                {
                    "job_id": result.job_id,
                    "provider_id": result.provider_id,
                    "snapshots": result.snapshots,
                    "rows_seen": result.rows_seen,
                    "rows_written": result.rows_written,
                    "dry_run": dry_run,
                },
                indent=2,
            )
        )
        return 0
    finally:
        await qe.close()
