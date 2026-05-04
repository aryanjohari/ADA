"""`python -m ada [chat|daemon|goal|workflow|dream|ingest-rss|...]`."""

from __future__ import annotations

import argparse
import asyncio
import sys

from ada.config import Settings, load_dotenv_if_present
from ada.cli import (
    run_chat,
    run_dream_cli,
    run_enrich_graph_cli,
    run_extract_graph_lite_cli,
)
from ada.goal_cli import async_main as goal_async_main
from ada.ingest.gets import run_ingest_gets_cli
from ada.ingest.brand import run_ingest_brand_cli
from ada.ingest.gsc_cli import build_ingest_gsc_parser, run_ingest_gsc_cli
from ada.ingest.keywords import run_ingest_keywords_cli
from ada.ingest.rss import run_ingest_rss_cli, run_register_rss_source_cli
from ada.keyword_select_cli import run_keyword_select_cli
from ada.main import main_daemon
from ada.approval_cli import build_approval_parser, run_approval_cli
from ada.triage.run import run_triage_cli
from ada.matrix_cli import run_matrix_scan_cli
from ada.observability.gate_failures_cli import run_gate_failures_cli
from ada.workflow_cli import (
    run_workflow_enqueue_cli,
    run_workflow_retry_cli,
    run_workflow_status_cli,
)


def main() -> None:
    load_dotenv_if_present()
    p = argparse.ArgumentParser(
        prog="ada",
        description="ADA — local SQLite + Gemini harness",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    chat_p = sub.add_parser("chat", help="Terminal REPL")
    chat_p.add_argument(
        "--new-session",
        action="store_true",
        help="Create a new task / session_id instead of reusing the latest",
    )

    sub.add_parser("daemon", help="Poll pending tasks in SQLite")

    sub.add_parser(
        "ingest-rss",
        help="Fetch RSS/Atom feeds listed in knowledge_sources (kind=rss) into knowledge_items",
    )

    sub.add_parser(
        "ingest-keywords",
        help="Batch keyword volume via DataForSEO → ingest_raw (set ADA_KEYWORD_TERMS, DATAFORSEO_*)",
    )

    sub.add_parser(
        "ingest-gets",
        help="Public GETS tender index (ADA_GETS_POLL_URL) → ingest_raw + knowledge_items",
    )
    brand_p = sub.add_parser(
        "ingest-brand",
        help="Bounded site ingest for brand truth into knowledge_items",
    )
    brand_p.add_argument(
        "--site-url",
        default=None,
        metavar="URL",
        help="Brand site URL (fallback: ADA_BRAND_SITE_URL)",
    )
    brand_p.add_argument(
        "--max-urls",
        type=int,
        default=None,
        metavar="N",
        help="Bounded pages to ingest (default: ADA_BRAND_INGEST_MAX_URLS)",
    )
    brand_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and report without writing knowledge_items",
    )
    build_ingest_gsc_parser(sub)
    ks_p = sub.add_parser(
        "keyword-select",
        help="Pick top GSC keyword cluster for publish targeting",
    )
    ks_p.add_argument("--entity-id", type=int, required=True, metavar="ID")
    ks_p.add_argument("--site", required=True, metavar="SITE_URL")
    ks_p.add_argument("--start-date", required=True, metavar="YYYY-MM-DD")
    ks_p.add_argument("--end-date", required=True, metavar="YYYY-MM-DD")
    extract_graph_p = sub.add_parser(
        "extract-graph-lite",
        help="Run deterministic graph-lite extraction over recent knowledge_items",
    )
    extract_graph_p.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Max knowledge items to scan (default: ADA_GRAPH_LITE_EXTRACT_LIMIT)",
    )
    extract_graph_p.add_argument(
        "--token-cap",
        type=int,
        default=None,
        metavar="N",
        help="Per job token cap budget (default: ADA_GRAPH_LITE_TOKEN_CAP_PER_JOB)",
    )
    extract_graph_p.add_argument(
        "--source-id",
        type=int,
        default=None,
        metavar="ID",
        help="Optional knowledge_sources.id filter",
    )

    enrich_graph_p = sub.add_parser(
        "enrich-graph",
        help="Batch ENRICH for matrix subject entities (intent + policy system context)",
    )
    enrich_graph_p.add_argument(
        "--entity-id",
        type=int,
        action="append",
        default=None,
        metavar="ID",
        dest="entity_ids",
        help="Subject entity id (repeatable); union with matrix pool, capped by --limit / policy",
    )
    enrich_graph_p.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Max entities this run (default: policy batch_enrich_max_entities)",
    )

    add_feed_p = sub.add_parser(
        "add-rss-source",
        help="Register an RSS feed URL in knowledge_sources (then run ada ingest-rss)",
    )
    add_feed_p.add_argument(
        "url",
        help="Feed URL (e.g. https://www.rnz.co.nz/rss/business.xml)",
    )
    add_feed_p.add_argument(
        "--label",
        default=None,
        metavar="TEXT",
        help="Optional label stored with the source",
    )

    goal_p = sub.add_parser("goal", help="Enqueue and inspect background goal tasks")
    goal_p.add_argument(
        "goal_argv",
        nargs=argparse.REMAINDER,
        default=[],
        help=argparse.SUPPRESS,
    )

    dream_p = sub.add_parser(
        "dream",
        help="Run dream compression once (summarize DB → master/soul); manual trigger for testing",
    )
    dream_p.add_argument(
        "--session",
        type=int,
        default=None,
        help="Limit transcript to this task id (default: all recent messages)",
    )
    dream_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Call model but do not write master.md / soul.md",
    )
    dream_p.add_argument(
        "--max-messages",
        type=int,
        default=None,
        help="Transcript window size (default: ADA_DREAM_MAX_MESSAGES)",
    )

    triage_p = sub.add_parser(
        "triage",
        help=(
            "Triage knowledge_items: impact score + primary/secondary categories (Gemini JSON); "
            "default queue is rows with impact_score unset"
        ),
    )
    triage_p.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Max items to process (default: ADA_TRIAGE_BATCH_SIZE)",
    )
    triage_p.add_argument(
        "--backfill-categories",
        action="store_true",
        help=(
            "Process rows that have impact_score but missing triage categories "
            "(preserves existing impact_score; fills categories from the model)"
        ),
    )

    wf_p = sub.add_parser(
        "workflow",
        help="Phase 3 workflows (enqueue template, status, retry failed workflow)",
    )
    wf_sub = wf_p.add_subparsers(dest="wf_cmd", required=True)
    wf_e = wf_sub.add_parser(
        "enqueue",
        help="Create a pending goal task plus workflow steps from a template kind",
    )
    wf_e.add_argument(
        "--kind",
        required=True,
        metavar="KIND",
        help="Template kind (e.g. rss_fetch_then_graph_then_synth, publish_entity_v1, publish_keyword_v1)",
    )
    wf_e.add_argument(
        "--goal",
        required=True,
        metavar="TEXT",
        help="Goal text stored on the new tasks row",
    )
    wf_e.add_argument(
        "--params-json",
        default=None,
        metavar="JSON",
        help='Optional JSON object string, e.g. \'{"topic":"Macro summary"}\'',
    )
    wf_e.add_argument(
        "--idempotency-key",
        default=None,
        metavar="KEY",
        help="Optional; duplicate (kind, key) returns existing workflow without new task",
    )
    wf_s = wf_sub.add_parser(
        "status",
        help="Print workflow row and steps as JSON",
    )
    wf_s.add_argument("workflow_id", type=int, metavar="ID")

    wf_r = wf_sub.add_parser(
        "retry",
        help=(
            "Reset a failed workflow + parent goal task to pending so the daemon resumes "
            "from the first non-completed step. Use --duplicate-run for a full re-enqueue "
            "clone (respects ADA approval when enqueue requires it)."
        ),
    )
    wf_r.add_argument("workflow_id", type=int, metavar="ID")
    wf_r_mx = wf_r.add_mutually_exclusive_group(required=False)
    wf_r_mx.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned resets without writing",
    )
    wf_r_mx.add_argument(
        "--duplicate-run",
        action="store_true",
        help="Enqueue a new workflow with idempotency wf-retry-{id}-{utc_ts} (full re-run)",
    )
    wf_r.add_argument(
        "--reason",
        default="manual_retry",
        metavar="TEXT",
        help='Reason logged in action_log (default: "manual_retry")',
    )

    gf_p = sub.add_parser(
        "gate-failures",
        help="Read-only JSON: recent failed GATE steps + bucket counts (default: publish_entity_v1 only)",
    )
    gf_p.add_argument(
        "--limit",
        type=int,
        default=50,
        metavar="N",
        help="Max failed GATE rows to list (default: 50, capped at 500)",
    )
    gf_p.add_argument(
        "--all-kinds",
        action="store_true",
        help="Include failed GATE steps from workflows other than publish_entity_v1",
    )

    mx_p = sub.add_parser(
        "matrix-scan",
        help="Scan publishable entities + category edges, enqueue publish_entity_v1 (see ADA_MATRIX_*)",
    )
    mx_p.add_argument(
        "--dry-run",
        action="store_true",
        help="List candidates and intended enqueues without writing (may run without ADA_MATRIX_ENABLE)",
    )
    build_approval_parser(sub)

    args = p.parse_args()
    if args.cmd == "chat":
        settings = Settings.load()
        asyncio.run(run_chat(settings, new_session=args.new_session))
    elif args.cmd == "daemon":
        main_daemon()
    elif args.cmd == "ingest-rss":
        settings = Settings.load()
        raise SystemExit(asyncio.run(run_ingest_rss_cli(settings)))
    elif args.cmd == "ingest-keywords":
        settings = Settings.load()
        raise SystemExit(asyncio.run(run_ingest_keywords_cli(settings)))
    elif args.cmd == "ingest-gets":
        settings = Settings.load()
        raise SystemExit(asyncio.run(run_ingest_gets_cli(settings)))
    elif args.cmd == "ingest-brand":
        settings = Settings.load()
        raise SystemExit(
            asyncio.run(
                run_ingest_brand_cli(
                    settings,
                    site_url=args.site_url,
                    max_urls=args.max_urls,
                    dry_run=bool(args.dry_run),
                )
            )
        )
    elif args.cmd == "ingest-gsc":
        settings = Settings.load()
        raise SystemExit(asyncio.run(run_ingest_gsc_cli(settings, args)))
    elif args.cmd == "keyword-select":
        settings = Settings.load()
        raise SystemExit(
            asyncio.run(
                run_keyword_select_cli(
                    settings,
                    entity_id=args.entity_id,
                    site=args.site,
                    start_date=args.start_date,
                    end_date=args.end_date,
                )
            )
        )
    elif args.cmd == "extract-graph-lite":
        settings = Settings.load()
        limit = (
            args.limit
            if args.limit is not None
            else settings.graph_lite_extract_limit
        )
        token_cap = (
            args.token_cap
            if args.token_cap is not None
            else settings.graph_lite_token_cap_per_job
        )
        raise SystemExit(
            asyncio.run(
                run_extract_graph_lite_cli(
                    settings,
                    limit=limit,
                    token_cap=token_cap,
                    source_id=args.source_id,
                )
            )
        )
    elif args.cmd == "enrich-graph":
        settings = Settings.load()
        raise SystemExit(
            asyncio.run(
                run_enrich_graph_cli(
                    settings,
                    entity_ids=args.entity_ids,
                    limit=args.limit,
                )
            )
        )
    elif args.cmd == "add-rss-source":
        settings = Settings.load()
        raise SystemExit(
            asyncio.run(
                run_register_rss_source_cli(
                    settings,
                    url=args.url,
                    label=args.label,
                )
            )
        )
    elif args.cmd == "goal":
        rest = list(args.goal_argv)
        while rest and rest[0] == "--":
            rest.pop(0)
        raise SystemExit(asyncio.run(goal_async_main(rest)))
    elif args.cmd == "dream":
        settings = Settings.load()
        max_m = (
            args.max_messages
            if args.max_messages is not None
            else settings.dream_default_max_messages
        )
        asyncio.run(
            run_dream_cli(
                settings,
                session_id=args.session,
                dry_run=args.dry_run,
                max_messages=max_m,
            )
        )
    elif args.cmd == "triage":
        settings = Settings.load()
        limit = (
            args.limit
            if args.limit is not None
            else settings.triage_batch_size
        )
        stats, code = asyncio.run(
            run_triage_cli(
                settings,
                limit=limit,
                backfill_categories=bool(args.backfill_categories),
            )
        )
        print(
            "triage:"
            f" processed={stats.processed}"
            f" scored={stats.scored}"
            f" skipped={stats.skipped}"
            f" deep_dives_enqueued={stats.deep_dives_enqueued}"
        )
        raise SystemExit(code)
    elif args.cmd == "workflow":
        settings = Settings.load()
        if args.wf_cmd == "enqueue":
            raise SystemExit(
                asyncio.run(
                    run_workflow_enqueue_cli(
                        settings,
                        kind=args.kind,
                        goal=args.goal,
                        params_json=args.params_json,
                        idempotency_key=args.idempotency_key,
                    )
                )
            )
        if args.wf_cmd == "status":
            raise SystemExit(
                asyncio.run(
                    run_workflow_status_cli(
                        settings,
                        workflow_id=args.workflow_id,
                    )
                )
            )
        if args.wf_cmd == "retry":
            raise SystemExit(
                asyncio.run(
                    run_workflow_retry_cli(
                        settings,
                        workflow_id=args.workflow_id,
                        dry_run=bool(args.dry_run),
                        reason=args.reason,
                        duplicate_run=bool(args.duplicate_run),
                    )
                )
            )
        raise SystemExit(2)
    elif args.cmd == "gate-failures":
        settings = Settings.load()
        raise SystemExit(
            run_gate_failures_cli(
                settings,
                limit=int(args.limit),
                publish_entity_only=not bool(args.all_kinds),
            )
        )
    elif args.cmd == "matrix-scan":
        settings = Settings.load()
        raise SystemExit(
            asyncio.run(
                run_matrix_scan_cli(
                    settings,
                    dry_run=bool(getattr(args, "dry_run", False)),
                )
            )
        )
    elif args.cmd == "approval":
        settings = Settings.load()
        raise SystemExit(asyncio.run(run_approval_cli(settings, args)))
    else:
        p.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
