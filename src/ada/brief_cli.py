"""`ada brief` — deterministic SQL-grounded operator brief."""

from __future__ import annotations

import argparse
import os
import sys

from ada.config import Settings
from ada.mission_control.digest import (
    goal_text_for_daily_brief,
    render_brief_from_settings,
    write_brief_artifact,
)
from ada.profile_runtime import enforce_profile_identity
from ada.query_engine import TASK_KIND_GOAL, QueryEngine


async def run_brief_cli(
    settings: Settings,
    *,
    mission_slug: str | None,
    enqueue: bool,
) -> int:
    from pathlib import Path

    slug = (
        mission_slug or os.environ.get("ADA_CHAT_DEFAULT_MISSION", "")
    ).strip() or None
    text = render_brief_from_settings(settings, mission_slug=slug)
    path = write_brief_artifact(settings, text)
    print(text, end="" if text.endswith("\n") else "\n")
    print(f"# artifact: {path}", file=sys.stderr)

    if not enqueue:
        return 0

    if not slug:
        print(
            "brief --enqueue: set --mission or ADA_CHAT_DEFAULT_MISSION",
            file=sys.stderr,
        )
        return 2
    try:
        tid = await enqueue_brief_goal(settings, mission_slug=slug, brief_md=text)
    except ValueError as e:
        print(f"brief --enqueue: {e}", file=sys.stderr)
        return 2
    print(f"# enqueued goal task_id={tid}", file=sys.stderr)
    return 0


async def enqueue_brief_goal(
    settings: Settings,
    *,
    mission_slug: str,
    brief_md: str | None = None,
) -> int:
    """Insert pending goal with SQL-grounded brief text. Returns task_id."""
    from pathlib import Path

    slug = mission_slug.strip()
    text = brief_md or render_brief_from_settings(settings, mission_slug=slug)
    schema_path = Path(__file__).resolve().parent / "db" / "schema.sql"
    qe = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    await enforce_profile_identity(qe, settings)
    try:
        row = await qe.get_mission_by_slug(slug)
        if row is None:
            raise ValueError(f"no mission with slug {slug!r}")
        mission_id = int(row["id"])
        tid = await qe.insert_task(
            goal_text_for_daily_brief(text),
            status="pending",
            task_kind=TASK_KIND_GOAL,
            mission_id=mission_id,
        )
        return tid
    finally:
        await qe.close()


def build_brief_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "brief",
        help="Print SQL-grounded brief (flags + snapshot); optional goal enqueue",
    )
    p.add_argument(
        "--mission",
        default=None,
        metavar="SLUG",
        help="Mission scope (default: ADA_CHAT_DEFAULT_MISSION)",
    )
    p.add_argument(
        "--enqueue",
        action="store_true",
        help="Enqueue daemon goal with brief text (goal_add path)",
    )
