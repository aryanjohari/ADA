"""Closed enum of subject (non-category) graph entity `type` values for publishing."""

from __future__ import annotations

# Matrix scan and PageProfileRegistry use the lowercased set.
PUBLISHABLE_SUBJECT_TYPES: frozenset[str] = frozenset(
    {"service", "regulation", "organization", "jurisdiction"}
)
