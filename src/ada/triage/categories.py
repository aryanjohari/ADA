"""Fixed triage taxonomy for knowledge_items routing (coarse codes only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

TRIAGE_CATEGORY_CODES: frozenset[str] = frozenset(
    {
        "policy_regulation",
        "government_fiscal",
        "markets_macro",
        "data_surveys_stats",
        "trade_industry",
        "sector_business",
        "infrastructure_projects",
        "climate_energy",
        "labour_workforce",
        "company_corporate",
        "consumer_retail",
        "international_spillover",
    }
)


@dataclass(frozen=True)
class TriageParseResult:
    impact_score: int
    primary_category: str
    secondary_categories: tuple[str, ...]


def parse_triage_response(data: dict[str, Any]) -> TriageParseResult | None:
    """Validate model JSON: impact_score 1–10, primary + 0–2 secondaries from enum."""
    v = data.get("impact_score")
    score: int | None
    if isinstance(v, bool):
        score = None
    elif isinstance(v, int):
        score = v if 1 <= v <= 10 else None
    elif isinstance(v, float) and v.is_integer():
        iv = int(v)
        score = iv if 1 <= iv <= 10 else None
    elif isinstance(v, str):
        try:
            iv = int(v.strip())
            score = iv if 1 <= iv <= 10 else None
        except ValueError:
            score = None
    else:
        score = None
    if score is None:
        return None

    raw_primary = data.get("primary_category")
    if not isinstance(raw_primary, str) or not raw_primary.strip():
        return None
    primary = raw_primary.strip()
    if primary not in TRIAGE_CATEGORY_CODES:
        return None

    raw_secs = data.get("secondary_categories")
    if raw_secs is None:
        secondaries: list[str] = []
    elif isinstance(raw_secs, list):
        secondaries = []
        for x in raw_secs:
            if not isinstance(x, str) or not x.strip():
                return None
            code = x.strip()
            if code not in TRIAGE_CATEGORY_CODES:
                return None
            secondaries.append(code)
    else:
        return None

    if len(secondaries) > 2:
        return None
    if len(set(secondaries)) != len(secondaries):
        return None
    if primary in secondaries:
        return None

    return TriageParseResult(
        impact_score=score,
        primary_category=primary,
        secondary_categories=tuple(secondaries),
    )
