"""DB-only graph sufficiency check before ENRICH live web (Serper / Jina)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ada.config import Settings
from ada.query_engine import QueryEngine


@dataclass(frozen=True)
class EnrichGraphSufficiency:
    """Result of evaluating configured thresholds (no web I/O)."""

    sufficient: bool
    reason: str
    metrics: dict[str, Any]
    # Effective thresholds used (after inherit / off semantics)
    threshold_unique_local_facts: int
    threshold_outgoing_edges: int
    mode: str


def _effective_min_unique_facts(settings: Settings) -> int:
    """
    None => inherit ADA_PUBLISH_MIN_UNIQUE_FACTS (GATE alignment).
    0 => criterion disabled. >0 => explicit floor.
    """
    raw = settings.enrich_suff_min_unique_facts
    if raw is None:
        return int(settings.ada_publish_min_unique_facts)
    return max(0, int(raw))


async def evaluate_enrich_graph_sufficiency(
    qe: QueryEngine, entity_id: int, settings: Settings
) -> EnrichGraphSufficiency:
    t_facts = _effective_min_unique_facts(settings)
    t_edges = max(0, int(settings.enrich_suff_min_outgoing_edges))
    n_facts = await qe.count_unique_local_facts(entity_id)
    n_edges = await qe.count_outgoing_active_edges(entity_id)
    mode = (settings.enrich_suff_mode or "all").strip().lower()
    if mode not in ("all", "any"):
        mode = "all"

    checks: list[tuple[str, bool]] = []
    if t_facts > 0:
        checks.append(("unique_local_facts", n_facts >= t_facts))
    if t_edges > 0:
        checks.append(("outgoing_active_edges", n_edges >= t_edges))

    if not checks:
        return EnrichGraphSufficiency(
            sufficient=False,
            reason="no_thresholds_configured",
            metrics={
                "unique_local_facts": n_facts,
                "outgoing_active_edges": n_edges,
            },
            threshold_unique_local_facts=t_facts,
            threshold_outgoing_edges=t_edges,
            mode=mode,
        )

    vals = [b for _, b in checks]
    if mode == "any":
        ok = any(vals)
    else:
        ok = all(vals)
    if ok:
        reason = "thresholds_met"
    elif mode == "any":
        reason = "no_threshold_matched"
    else:
        reason = "not_all_thresholds_met"
    return EnrichGraphSufficiency(
        sufficient=ok,
        reason=reason,
        metrics={
            "unique_local_facts": n_facts,
            "outgoing_active_edges": n_edges,
        },
        threshold_unique_local_facts=t_facts,
        threshold_outgoing_edges=t_edges,
        mode=mode,
    )
