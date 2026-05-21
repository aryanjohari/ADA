"""CLI for programme apply (`ada programme apply`)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ada.config import Settings
from ada.programme.apply import confirm_and_apply
from ada.programme.packet import ProgrammePacket
from ada.profile_runtime import enforce_profile_identity
from ada.query_engine import QueryEngine


async def run_programme_apply(
    settings: Settings,
    *,
    packet_path: str,
    skip_confirm: bool = False,
) -> int:
    settings.ensure_data_dir()
    schema_path = Path(__file__).resolve().parent / "db" / "schema.sql"
    qe = QueryEngine(settings.state_db_path, schema_path)
    await qe.connect()
    await enforce_profile_identity(qe, settings)
    try:
        path = Path(packet_path)
        if not path.is_file():
            print(f"programme apply: file not found: {path}", file=sys.stderr)
            return 2
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"programme apply: invalid JSON: {e}", file=sys.stderr)
            return 2
        try:
            packet = ProgrammePacket.model_validate(data)
        except Exception as e:
            print(f"programme apply: invalid packet: {e}", file=sys.stderr)
            return 2

        print(f"Mission: {packet.mission_slug!r} — {packet.title!r}")
        print(f"Risk: {packet.risk_summary or '(none)'}")
        approved = skip_confirm
        if not skip_confirm:
            ans = input("Apply programme? [y/N] ").strip().lower()
            approved = ans in ("y", "yes")
        out = await confirm_and_apply(
            qe, settings, packet, approved=approved, session_id=None
        )
        if out.get("denied"):
            print("Apply denied.", file=sys.stderr)
            return 1
        if not out.get("ok"):
            print(f"Apply failed: {out}", file=sys.stderr)
            return 1
        print(json.dumps(out, indent=2))
        return 0
    finally:
        await qe.close()
