"""Shared helpers for deterministic ingest (allowlists, URL checks)."""

from __future__ import annotations

from urllib.parse import urlparse


def url_host_in_allowlist(url: str, host_allowlist: frozenset[str]) -> bool:
    """
    If host_allowlist is empty, any http(s) URL with a hostname is allowed.
    Otherwise hostname must match one entry (case-insensitive).
    """
    raw = (url or "").strip()
    if not raw:
        return False
    p = urlparse(raw)
    if p.scheme not in ("http", "https"):
        return False
    host = (p.hostname or "").lower()
    if not host:
        return False
    if not host_allowlist:
        return True
    allowed = {h.strip().lower() for h in host_allowlist if h.strip()}
    return host in allowed


def assert_gov_api_url_allowed(url: str, gov_api_host_allowlist: frozenset[str]) -> None:
    """Raise ValueError if URL host is not in ADA_GOV_API_HOST_ALLOWLIST (when non-empty)."""
    if not gov_api_host_allowlist:
        raise ValueError(
            "ADA_GOV_API_HOST_ALLOWLIST is empty; set allowed hosts for DataForSEO/GETS ingest"
        )
    if not url_host_in_allowlist(url, gov_api_host_allowlist):
        p = urlparse(url)
        host = (p.hostname or "").lower() or "?"
        raise ValueError(f"host {host!r} not in ADA_GOV_API_HOST_ALLOWLIST")
