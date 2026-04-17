"""Serper search + Jina Reader / httpx fetch with caps, allowlist, and basic SSRF guards."""

from __future__ import annotations

import fnmatch
import html.parser
import ipaddress
import logging
import re
from typing import Any
from urllib.parse import urlparse

import httpx

log = logging.getLogger("ada.web")

SERPER_URL = "https://google.serper.dev/search"
_TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)


def _truncate(s: str, max_chars: int) -> tuple[str, bool]:
    if len(s) <= max_chars:
        return s, False
    return s[: max_chars - 1] + "…", True


class _HTMLStripper(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)

    def get_text(self) -> str:
        return " ".join(" ".join(self._chunks).split())


def html_to_text(html: str, max_chars: int) -> tuple[str, bool]:
    try:
        p = _HTMLStripper()
        p.feed(html)
        p.close()
        raw = p.get_text()
    except Exception:
        raw = _TAG_RE.sub(" ", html)
        raw = " ".join(raw.split())
    return _truncate(raw, max_chars)


def host_allowed(hostname: str, patterns: frozenset[str]) -> bool:
    if not patterns:
        return True
    h = hostname.lower().strip(".")
    for pat in patterns:
        pat = pat.strip().lower()
        if not pat:
            continue
        if fnmatch.fnmatch(h, pat):
            return True
    return False


def _is_private_or_reserved_ip(
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> bool:
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
    )


def validate_https_url(raw: str) -> tuple[str | None, str | None]:
    """
    Return (normalized_url, error_message).
    Require https; block obvious SSRF targets (localhost, literal private IPs).
    """
    raw = (raw or "").strip()
    if not raw:
        return None, "empty url"
    try:
        p = urlparse(raw)
    except Exception as e:
        return None, f"invalid url: {e}"
    if p.scheme.lower() != "https":
        return None, "only https URLs are allowed"
    if not p.netloc:
        return None, "missing host"
    host = p.hostname
    if host is None:
        return None, "missing hostname"
    hl = host.lower()
    if hl in ("localhost",) or hl.endswith(".localhost"):
        return None, "host not allowed"
    try:
        ip = ipaddress.ip_address(host)
        if _is_private_or_reserved_ip(ip):
            return None, "host not allowed"
    except ValueError:
        pass
    # Reconstruct stable form
    norm = raw.split("#", 1)[0].strip()
    return norm, None


def validate_url_with_allowlist(
    raw: str, host_patterns: frozenset[str]
) -> tuple[str | None, str | None]:
    url, err = validate_https_url(raw)
    if err or url is None:
        return None, err or "invalid url"
    p = urlparse(url)
    h = p.hostname or ""
    if not host_allowed(h, host_patterns):
        return None, "host not in allowlist"
    return url, None


async def serper_search(
    *,
    api_key: str,
    query: str,
    max_results: int,
    timeout_sec: float,
) -> dict[str, Any]:
    q = (query or "").strip()
    if not q:
        return {"error": "empty query"}
    n = max(1, min(max_results, 50))
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    body = {"q": q, "num": n}
    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            r = await client.post(SERPER_URL, headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError as e:
        log.warning("serper http error: %s", e)
        return {"error": f"serper http {e.response.status_code}"}
    except httpx.TimeoutException:
        log.warning("serper timeout")
        return {"error": "timeout"}
    except Exception as e:
        log.warning("serper error: %s", e)
        return {"error": str(e)}

    organic = data.get("organic")
    if not isinstance(organic, list):
        return {"error": "unexpected serper response", "provider": "serper"}
    results: list[dict[str, str]] = []
    for item in organic[:n]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "")
        link = str(item.get("link") or "")
        snippet = str(item.get("snippet") or "")
        results.append({"title": title, "url": link, "snippet": snippet})
    return {"results": results, "provider": "serper"}


async def _fetch_one_jina(
    client: httpx.AsyncClient,
    target_url: str,
    *,
    jina_base: str,
    jina_api_key: str | None,
    timeout_sec: float,
    max_bytes: int,
) -> tuple[str | None, bool]:
    """Returns (markdown_or_plain_text, truncated_raw_bytes)."""
    base = jina_base.rstrip("/") + "/"
    reader_url = base + target_url
    headers: dict[str, str] = {}
    if jina_api_key:
        headers["Authorization"] = f"Bearer {jina_api_key}"
    try:
        r = await client.get(
            reader_url,
            headers=headers or None,
            timeout=timeout_sec,
            follow_redirects=True,
        )
        r.raise_for_status()
        raw = r.content
        truncated = len(raw) > max_bytes
        if truncated:
            raw = raw[:max_bytes]
        text = raw.decode("utf-8", errors="replace")
        return text, truncated
    except Exception as e:
        log.warning("jina fetch error for %s: %s", target_url, e)
        raise


async def _fetch_one_httpx_direct(
    client: httpx.AsyncClient,
    target_url: str,
    *,
    timeout_sec: float,
    max_bytes: int,
) -> tuple[str, bool]:
    r = await client.get(
        target_url, timeout=timeout_sec, follow_redirects=True
    )
    r.raise_for_status()
    raw = r.content
    truncated = len(raw) > max_bytes
    if truncated:
        raw = raw[:max_bytes]
    html = raw.decode("utf-8", errors="replace")
    text, html_trunc = html_to_text(html, max_chars=max_bytes)
    return text, truncated or html_trunc


async def fetch_url_text_batch(
    urls: list[str],
    *,
    mode: str,
    max_urls: int,
    max_total_chars: int,
    max_bytes_per_response: int,
    timeout_sec: float,
    host_patterns: frozenset[str],
    jina_base_url: str,
    jina_api_key: str | None,
) -> dict[str, Any]:
    if not urls:
        return {"error": "no urls", "pages": []}
    pages: list[dict[str, Any]] = []
    remaining = max_total_chars
    capped_urls = urls[: max(1, max_urls)]
    async with httpx.AsyncClient() as client:
        for raw_u in capped_urls:
            if remaining <= 0:
                break
            url, verr = validate_url_with_allowlist(raw_u, host_patterns)
            if verr or url is None:
                pages.append(
                    {
                        "url": raw_u,
                        "text": "",
                        "truncated": False,
                        "error": verr or "invalid url",
                    }
                )
                continue
            per_byte_cap = max(4096, min(max_bytes_per_response, remaining * 4))
            try:
                if mode == "jina":
                    body, raw_trunc = await _fetch_one_jina(
                        client,
                        url,
                        jina_base=jina_base_url,
                        jina_api_key=jina_api_key,
                        timeout_sec=timeout_sec,
                        max_bytes=per_byte_cap,
                    )
                    text_out, trunc = _truncate(body or "", remaining)
                    pages.append(
                        {
                            "url": url,
                            "text": text_out,
                            "truncated": trunc or raw_trunc,
                            "error": None,
                        }
                    )
                else:
                    body, raw_trunc = await _fetch_one_httpx_direct(
                        client,
                        url,
                        timeout_sec=timeout_sec,
                        max_bytes=per_byte_cap,
                    )
                    text_out, trunc = _truncate(body, remaining)
                    pages.append(
                        {
                            "url": url,
                            "text": text_out,
                            "truncated": trunc or raw_trunc,
                            "error": None,
                        }
                    )
            except Exception as e:
                log.warning("fetch failed for %s: %s", url, e)
                pages.append(
                    {
                        "url": url,
                        "text": "",
                        "truncated": False,
                        "error": str(e),
                    }
                )
            last_text = pages[-1].get("text") or ""
            if isinstance(last_text, str) and not pages[-1].get("error"):
                remaining -= len(last_text)
    return {"pages": pages}
