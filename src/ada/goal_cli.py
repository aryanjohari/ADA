"""CLI for enqueueing background goal tasks (`ada goal`)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ada.config import Settings
from ada.query_engine import TASK_KIND_GOAL, QueryEngine
from ada.profile_runtime import enforce_profile_identity


# Max goal text length (bytes) — pathological input guard
GOAL_TEXT_MAX_CHARS = 32 * 1024
# Default terminal preview for tasks.current_output in `goal show` (use --full for all)
GOAL_SHOW_OUTPUT_PREVIEW_CHARS = 4000


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="ada goal",
        description="Enqueue background goal tasks (SQLite; consumed by ada daemon).",
    )
    sub = p.add_subparsers(dest="subcmd", required=True)

    add_p = sub.add_parser("add", help="Insert a pending goal task")
    add_p.add_argument(
        "goal",
        nargs="+",
        help="Goal text (multi-word allowed)",
    )
    add_p.add_argument(
        "--mission",
        default=None,
        metavar="SLUG",
        help="Attach to mission by slug (must exist)",
    )
    add_p.add_argument(
        "--plan-json",
        default="{}",
        metavar="JSON",
        help="Initial plan_json string (must be valid JSON; default: {})",
    )

    list_p = sub.add_parser("list", help="List recent goal tasks")
    list_p.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max rows (default 50, max 500)",
    )
    list_p.add_argument(
        "--status",
        default=None,
        metavar="STATUS",
        help="Filter by status (e.g. pending, executing, completed, failed)",
    )
    list_p.add_argument(
        "--mission",
        default=None,
        metavar="SLUG",
        help="Only tasks for this mission slug",
    )

    show_p = sub.add_parser("show", help="Show one goal task by id")
    show_p.add_argument("task_id", type=int, help="tasks.id")
    show_p.add_argument(
        "--full",
        action="store_true",
        help="Print full current_output (default: preview if very long)",
    )

    return p.parse_args(argv)


async def _run_add(qe: QueryEngine, args: argparse.Namespace) -> int:
    goal = " ".join(args.goal).strip()
    if not goal:
        print("goal add: empty goal text", file=sys.stderr)
        return 2
    if len(goal) > GOAL_TEXT_MAX_CHARS:
        print(
            f"goal add: goal text exceeds {GOAL_TEXT_MAX_CHARS} characters",
            file=sys.stderr,
        )
        return 2
    raw_plan = args.plan_json
    try:
        json.loads(raw_plan)
    except json.JSONDecodeError as e:
        print(f"goal add: --plan-json is not valid JSON: {e}", file=sys.stderr)
        return 2
    mission_id: int | None = None
    if args.mission is not None:
        ms = args.mission.strip()
        if not ms:
            print("goal add: empty --mission slug", file=sys.stderr)
            return 2
        row = await qe.get_mission_by_slug(ms)
        if row is None:
            print(f"goal add: no mission with slug {ms!r}", file=sys.stderr)
            return 2
        mission_id = int(row["id"])
    tid = await qe.insert_task(
        goal,
        status="pending",
        task_kind=TASK_KIND_GOAL,
        mission_id=mission_id,
    )
    if raw_plan.strip() != "{}":
        await qe.set_task_plan_json(tid, raw_plan)
    print(tid)
    return 0


async def _run_list(qe: QueryEngine, args: argparse.Namespace) -> int:
    limit = max(1, min(int(args.limit), 500))
    ms = args.mission.strip() if args.mission else None
    rows = await qe.list_goal_tasks(
        limit=limit, status=args.status, mission_slug=ms
    )
    if not rows:
        print("(no goal tasks)")
        return 0
    for r in rows:
        gid = r["id"]
        st = r["status"]
        g = r["goal"].replace("\n", " ")[:120]
        if len(r["goal"]) > 120:
            g += "…"
        slug = r.get("mission_slug") or ""
        if slug:
            print(f"{gid}\t{st}\t{slug}\t{g}")
        else:
            print(f"{gid}\t{st}\t\t{g}")
    return 0


async def _run_show(qe: QueryEngine, args: argparse.Namespace) -> int:
    try:
        r = await qe.get_goal_task(args.task_id)
    except LookupError:
        print(f"goal show: no task id {args.task_id}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"goal show: {e}", file=sys.stderr)
        return 2
    print(f"id:\t{r['id']}")
    print(f"status:\t{r['status']}")
    mid = r.get("mission_id")
    mslug = r.get("mission_slug")
    if mid is not None:
        print(f"mission_id:\t{mid}")
    else:
        print("mission_id:\t")
    if mslug:
        print(f"mission_slug:\t{mslug}")
    else:
        print("mission_slug:\t")
    print(f"created_at:\t{r['created_at']}")
    print(f"updated_at:\t{r['updated_at']}")
    print(f"goal:\t{r['goal']}")
    print(f"plan_json:\t{r['plan_json']}")
    out = r.get("current_output", "")
    print("current_output:")
    if args.full or len(out) <= GOAL_SHOW_OUTPUT_PREVIEW_CHARS:
        print(out)
    else:
        preview = out[:GOAL_SHOW_OUTPUT_PREVIEW_CHARS]
        print(preview)
        print(
            f"\n… truncated ({len(out)} characters total). "
            f"Re-run with: ada goal show {args.task_id} --full",
            file=sys.stderr,
        )
    return 0


async def async_main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
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
        if args.subcmd == "add":
            return await _run_add(qe, args)
        if args.subcmd == "list":
            return await _run_list(qe, args)
        if args.subcmd == "show":
            return await _run_show(qe, args)
    finally:
        await qe.close()
    return 2
