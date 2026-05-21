"""CLI for ``system_jobs`` (list / status / retry / cancel)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ada.config import Settings, load_dotenv_if_present
from ada.profile_runtime import enforce_profile_identity
from ada.query_engine import QueryEngine


async def _async_main(argv: list[str]) -> int:
    load_dotenv_if_present()
    settings = Settings.load()
    settings.ensure_data_dir()
    schema_path = Path(__file__).resolve().parent / "db" / "schema.sql"
    qe = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    await enforce_profile_identity(qe, settings)
    try:
        p = argparse.ArgumentParser(prog="ada jobs")
        sub = p.add_subparsers(dest="sub", required=True)
        pl = sub.add_parser("list", help="List recent system_jobs")
        pl.add_argument("--limit", type=int, default=50)
        pl.add_argument("--status", default=None)
        pl.add_argument("--mission-id", type=int, default=None)
        pl.add_argument("--kind", default=None)
        ps = sub.add_parser("status", help="Show one job as JSON")
        ps.add_argument("job_id", type=int)
        pr = sub.add_parser("retry", help="Clone a job as a new pending row")
        pr.add_argument("job_id", type=int)
        pc = sub.add_parser("cancel", help="Cancel a pending job")
        pc.add_argument("job_id", type=int)
        pe = sub.add_parser(
            "enqueue-ingest",
            help="Enqueue ingest.run for an ingest_jobs row (sets mission_id for observability)",
        )
        pe.add_argument("ingest_job_id", type=int)
        pe.add_argument(
            "--mission-id",
            type=int,
            default=None,
            help="Mission scope for the system_jobs row (optional)",
        )
        args = p.parse_args(argv)
        if args.sub == "list":
            rows = await qe.list_system_jobs(
                limit=args.limit,
                status=args.status,
                mission_id=args.mission_id,
                kind=args.kind,
            )
            print(json.dumps(rows, indent=2, default=str))
            return 0
        if args.sub == "status":
            row = await qe.get_system_job(args.job_id)
            if row is None:
                print("not found")
                return 1
            print(json.dumps(row, indent=2, default=str))
            return 0
        if args.sub == "retry":
            nid = await qe.retry_system_job_clone(args.job_id)
            if nid is None:
                print("retry failed (missing job?)")
                return 1
            print(f"new_job_id={nid}")
            return 0
        if args.sub == "cancel":
            ok = await qe.cancel_system_job(args.job_id)
            print(f"cancelled={ok}")
            return 0 if ok else 1
        if args.sub == "enqueue-ingest":
            jid = await qe.try_enqueue_ingest_run(
                args.ingest_job_id, mission_id=args.mission_id
            )
            if jid is None:
                print("nothing_enqueued (missing job, completed, or in-flight ingest.run)")
                return 1
            print(f"system_job_id={jid}")
            return 0
        return 2
    finally:
        await qe.close()


def main(argv: list[str] | None = None) -> int:
    import asyncio

    a = list(argv) if argv is not None else __import__("sys").argv[1:]
    return asyncio.run(_async_main(a))
