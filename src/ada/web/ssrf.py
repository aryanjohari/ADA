"""SSRF-safe URL validation for web egress (M07).

Resolve DNS → reject private/link-local/metadata → pin redirect revalidation.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


ALLOWED_PORTS = frozenset({80, 443})
MAX_REDIRECTS = 5


class SsrfError(ValueError):
    """URL rejected for SSRF / scheme / port policy."""


@dataclass(frozen=True)
class ResolvedTarget:
    url: str
    scheme: str
    host: str
    port: int
    ip: str
    path: str


def _default_port(scheme: str) -> int:
    return 443 if scheme == "https" else 80


def parse_url_strict(url: str, *, allow_http: bool = False) -> tuple[str, str, int, str]:
    """Return (scheme, host, port, path). Raises SsrfError on bad scheme/creds."""
    raw = (url or "").strip()
    if not raw:
        raise SsrfError("empty url")
    parsed = urlparse(raw)
    scheme = (parsed.scheme or "").lower()
    if scheme == "https":
        pass
    elif scheme == "http":
        if not allow_http:
            raise SsrfError("http only allowed for already-allowlisted hosts")
    else:
        raise SsrfError(f"scheme not allowed: {scheme or '(none)'}")
    if parsed.username or parsed.password:
        raise SsrfError("credentials in URL not allowed")
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise SsrfError("missing host")
    port = parsed.port or _default_port(scheme)
    if port not in ALLOWED_PORTS:
        raise SsrfError(f"port not allowed: {port}")
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    return scheme, host, port, path


def is_blocked_ip(ip_str: str) -> bool:
    """True if address is private, loopback, link-local, CGNAT, or metadata-class."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
        return True
    if ip.is_reserved or ip.is_unspecified:
        return True
    # CGNAT 100.64.0.0/10
    if isinstance(ip, ipaddress.IPv4Address):
        if ip in ipaddress.ip_network("100.64.0.0/10"):
            return True
        if ip == ipaddress.ip_address("169.254.169.254"):
            return True
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            return is_blocked_ip(str(ip.ipv4_mapped))
    return False


def resolve_host(host: str) -> list[str]:
    """Resolve host to IP strings (IPv4 preferred order)."""
    # Literal IP in host
    try:
        ipaddress.ip_address(host)
        return [host]
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise SsrfError(f"DNS resolve failed for {host}: {exc}") from exc
    ips: list[str] = []
    for info in infos:
        addr = info[4][0]
        if addr not in ips:
            ips.append(addr)
    if not ips:
        raise SsrfError(f"no addresses for {host}")
    return ips


def validate_resolved(host: str, ips: list[str] | None = None) -> str:
    """Resolve (if needed) and ensure at least one non-blocked IP; return first safe IP."""
    addrs = ips if ips is not None else resolve_host(host)
    safe: list[str] = []
    for ip in addrs:
        if is_blocked_ip(ip):
            continue
        safe.append(ip)
    if not safe:
        raise SsrfError(f"SSRF: host {host} resolves only to blocked addresses {addrs}")
    return safe[0]


def check_url(
    url: str,
    *,
    allow_http: bool = False,
    resolve: bool = True,
) -> ResolvedTarget:
    """Parse + optional DNS/SSRF check. Does not open a socket connection."""
    scheme, host, port, path = parse_url_strict(url, allow_http=allow_http)
    ip = ""
    if resolve:
        ip = validate_resolved(host)
    rebuilt = f"{scheme}://{host}"
    if (scheme == "https" and port != 443) or (scheme == "http" and port != 80):
        rebuilt = f"{scheme}://{host}:{port}"
    rebuilt = rebuilt + path
    return ResolvedTarget(
        url=rebuilt if rebuilt.endswith(path) else f"{scheme}://{host}:{port}{path}",
        scheme=scheme,
        host=host,
        port=port,
        ip=ip,
        path=path,
    )


def assert_redirect_safe(
    next_url: str,
    *,
    allowlisted_hosts: set[str],
    pasted_hosts: set[str] | None = None,
    allow_http_hosts: set[str] | None = None,
) -> ResolvedTarget:
    """Re-validate a redirect hop: SSRF + final host must be allowlisted or pasted."""
    pasted = pasted_hosts or set()
    http_ok = allow_http_hosts or set()
    # Peek host before scheme policy
    peek = urlparse(next_url.strip())
    host = (peek.hostname or "").lower().rstrip(".")
    allow_http = host in http_ok or host in allowlisted_hosts
    target = check_url(next_url, allow_http=allow_http, resolve=True)
    if target.host not in allowlisted_hosts and target.host not in pasted:
        raise SsrfError(
            f"redirect host not allowlisted: {target.host}"
        )
    return target


def outcome_denied(reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "outcome": "error",
        "error": reason,
        "denied_reason": reason,
    }
