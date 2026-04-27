"""CLI for durable approval records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ada.config import Settings
from ada.profile_runtime import enforce_profile_identity
from ada.query_engine import QueryEngine


def build_approval_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    ap = subparsers.add_parser("approval", help="Manage approval records")
    ap_sub = ap.add_subparsers(dest="approval_cmd", required=True)
    req = ap_sub.add_parser("request", help="Create or update approval request")
    req.add_argument("--artifact-type", required=True)
    req.add_argument("--artifact-ref", required=True)
    req.add_argument("--reason", default="")
    req.add_argument("--requested-by", default="operator")
    decide = ap_sub.add_parser("decide", help="Approve or reject an artifact")
    decide.add_argument("--artifact-type", required=True)
    decide.add_argument("--artifact-ref", required=True)
    decide.add_argument("--status", required=True, choices=["approved", "rejected", "expired"])
    decide.add_argument("--reason", default="")
    decide.add_argument("--approved-by", default="operator")
    show = ap_sub.add_parser("show", help="Show approval record")
    show.add_argument("--artifact-type", required=True)
    show.add_argument("--artifact-ref", required=True)


async def run_approval_cli(settings: Settings, args: argparse.Namespace) -> int:
    settings.ensure_data_dir()
    schema_path = Path(__file__).resolve().parent / "db" / "schema.sql"
    qe = QueryEngine(settings.state_db_path, schema_path, debounce_ms=settings.persist_debounce_ms)
    await qe.connect()
    await enforce_profile_identity(qe, settings)
    try:
        if args.approval_cmd == "request":
            await qe.upsert_approval_record(
                artifact_type=str(args.artifact_type).strip(),
                artifact_ref=str(args.artifact_ref).strip(),
                status="requested",
                requested_by=str(args.requested_by).strip(),
                reason=str(args.reason).strip(),
            )
            print("ok")
            return 0
        if args.approval_cmd == "decide":
            await qe.upsert_approval_record(
                artifact_type=str(args.artifact_type).strip(),
                artifact_ref=str(args.artifact_ref).strip(),
                status=str(args.status).strip(),
                approved_by=str(args.approved_by).strip(),
                reason=str(args.reason).strip(),
                set_decided=True,
            )
            print("ok")
            return 0
        if args.approval_cmd == "show":
            row = await qe.get_approval_record(
                artifact_type=str(args.artifact_type).strip(),
                artifact_ref=str(args.artifact_ref).strip(),
            )
            if row is None:
                print("(not found)")
                return 1
            print(json.dumps(row, indent=2, default=str))
            return 0
        return 2
    finally:
        await qe.close()
