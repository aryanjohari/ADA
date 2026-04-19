"""`python -m ada [chat|daemon|goal|dream|ingest-rss]`."""

from __future__ import annotations

import argparse
import asyncio
import sys

from ada.config import Settings, load_dotenv_if_present
from ada.cli import run_chat, run_dream_cli
from ada.goal_cli import async_main as goal_async_main
from ada.ingest.rss import run_ingest_rss_cli
from ada.main import main_daemon


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

    args = p.parse_args()
    if args.cmd == "chat":
        settings = Settings.load()
        asyncio.run(run_chat(settings, new_session=args.new_session))
    elif args.cmd == "daemon":
        main_daemon()
    elif args.cmd == "ingest-rss":
        settings = Settings.load()
        raise SystemExit(asyncio.run(run_ingest_rss_cli(settings)))
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
    else:
        p.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
