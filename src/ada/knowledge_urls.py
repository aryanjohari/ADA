"""Validate URLs for knowledge_sources (RSS feeds, etc.)."""

from __future__ import annotations

from urllib.parse import urlparse


def validate_knowledge_feed_url(
    url: str,
    *,
    host_allowlist: frozenset[str],
    max_len: int = 2048,
) -> None:
    """
    Reject obviously unsafe URLs. If host_allowlist is non-empty, hostname must match
    one entry (case-insensitive, exact host only).
    """
    raw = url.strip()
    if not raw:
        raise ValueError("URL is empty")
    if len(raw) > max_len:
        raise ValueError("URL too long")
    p = urlparse(raw)
    if p.scheme not in ("http", "https"):
        raise ValueError("URL scheme must be http or https")
    host = (p.hostname or "").lower()
    if not host:
        raise ValueError("URL must include a hostname")
    if host_allowlist:
        allowed = {h.strip().lower() for h in host_allowlist if h.strip()}
        if host not in allowed:
            raise ValueError(f"host {host!r} not in knowledge feed allowlist")
