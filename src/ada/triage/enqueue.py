"""Category-aware rules for automatic deep-dive (goal) enqueue from triage."""

from __future__ import annotations


def tier1_macro_eligible(
    *,
    impact_score: int,
    primary_category: str,
    trigger_min: int,
) -> bool:
    """
    Tier1 (macro) deep-dive: high score + primary suited to macro/hard-signal synthesis.

    Excludes sector_business (qualitative lead lane). consumer_retail needs 9+ for Tier1.
    """
    if impact_score < max(8, trigger_min):
        return False
    if primary_category == "sector_business":
        return False
    if primary_category == "consumer_retail" and impact_score < 9:
        return False
    return True


def tier2_lead_eligible(
    *,
    impact_score: int,
    trigger_min: int,
) -> bool:
    """Tier2 (lead) deep-dive: scores 6–7 only (qualitative lane with daily cap)."""
    if impact_score < max(6, trigger_min):
        return False
    return impact_score <= 7
