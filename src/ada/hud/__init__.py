"""M03 control-plane HUD — localhost ASGI + Tailscale Serve (no Funnel)."""

from __future__ import annotations

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787

__all__ = ["DEFAULT_HOST", "DEFAULT_PORT", "assert_loopback_host"]


def assert_loopback_host(host: str) -> str:
    """Return a normalized loopback bind address or raise ValueError.

    POLICY (M01/M03): HUD must not bind 0.0.0.0 / LAN interfaces.
    """
    h = (host or "").strip().lower()
    if h in ("127.0.0.1", "localhost"):
        return "127.0.0.1"
    if h in ("::1", "[::1]"):
        return "::1"
    raise ValueError(
        f"HUD refuses non-loopback bind host {host!r}; "
        "use 127.0.0.1 and Tailscale Serve (Funnel NO)"
    )
