"""CLI for missions (`ada mission`)."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

import yaml

from ada.config import Settings, _find_project_root
from ada.config_deprecation import DEPRECATED_ENVS, env_patch_from_current_process
from ada.mission_control.audit_scope import audit_mission_scope
from ada.mission_control.snapshot import build_snapshot_from_settings
from ada.mission_tick import run_mission_tick
from ada.observability.queries import open_readonly_connection
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

    status_p = sub.add_parser(
        "status",
        help="Read-only mission control snapshot + flags (JSON)",
    )
    status_p.add_argument("slug", metavar="SLUG")

    audit_p = sub.add_parser(
        "audit-scope",
        help="Read-only graph/knowledge scope audit for a mission (JSON)",
    )
    audit_p.add_argument("slug", metavar="SLUG")

    tmpl_p = sub.add_parser(
        "apply-template",
        help="Build ProgrammePacket from templates/missions/<name>.yaml",
    )
    tmpl_p.add_argument("name", metavar="NAME", help="Template name (without .yaml)")
    tmpl_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned packet JSON only (no DB writes)",
    )
    tmpl_p.add_argument(
        "--yes",
        action="store_true",
        help="Apply without interactive confirm",
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


async def _run_status(settings: Settings, args: argparse.Namespace) -> int:
    slug = str(args.slug).strip()
    if not _validate_slug(slug):
        print(
            "mission status: slug must match ^[a-z0-9][a-z0-9_-]{1,63}$",
            file=sys.stderr,
        )
        return 2
    conn = open_readonly_connection(settings.state_db_path)
    try:
        cur = conn.execute("SELECT id FROM missions WHERE slug = ?", (slug,))
        row = cur.fetchone()
        if row is None:
            print(f"mission status: no mission with slug {slug!r}", file=sys.stderr)
            return 2
        mid = int(row[0])
    finally:
        conn.close()
    snap = build_snapshot_from_settings(
        settings,
        mission_id=mid,
        mission_slug=slug,
        profile_scope=True,
    )
    print(json.dumps(snap, ensure_ascii=False, indent=2))
    return 0


async def _run_audit_scope(settings: Settings, args: argparse.Namespace) -> int:
    slug = str(args.slug).strip()
    if not _validate_slug(slug):
        print(
            "mission audit-scope: slug must match ^[a-z0-9][a-z0-9_-]{1,63}$",
            file=sys.stderr,
        )
        return 2
    conn = open_readonly_connection(settings.state_db_path)
    try:
        cur = conn.execute("SELECT id FROM missions WHERE slug = ?", (slug,))
        row = cur.fetchone()
        if row is None:
            print(f"mission audit-scope: no mission with slug {slug!r}", file=sys.stderr)
            return 2
        mid = int(row[0])
        report = audit_mission_scope(conn, mission_id=mid, mission_slug=slug)
    finally:
        conn.close()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


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


def list_mission_template_names() -> list[str]:
    """Stem names of templates/missions/*.yaml (for Plan harness)."""
    root = _find_project_root()
    folder = root / "templates" / "missions"
    if not folder.is_dir():
        return []
    return sorted(p.stem for p in folder.glob("*.yaml") if p.is_file())


def load_mission_template(name: str) -> dict:
    """Load templates/missions/<name>.yaml as a programme packet dict (HUD/CLI)."""
    return _load_mission_template(name)


def _load_mission_template(name: str) -> dict:
    root = _find_project_root()
    path = (root / "templates" / "missions" / f"{name.strip()}.yaml").resolve()
    if not path.is_file():
        raise FileNotFoundError(f"template not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("template must be a YAML mapping")
    slug = str(raw.get("slug") or raw.get("name") or name).strip()
    defaults = dict(raw.get("defaults_json") or {})
    pack = raw.get("pack")
    if pack is not None and str(pack).strip():
        defaults["pack"] = str(pack).strip()
    brief = raw.get("brief_md")
    brief_md = str(brief).strip() if brief is not None else ""
    return {
        "mission_slug": slug,
        "title": str(raw.get("title") or slug),
        "defaults_json": defaults,
        "schedule_hint_json": raw.get("schedule_hint_json"),
        "knowledge_sources": list(raw.get("knowledge_sources") or []),
        "recommended_cron": list(raw.get("recommended_cron") or []),
        "skills_enabled": list(raw.get("skills_enabled") or []),
        "risk_summary": str(
            raw.get("risk_summary")
            or f"Mission template {name!r} — review before apply."
        ),
        "brief_md": brief_md,
    }


async def _run_apply_template(
    qe: QueryEngine, settings: Settings, args: argparse.Namespace
) -> int:
    from ada.programme.apply import confirm_and_apply
    from ada.programme.packet import ProgrammePacket

    try:
        data = _load_mission_template(args.name)
    except (FileNotFoundError, ValueError) as e:
        print(f"apply-template: {e}", file=sys.stderr)
        return 2
    try:
        packet = ProgrammePacket.model_validate(data)
    except Exception as e:
        print(f"apply-template: invalid packet: {e}", file=sys.stderr)
        return 2
    if args.dry_run:
        print(json.dumps(packet.model_dump(mode="json"), indent=2))
        return 0
    approved = bool(args.yes)
    if not approved:
        ans = input(f"Apply template {args.name!r} to mission {packet.mission_slug!r}? [y/N] ")
        approved = ans.strip().lower() in ("y", "yes")
    out = await confirm_and_apply(qe, settings, packet, approved=approved)
    if out.get("denied"):
        return 1
    if not out.get("ok"):
        print(json.dumps(out), file=sys.stderr)
        return 1
    print(json.dumps(out, indent=2))
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
        if args.subcmd == "status":
            return await _run_status(settings, args)
        if args.subcmd == "audit-scope":
            return await _run_audit_scope(settings, args)
        if args.subcmd == "apply-template":
            return await _run_apply_template(qe, settings, args)
    finally:
        await qe.close()
    return 2
