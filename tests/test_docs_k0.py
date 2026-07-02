"""K0 documentation deliverables exist and are non-empty."""

from __future__ import annotations

from pathlib import Path

import pytest

from ada.config import _find_project_root

K0_DOC_PATHS: tuple[str, ...] = (
    "docs/ADA_ENTITY_BUCKETS.md",
    "docs/TOOL_EXTENSION_GUIDE.md",
    "docs/MEMORY_OPS.md",
    "docs/buckets/FRIEND.md",
    "docs/buckets/HOUSE.md",
    "docs/buckets/LAB.md",
    "docs/use_cases/README.md",
    "docs/use_cases/_TEMPLATE.md",
    "docs/use_cases/INDEX.md",
)


@pytest.fixture
def docs_root() -> Path:
    return _find_project_root()


@pytest.mark.parametrize("rel_path", K0_DOC_PATHS)
def test_k0_doc_exists_and_non_empty(docs_root: Path, rel_path: str) -> None:
    path = docs_root / rel_path
    assert path.is_file(), f"missing K0 doc: {path}"
    assert path.read_text(encoding="utf-8").strip(), f"empty K0 doc: {path}"


def test_use_cases_index_has_table_header(docs_root: Path) -> None:
    index = docs_root / "docs/use_cases/INDEX.md"
    text = index.read_text(encoding="utf-8")
    assert "| ID | Bucket |" in text
    assert "| Capability | Status |" in text
