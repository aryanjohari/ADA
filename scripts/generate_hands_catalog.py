#!/usr/bin/env python3
"""Generate docs/hands_catalog.json from live code (read-only aggregation).

Usage:
  PYTHONPATH=src python3 scripts/generate_hands_catalog.py
  PYTHONPATH=src python3 scripts/generate_hands_catalog.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running from repo root without install
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from ada.config import _find_project_root  # noqa: E402
from ada.motor.manifest_sync import build_hands_catalog_dict  # noqa: E402

_DEFAULT_OUT = _find_project_root() / "docs" / "hands_catalog.json"


def _canonical_json(data: dict) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Hands catalog JSON")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if committed JSON differs from generator output",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUT,
        help=f"Output path (default: {_DEFAULT_OUT})",
    )
    args = parser.parse_args()
    catalog = build_hands_catalog_dict()
    text = _canonical_json(catalog)
    if args.check:
        if not args.output.is_file():
            print(f"missing {args.output}", file=sys.stderr)
            return 1
        committed = args.output.read_text(encoding="utf-8")
        if committed != text:
            print(
                f"{args.output} is stale; run scripts/generate_hands_catalog.py",
                file=sys.stderr,
            )
            return 1
        print(f"OK {args.output}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    caps = len(catalog.get("capabilities") or [])
    acts = len(catalog.get("actions") or [])
    pipes = len(catalog.get("pipelines") or [])
    pbs = len(catalog.get("playbooks") or [])
    print(f"wrote {args.output} ({caps} capabilities, {acts} actions, {pipes} pipelines, {pbs} playbooks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
