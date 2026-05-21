"""`ada profile brief` — read-only cross-mission JSON."""

from __future__ import annotations

import argparse
import json
import sys

from ada.config import Settings
from ada.mission_control.digest import build_profile_brief_payload


def build_profile_parser(sub: argparse._SubParsersAction) -> None:
    prof = sub.add_parser("profile", help="Profile-scoped read-only summaries")
    prof_sub = prof.add_subparsers(dest="profile_cmd", required=True)
    prof_sub.add_parser(
        "brief",
        help="JSON: flags + mission overviews (no writes)",
    )


async def run_profile_brief_cli(settings: Settings) -> int:
    payload = build_profile_brief_payload(settings)
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    return 0
