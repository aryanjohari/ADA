"""Blog slug from the question. Not artifacts._slugify."""

from __future__ import annotations

import re

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
MAX_SLUG = 80


class SlugError(ValueError):
    """The question does not yield one usable blog path segment."""


def require_blog_segment(slug: str) -> str:
    """One path segment: non-empty, not ``.`` or ``..``, no slash, no leading dot, ≤80."""
    if not isinstance(slug, str):
        raise SlugError("slug is not one path segment")
    if (
        not slug
        or slug in {".", ".."}
        or "/" in slug
        or "\\" in slug
        or slug.startswith(".")
    ):
        raise SlugError("slug is not one path segment")
    if len(slug) > MAX_SLUG:
        raise SlugError(
            f"refusing slug of length {len(slug)}; the question was not shortened"
        )
    return slug


def blog_slug(question: str) -> str:
    """Lowercase, collapse non-alphanumerics to one hyphen, strip end hyphens.

    An empty result or a result longer than 80 characters is a refusal.
    This function does not truncate and does not mint a ``-2`` suffix.
    """
    raw = (question or "").strip().lower()
    slug = _NON_ALNUM.sub("-", raw).strip("-")
    return require_blog_segment(slug)
