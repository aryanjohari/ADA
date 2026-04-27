"""Export all completed DRAFT `page` JSON from SQLite to a WordPress-style CSV (standalone)."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from pathlib import Path
from typing import Any

from ada.config import Settings, load_dotenv_if_present
from ada.profile_runtime import enforce_profile_identity
from ada.query_engine import QueryEngine

# Header must match a typical WordPress/CSV import (e.g. wordpress.csv).
WORDPRESS_CSV_FIELDNAMES = (
    "Title",
    "Content",
    "Slug",
    "Meta_Description",
    "Focus_Keyword",
)


def _parse_json_object(raw: str | None) -> dict[str, Any]:
    if not raw or not str(raw).strip():
        return {}
    try:
        o = json.loads(str(raw))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def resolve_focus_keyword(
    output_json: dict[str, Any],
    step_input_json: dict[str, Any],
    workflow_params_json: dict[str, Any],
) -> str:
    """1:1 with publish params: target_keyword_cluster, else niche."""
    for src in (output_json, step_input_json, workflow_params_json):
        t = src.get("target_keyword_cluster")
        if isinstance(t, str) and t.strip():
            return t.strip()
    for src in (step_input_json, workflow_params_json):
        n = src.get("niche")
        if isinstance(n, str) and n.strip():
            return n.strip()
    return ""


def page_to_wordpress_row(
    page: dict[str, Any],
    focus_keyword: str,
) -> dict[str, str]:
    """Map PageJsonV1 dump keys to WordPress column names."""
    title = str(page.get("title", "") or "")
    content = str(page.get("content", "") or "")
    slug = str(page.get("slug", "") or "")
    meta = str(page.get("meta_description", "") or "")
    return {
        "Title": title,
        "Content": content,
        "Slug": slug,
        "Meta_Description": meta,
        "Focus_Keyword": focus_keyword,
    }


SELECT_DRAFT_PAGES = """
SELECT
  ws.id,
  ws.workflow_id,
  w.kind,
  w.params_json,
  ws.input_json,
  ws.output_json
FROM workflow_steps AS ws
JOIN workflows AS w ON w.id = ws.workflow_id
WHERE ws.step_type = 'DRAFT'
  AND ws.status = 'completed'
ORDER BY ws.id ASC
"""


async def collect_wordpress_rows(
    settings: Settings,
    *,
    kind_filter: frozenset[str] | None = None,
) -> tuple[list[dict[str, str]], list[str]]:
    """
    Return (rows, skip_reasons) for logging: one row per completed DRAFT with a valid `page`.
    """
    project_root = Path(__file__).resolve().parent
    schema_path = project_root / "db" / "schema.sql"
    settings.ensure_data_dir()
    qe = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    try:
        await enforce_profile_identity(qe, settings)
        # Reuse the migrated connection from this session (read-only query).
        store = qe._ps
        if store is None:
            raise RuntimeError("QueryEngine not connected")
        conn = store._conn
        if conn is None:
            raise RuntimeError("PersistentState has no connection")
        cur = await conn.execute(SELECT_DRAFT_PAGES)
        db_rows = await cur.fetchall()
    finally:
        await qe.close()

    out_rows: list[dict[str, str]] = []
    skip_reasons: list[str] = []
    for row in db_rows:
        step_id, wf_id, kind, params_s, in_s, out_s = (
            int(row[0]),
            int(row[1]),
            str(row[2]),
            str(row[3] or "{}"),
            str(row[4] or "{}"),
            str(row[5] or "{}"),
        )
        if kind_filter is not None and str(kind) not in kind_filter:
            continue
        wfp = _parse_json_object(params_s)
        sinp = _parse_json_object(in_s)
        oj = _parse_json_object(out_s)
        page = oj.get("page")
        if not isinstance(page, dict):
            skip_reasons.append(
                f"step_id={step_id} workflow_id={wf_id}: no output_json.page"
            )
            continue
        need = ("title", "content", "slug", "meta_description")
        if not all(k in page for k in need):
            skip_reasons.append(
                f"step_id={step_id} workflow_id={wf_id}: page missing one of {need}"
            )
            continue
        focus = resolve_focus_keyword(oj, sinp, wfp)
        out_rows.append(page_to_wordpress_row(page, focus))
    return out_rows, skip_reasons


def write_wordpress_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=list(WORDPRESS_CSV_FIELDNAMES),
            quoting=csv.QUOTE_MINIMAL,
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Read all completed DRAFT step outputs (page JSON) from the Ada state DB "
            "for the current profile, and write one WordPress-style CSV row per draft."
        )
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("wordpress_export.csv"),
        help="Output CSV path (default: ./wordpress_export.csv)",
    )
    p.add_argument(
        "--only-kind",
        type=str,
        default="",
        help=(
            "Optional comma-separated workflow kinds to include "
            "(e.g. publish_entity_v1,publish_keyword_v1). "
            "Default: all kinds with a DRAFT step."
        ),
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Print skip reasons for rows without a valid page",
    )
    return p


async def async_main() -> int:
    load_dotenv_if_present()
    args = build_parser().parse_args()
    settings = Settings.load()
    kind_filter: frozenset[str] | None = None
    if str(args.only_kind).strip():
        kind_filter = frozenset(
            s.strip() for s in str(args.only_kind).split(",") if s.strip()
        )
    rows, skips = await collect_wordpress_rows(settings, kind_filter=kind_filter)
    write_wordpress_csv(args.output, rows)
    print(
        f"Wrote {len(rows)} row(s) to {args.output.resolve()}",
        file=sys.stdout,
    )
    if args.verbose and skips:
        for line in skips:
            print(f"skip: {line}", file=sys.stderr)
    elif skips and not args.verbose:
        print(
            f"Skipped {len(skips)} step(s) (no valid page). Use --verbose for reasons.",
            file=sys.stderr,
        )
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(async_main()))


if __name__ == "__main__":
    main()
