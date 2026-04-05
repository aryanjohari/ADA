"""`python -m ada [chat|daemon]`."""

from __future__ import annotations

import argparse
import asyncio
import sys

from ada.config import Settings, load_dotenv_if_present
from ada.cli import run_chat
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

    args = p.parse_args()
    if args.cmd == "chat":
        settings = Settings.load()
        asyncio.run(run_chat(settings, new_session=args.new_session))
    elif args.cmd == "daemon":
        main_daemon()
    else:
        p.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
