#!/usr/bin/env python3
"""Dry-run profile merge: report two ADA profile dirs (no writes)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description="Compare two profile data dirs (dry-run).")
    p.add_argument("profile_a", type=Path, help="Path to profile A data dir (contains state.db)")
    p.add_argument("profile_b", type=Path, help="Path to profile B data dir")
    args = p.parse_args()
    a = args.profile_a.resolve()
    b = args.profile_b.resolve()
    dba = a / "state.db"
    dbb = b / "state.db"
    report = {
        "profile_a": str(a),
        "profile_b": str(b),
        "state_db_a_exists": dba.is_file(),
        "state_db_b_exists": dbb.is_file(),
        "note": (
            "Full merge requires copying missions/tasks/workflows and reconciling "
            "missions.id — not performed here. Use this script to verify paths before a manual merge."
        ),
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
