"""Smoke: markdown links in H8 ops docs resolve to repo paths."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DOC_PATHS = (
    _REPO_ROOT / "docs" / "ADA_CORE_OPS.md",
    _REPO_ROOT / "docs" / "HANDS_PHASES.md",
)
_LINK_RE = re.compile(r"\]\(([^)]+)\)")
_SKIP_PREFIXES = ("http://", "https://", "mailto:")
_SKIP_TARGETS = frozenset({"STREAMLIT_DAILY_USE.md"})


def _collect_relative_links(md_path: Path) -> list[tuple[str, str]]:
    text = md_path.read_text(encoding="utf-8")
    out: list[tuple[str, str]] = []
    for raw in _LINK_RE.findall(text):
        target = raw.strip()
        if not target or target.startswith("#"):
            continue
        if any(target.startswith(p) for p in _SKIP_PREFIXES):
            continue
        path_part = target.split("#", 1)[0].strip()
        if not path_part or path_part in _SKIP_TARGETS:
            continue
        out.append((str(md_path.relative_to(_REPO_ROOT)), path_part))
    return out


@pytest.mark.parametrize("doc_path", _DOC_PATHS, ids=lambda p: p.name)
def test_ops_doc_markdown_links_exist(doc_path: Path) -> None:
    missing: list[str] = []
    for source, link in _collect_relative_links(doc_path):
        resolved = (_REPO_ROOT / doc_path.parent / link).resolve()
        try:
            resolved.relative_to(_REPO_ROOT.resolve())
        except ValueError:
            missing.append(f"{source}: {link} (outside repo)")
            continue
        if not resolved.exists():
            missing.append(f"{source}: {link} -> {resolved}")
    assert not missing, "broken links:\n" + "\n".join(missing)
