"""CLI for missions (`ada mission`)."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

from ada.config import Settings
from ada.config_deprecation import DEPRECATED_ENVS, env_patch_from_current_process
from ada.mission_tick import run_mission_tick
from ada.query_engine import QueryEngine
from ada.profile_runtime import enforce_profile_identity

_MISSION_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="ada mission",
        description="Create and inspect missions (SQLite).",
    )
    sub = p.add_subparsers(dest="subcmd", required=True)

    init_p = sub.add_parser("init", help="Insert a mission row")
    init_p.add_argument(
        "slug",
        metavar="SLUG",
        help="Unique slug (lowercase letters, digits, hyphen, underscore)",
    )
    init_p.add_argument(
        "--title",
        required=True,
        metavar="TEXT",
        help="Mission title",
    )
    init_p.add_argument("--niche", default=None, metavar="TEXT")
    init_p.add_argument("--topic", default=None, metavar="TEXT")
    init_p.add_argument(
        "--defaults-json",
        default=None,
        metavar="JSON",
        help="Merged into playbook params when using workflow enqueue --mission",
    )
    init_p.add_argument(
        "--schedule-hint-json",
        default=None,
        metavar="JSON",
        help='Optional ada mission tick hints, e.g. {"version":1,"jobs":[...]}',
    )

    tick_p = sub.add_parser(
        "tick",
        help="Deterministic tick: schedule_hint_json v1 + SQLite state last-run keys",
    )
    tick_p.add_argument(
        "--mission",
        required=True,
        metavar="SLUG",
        help="Mission slug",
    )
    tick_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print due jobs without writes (no ingest, enqueue, or state bumps)",
    )
    tick_p.add_argument(
        "--force",
        action="store_true",
        help="Run every listed job ignoring min_interval_hours last-run state",
    )

    list_p = sub.add_parser("list", help="List missions (newest first)")
    list_p.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max rows (default 50, max 500)",
    )

    show_p = sub.add_parser("show", help="Print one mission by slug")
    show_p.add_argument("slug", metavar="SLUG")

    mig_p = sub.add_parser(
        "migrate-env",
        help="Build a missions.defaults_json patch from deprecated env vars (dry-run unless --apply)",
    )
    mig_p.add_argument(
        "slug",
        metavar="SLUG",
        help="Mission slug to merge into",
    )
    mig_p.add_argument(
        "--apply",
        action="store_true",
        help="Persist merge into SQLite (default: print JSON only)",
    )
    mig_p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing defaults_json keys present in the env patch",
    )
    mig_p.add_argument(
        "--only",
        default=None,
        metavar="ENV,...",
        help="Comma-separated deprecated env var names (default: all set in the environment)",
    )

    return p.parse_args(argv)


def _validate_slug(slug: str) -> bool:
    return bool(slug.strip() and _MISSION_SLUG_RE.fullmatch(slug.strip()))


async def _run_init(qe: QueryEngine, args: argparse.Namespace) -> int:
    slug = args.slug.strip()
    title = args.title.strip()
    if not title:
        print("mission init: empty --title", file=sys.stderr)
        return 2
    if not _validate_slug(slug):
        print(
            "mission init: slug must match ^[a-z0-9][a-z0-9_-]{1,63}$",
            file=sys.stderr,
        )
        return 2
    dj = getattr(args, "defaults_json", None)
    sj = getattr(args, "schedule_hint_json", None)
    defaults_obj: dict | None = None
    schedule_obj: dict | None = None
    if dj is not None:
        dj_s = str(dj).strip()
        if not dj_s:
            print("mission init: empty --defaults-json", file=sys.stderr)
            return 2
        try:
            parsed = json.loads(dj_s)
        except json.JSONDecodeError as e:
            print(f"mission init: invalid --defaults-json: {e}", file=sys.stderr)
            return 2
        if not isinstance(parsed, dict):
            print("mission init: --defaults-json must be a JSON object", file=sys.stderr)
            return 2
        defaults_obj = parsed
    if sj is not None:
        sj_s = str(sj).strip()
        if not sj_s:
            print("mission init: empty --schedule-hint-json", file=sys.stderr)
            return 2
        try:
            parsed_s = json.loads(sj_s)
        except json.JSONDecodeError as e:
            print(f"mission init: invalid --schedule-hint-json: {e}", file=sys.stderr)
            return 2
        if not isinstance(parsed_s, dict):
            print(
                "mission init: --schedule-hint-json must be a JSON object",
                file=sys.stderr,
            )
            return 2
        schedule_obj = parsed_s
    try:
        mid = await qe.create_mission(
            slug,
            title,
            niche=args.niche,
            topic=args.topic,
            defaults_json=defaults_obj,
            schedule_hint_json=schedule_obj,
        )
    except sqlite3.IntegrityError:
        print(f"mission init: slug already exists: {slug}", file=sys.stderr)
        return 2
    print(mid)
    return 0


async def _run_list(qe: QueryEngine, args: argparse.Namespace) -> int:
    limit = max(1, min(int(args.limit), 500))
    rows = await qe.list_missions(limit=limit)
    if not rows:
        print("(no missions)")
        return 0
    for r in rows:
        print(f"{r['id']}\t{r['slug']}\t{r['title']}")
    return 0


async def _run_show(qe: QueryEngine, args: argparse.Namespace) -> int:
    slug = args.slug.strip()
    r = await qe.get_mission_by_slug(slug)
    if r is None:
        print(f"mission show: no mission with slug {slug!r}", file=sys.stderr)
        return 2
    dj = r.get("defaults_json")
    dj_out = dj if isinstance(dj, dict) else {}
    sh = r.get("schedule_hint_json")
    print(f"id:\t{r['id']}")
    print(f"slug:\t{r['slug']}")
    print(f"title:\t{r['title']}")
    print(f"niche:\t{r.get('niche') or ''}")
    print(f"topic:\t{r.get('topic') or ''}")
    print(f"created_at:\t{r['created_at']}")
    print(f"updated_at:\t{r['updated_at']}")
    print(f"defaults_json:\t{json.dumps(dj_out, ensure_ascii=False)}")
    print(
        f"schedule_hint_json:\t"
        f"{json.dumps(sh, ensure_ascii=False) if sh is not None else 'null'}"
    )
    brief = r.get("brief_md") or ""
    if brief.strip():
        print("brief_md:")
        print(brief)
    return 0


async def _run_tick(
    qe: QueryEngine,
    settings: Settings,
    args: argparse.Namespace,
) -> int:
    return await run_mission_tick(
        qe,
        settings,
        mission_slug=str(args.mission).strip(),
        dry_run=bool(args.dry_run),
        force=bool(args.force),
    )


async def _run_migrate_env(qe: QueryEngine, args: argparse.Namespace) -> int:
    slug = str(args.slug).strip()
    if not _validate_slug(slug):
        print(
            "mission migrate-env: slug must match ^[a-z0-9][a-z0-9_-]{1,63}$",
            file=sys.stderr,
        )
        return 2
    row = await qe.get_mission_by_slug(slug)
    if row is None:
        print(f"mission migrate-env: no mission with slug {slug!r}", file=sys.stderr)
        return 2

    only_raw = getattr(args, "only", None)
    only_env: frozenset[str] | None = None
    if only_raw is not None and str(only_raw).strip():
        parts = {p.strip() for p in str(only_raw).split(",") if p.strip()}
        known = frozenset(d.env_var for d in DEPRECATED_ENVS)
        unknown = sorted(parts - known)
        if unknown:
            print(
                f"mission migrate-env: unknown --only name(s): {unknown}",
                file=sys.stderr,
            )
            return 2
        only_env = frozenset(parts)

    patch = env_patch_from_current_process(only_env_vars=only_env)
    if not patch:
        print(
            "mission migrate-env: no deprecated env vars set (nothing to merge)",
            file=sys.stderr,
        )
        return 0

    force = bool(getattr(args, "force", False))
    apply = bool(getattr(args, "apply", False))
    cur = row.get("defaults_json")
    current: dict = dict(cur) if isinstance(cur, dict) else {}
    would_apply: dict = {}
    skipped: list[str] = []
    for k, v in patch.items():
        if k in current and not force:
            skipped.append(k)
            continue
        would_apply[k] = v

    out: dict = {"env_patch": patch, "would_apply": would_apply, "skipped_existing_keys": skipped}
    if not apply:
        print(json.dumps(out, ensure_ascii=False))
        return 0

    merged = await qe.update_mission_defaults_json(slug, patch, force=force)
    print(json.dumps({"merged_defaults_json": merged}, ensure_ascii=False))
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
        if args.subcmd == "init":
            return await _run_init(qe, args)
        if args.subcmd == "tick":
            return await _run_tick(qe, settings, args)
        if args.subcmd == "list":
            return await _run_list(qe, args)
        if args.subcmd == "show":
            return await _run_show(qe, args)
        if args.subcmd == "migrate-env":
            return await _run_migrate_env(qe, args)
    finally:
        await qe.close()
    return 2
