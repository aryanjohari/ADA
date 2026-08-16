"""Birth pack — repo seeds → ada-data if missing (M16 Phase 0).

Never overwrite operator data. Never put private biography in git.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from ada.io.paths import BodyFault, DataPaths, ada_data_mounted, require_ada_data

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SEEDS_ROOT = _REPO_ROOT / "seeds"

# (repo-relative under seeds/, destination under ada-data root)
_SEED_MAP: tuple[tuple[str, str], ...] = (
    ("syllabus/SELF.md", "syllabus/SELF.md"),
    ("syllabus/OPERATOR.md", "syllabus/OPERATOR.md"),
    ("facts/people/_template.yaml", "memory/facts/people/_template.yaml"),
)


def seeds_root() -> Path:
    return _SEEDS_ROOT


def apply_birth_pack(
    paths: DataPaths | None = None,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Copy seed templates into ada-data when missing.

    ``force=True`` is for tests only — production birth never overwrites.
    """
    p = paths or require_ada_data()
    if not ada_data_mounted(p.root):
        raise BodyFault(
            f"ada-data not mounted or missing at {p.root}; refusing birth pack"
        )
    if not _SEEDS_ROOT.is_dir():
        return {
            "ok": False,
            "outcome": "error",
            "error": f"seeds root missing at {_SEEDS_ROOT}",
            "applied": [],
            "skipped": [],
        }

    applied: list[str] = []
    skipped: list[str] = []
    missing_src: list[str] = []

    for src_rel, dst_rel in _SEED_MAP:
        src = _SEEDS_ROOT / src_rel
        dst = p.root / dst_rel
        if not src.is_file():
            missing_src.append(src_rel)
            continue
        if dst.is_file() and not force:
            skipped.append(dst_rel)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        applied.append(dst_rel)

    return {
        "ok": True,
        "outcome": "ok",
        "applied": applied,
        "skipped": skipped,
        "missing_src": missing_src,
        "seeds_root": str(_SEEDS_ROOT),
    }


def syllabus_self_path(paths: DataPaths | None = None) -> Path | None:
    """Prefer ada-data SELF.md; fall back to repo seed for boot when missing."""
    try:
        p = paths or require_ada_data()
        local = p.syllabus_self
        if local.is_file():
            return local
    except BodyFault:
        pass
    seed = _SEEDS_ROOT / "syllabus" / "SELF.md"
    return seed if seed.is_file() else None


def load_syllabus_heads(
    *,
    paths: DataPaths | None = None,
    max_chars: int = 1200,
) -> str:
    """Budgeted SELF.md heads for charter boot (F3)."""
    path = syllabus_self_path(paths)
    if path is None or not path.is_file():
        return "Syllabus (SELF): (missing — run birth pack)."
    text = path.read_text(encoding="utf-8").strip()
    # Prefer first meaningful sections; truncate hard for boot budget.
    if len(text) > max_chars:
        text = text[: max_chars - 20].rstrip() + "\n…(truncated)"
    return "Syllabus (SELF — capability heads):\n" + text
