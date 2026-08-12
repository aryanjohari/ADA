"""Cross-store search: FACTS + WORLDVIEW (+ optional runs grep)."""

from __future__ import annotations

from typing import Any

from ada.io.paths import DataPaths, require_ada_data
from ada.memory.facts import search_facts
from ada.memory.worldview import search_worldview


def search_memory(
    query: str,
    *,
    paths: DataPaths | None = None,
    include_runs: bool = False,
    max_hits: int = 20,
) -> dict[str, Any]:
    p = paths or require_ada_data()
    facts = search_facts(query, paths=p, max_hits=max_hits)
    worldview = search_worldview(query, paths=p, max_hits=max_hits)
    runs_hits: list[dict[str, Any]] = []
    if include_runs and p.runs.is_dir():
        q = (query or "").strip().lower()
        if q:
            for path in sorted(p.runs.rglob("*.jsonl")):
                if len(runs_hits) >= max_hits:
                    break
                try:
                    # Bound read — first 200KB per file.
                    text = path.read_text(encoding="utf-8", errors="replace")[:200_000]
                except OSError:
                    continue
                if q not in text.lower():
                    continue
                runs_hits.append({"path": str(path), "kind": "runs_grep"})
    return {
        "query": query,
        "facts": facts,
        "worldview": worldview,
        "runs": {"hits": runs_hits, "count": len(runs_hits)},
    }
