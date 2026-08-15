"""Allowlisted HTTPS GET + extract + cite/TTL (M07 + M10).

httpx client with redirect SSRF revalidation. Observations never include HTML.
Disk may store full extract + chunks; Gemini sees OBSERVATION_CHAR_CAP only.
"""

from __future__ import annotations

import hashlib
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from ada.body.vitals import utc_now_iso
from ada.io.paths import DataPaths, require_ada_data
from ada.web import allowlist as allowlist_mod
from ada.web import cites as cites_mod
from ada.web.chunk import STORE_EXTRACT_CHAR_CAP, chunk_text
from ada.web.classify import classify_fetch
from ada.web.extract import extract_main
from ada.web.ssrf import (
    MAX_REDIRECTS,
    SsrfError,
    assert_redirect_safe,
    check_url,
)

USER_AGENT = "ADA-User"
MAX_BODY_BYTES = 5 * 1024 * 1024  # 5 MiB
OBSERVATION_CHAR_CAP = 12_000
REQUEST_TIMEOUT = 15.0


def _content_hash(body: bytes) -> str:
    return "sha256:" + hashlib.sha256(body).hexdigest()


def _cap_excerpts(text: str, *, cap: int = OBSERVATION_CHAR_CAP) -> tuple[list[str], bool]:
    """Observation head only — not the library document (M10 F3)."""
    text = (text or "").strip()
    if not text:
        return [], False
    if len(text) <= cap:
        return [text], False
    return [text[:cap]], True


def _robots_allowed(url: str, *, ignore_robots: bool) -> tuple[bool, str]:
    if ignore_robots:
        return True, "ignored_user_intent"
    # Thin robots: try /robots.txt Disallow for path; fail-open on fetch error
    # for interactive; campaigns should still set ignore_robots=false.
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        with httpx.Client(timeout=5.0, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            resp = client.get(robots_url)
            if resp.status_code != 200:
                return True, "honored"
            path = parsed.path or "/"
            ua_block = False
            applies = False
            for line in resp.text.splitlines():
                low = line.strip().lower()
                if low.startswith("user-agent:"):
                    agent = low.split(":", 1)[1].strip()
                    applies = agent in ("*", "ada-user")
                elif applies and low.startswith("disallow:"):
                    rule = line.split(":", 1)[1].strip()
                    if rule and path.startswith(rule):
                        ua_block = True
            if ua_block:
                return False, "honored"
            return True, "honored"
    except Exception:  # noqa: BLE001
        return True, "honored"


def _manual_get(
    url: str,
    *,
    allowlisted: set[str],
    pasted: set[str],
    headers: dict[str, str],
    allow_http_hosts: set[str],
) -> tuple[httpx.Response, str, list[str]]:
    """GET with manual redirects; re-validate each hop for SSRF/allowlist."""
    current = url
    hop_urls = [current]
    with httpx.Client(
        timeout=REQUEST_TIMEOUT,
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT, **headers},
    ) as client:
        for _ in range(MAX_REDIRECTS + 1):
            target = check_url(
                current,
                allow_http=(
                    urlparse(current).hostname or ""
                ).lower().rstrip(".")
                in allow_http_hosts
                or (urlparse(current).hostname or "").lower().rstrip(".") in allowlisted,
                resolve=True,
            )
            # Build request URL (prefer original form for Host header correctness)
            resp = client.get(current)
            if resp.status_code in (301, 302, 303, 307, 308):
                loc = resp.headers.get("location")
                if not loc:
                    raise SsrfError("redirect without Location")
                next_url = urljoin(str(resp.url), loc)
                assert_redirect_safe(
                    next_url,
                    allowlisted_hosts=allowlisted,
                    pasted_hosts=pasted,
                    allow_http_hosts=allow_http_hosts,
                )
                current = next_url
                hop_urls.append(current)
                continue
            return resp, str(resp.url), hop_urls
    raise SsrfError(f"too many redirects (>{MAX_REDIRECTS})")


def web_fetch(
    url: str,
    *,
    force: bool = False,
    user_pasted: bool = False,
    pasted_text: str | None = None,
    ignore_robots: bool = False,
    confirm_host: bool = False,
    receipt_id: str | None = None,
    question: str | None = None,  # noqa: ARG001 — reserved for excerpt bias
    paths: DataPaths | None = None,
    http_get=None,  # test seam
    campaign_id: str | None = None,
    watch_id: str | None = None,
) -> dict[str, Any]:
    """Fetch URL → extract → durable cite. Returns observation-shaped data."""
    p = paths or require_ada_data()
    p.ensure_cite_dirs()
    rid = receipt_id or ""

    policy = allowlist_mod.check_host_access(
        url,
        paths=p,
        user_pasted=user_pasted,
        pasted_text=pasted_text,
        confirm_host=confirm_host,
    )
    if policy.get("needs_confirm"):
        return policy
    if not policy.get("ok"):
        return policy

    host = policy["host"]
    pasted_set: set[str] = set()
    if policy.get("pasted"):
        pasted_set.add(host)
    pasted_set |= allowlist_mod.pasted_hosts_from_text(pasted_text)
    allowlisted = allowlist_mod.allowlist_hosts(p)
    # Pasted hosts are treated as temporarily allowed for redirect checks
    effective_allow = set(allowlisted) | pasted_set

    # Scheme: https preferred; http only if allowlisted
    try:
        # When http_get is injected (tests), skip live DNS — SSRF still unit-tested.
        check_url(
            url,
            allow_http=(host in allowlisted),
            resolve=http_get is None,
        )
    except SsrfError as exc:
        return {
            "ok": False,
            "outcome": "error",
            "error": str(exc),
            "denied_reason": str(exc),
        }

    ttl = allowlist_mod.ttl_for_host(host, p)
    existing = cites_mod.newest_cite_for_url(url, paths=p)

    if existing and not force and cites_mod.is_fresh(existing, ttl_seconds=ttl):
        # M11-B: stamp campaign/watch on TTL hit when watch wake provides ids.
        if (campaign_id and not existing.get("campaign_id")) or (
            watch_id and not existing.get("watch_id")
        ):
            updated = cites_mod.update_cite_fetched_at(
                str(existing["id"]),
                fetched_at=existing.get("fetched_at") or utc_now_iso(),
                etag=existing.get("etag"),
                last_modified=existing.get("last_modified"),
                status=existing.get("status"),
                receipt_id=rid or existing.get("receipt_id"),
                campaign_id=campaign_id,
                watch_id=watch_id,
                paths=p,
            )
            cite = updated["cite"]
            obs = cites_mod.observation_from_cite(
                cite, cache="hit", receipt_id=rid or None
            )
            return {"ok": True, "outcome": "ok", **obs}
        obs = cites_mod.observation_from_cite(existing, cache="hit", receipt_id=rid or None)
        return {"ok": True, "outcome": "ok", **obs}

    robots_ok, robots_flag = _robots_allowed(url, ignore_robots=ignore_robots)
    if not robots_ok:
        return {
            "ok": False,
            "outcome": "error",
            "error": "robots.txt disallows this path",
            "denied_reason": "robots.txt disallows this path",
            "robots": robots_flag,
        }

    headers: dict[str, str] = {}
    if existing and not force and existing.get("etag"):
        headers["If-None-Match"] = str(existing["etag"])

    try:
        if http_get is not None:
            resp, final_url, _hops = http_get(
                url,
                headers=headers,
                allowlisted=effective_allow,
                pasted=pasted_set,
            )
        else:
            resp, final_url, _hops = _manual_get(
                url,
                allowlisted=effective_allow,
                pasted=pasted_set,
                headers=headers,
                allow_http_hosts=allowlisted,
            )
    except SsrfError as exc:
        return {
            "ok": False,
            "outcome": "error",
            "error": str(exc),
            "denied_reason": str(exc),
        }
    except httpx.HTTPError as exc:
        return {
            "ok": False,
            "outcome": "error",
            "error": f"http error: {exc}",
            "denied_reason": f"http error: {exc}",
        }

    etag = resp.headers.get("etag")
    last_mod = resp.headers.get("last-modified")

    if resp.status_code == 304 and existing:
        updated = cites_mod.update_cite_fetched_at(
            str(existing["id"]),
            fetched_at=utc_now_iso(),
            etag=etag or existing.get("etag"),
            last_modified=last_mod or existing.get("last_modified"),
            status=304,
            receipt_id=rid or existing.get("receipt_id"),
            campaign_id=campaign_id,
            watch_id=watch_id,
            paths=p,
        )
        cite = updated["cite"]
        obs = cites_mod.observation_from_cite(cite, cache="revalidate", receipt_id=rid or None)
        return {"ok": True, "outcome": "ok", **obs}

    if resp.status_code != 200:
        return {
            "ok": False,
            "outcome": "error",
            "error": f"HTTP {resp.status_code}",
            "denied_reason": f"HTTP {resp.status_code}",
            "status": resp.status_code,
            "final_url": final_url,
        }

    body = resp.content
    if len(body) > MAX_BODY_BYTES:
        body = body[:MAX_BODY_BYTES]
        truncated_download = True
    else:
        truncated_download = False

    content_hash = _content_hash(body)

    if existing and existing.get("content_hash") == content_hash:
        updated = cites_mod.update_cite_fetched_at(
            str(existing["id"]),
            fetched_at=utc_now_iso(),
            etag=etag,
            last_modified=last_mod,
            status=200,
            receipt_id=rid or existing.get("receipt_id"),
            campaign_id=campaign_id,
            watch_id=watch_id,
            paths=p,
        )
        cite = updated["cite"]
        obs = cites_mod.observation_from_cite(cite, cache="same_hash", receipt_id=rid or None)
        return {"ok": True, "outcome": "ok", **obs}

    # Decode for extract
    charset = resp.charset_encoding or "utf-8"
    try:
        html = body.decode(charset, errors="replace")
    except Exception:  # noqa: BLE001
        html = body.decode("utf-8", errors="replace")

    extracted = extract_main(html, url=final_url)
    full_text = (extracted.get("text") or "").strip()
    if len(full_text) > STORE_EXTRACT_CHAR_CAP:
        full_text = full_text[:STORE_EXTRACT_CHAR_CAP]

    classified = classify_fetch(
        url=final_url or url,
        raw_body=html,
        extracted_text=full_text,
        truncated_download=truncated_download,
    )
    excerpts, trunc_obs = _cap_excerpts(full_text, cap=OBSERVATION_CHAR_CAP)
    # truncated = observation (or download) was cut — not "library complete" (M10 F3).
    truncated = truncated_download or trunc_obs
    chunks = chunk_text(full_text) if full_text else []

    cite = cites_mod.write_cite(
        url=url,
        final_url=final_url,
        status=200,
        etag=etag,
        last_modified=last_mod,
        content_hash=content_hash,
        title=extracted.get("title"),
        excerpts=excerpts,
        truncated=truncated,
        robots=robots_flag,
        allowlist_host=host,
        receipt_id=rid,
        paths=p,
        save_raw_html=html if len(html) <= MAX_BODY_BYTES else None,
        kind=classified.kind,
        extract_status=classified.extract_status,
        extract_ok=classified.extract_ok,
        extract_source="html",
        chunks=chunks,
        full_extract=full_text or None,
        campaign_id=campaign_id,
        watch_id=watch_id,
    )
    obs = cites_mod.observation_from_cite(cite, cache="miss", receipt_id=rid or None)
    return {"ok": True, "outcome": "ok", **obs}


def web_cite_get(cite_id: str, *, paths: DataPaths | None = None) -> dict[str, Any]:
    got = cites_mod.get_cite(cite_id, paths=paths)
    if not got.get("ok"):
        return got
    cite = got["cite"]
    obs = cites_mod.observation_from_cite(cite, cache="disk")
    return {"ok": True, "outcome": "ok", **obs}


def web_cite_search(
    query: str,
    *,
    max_hits: int = 10,
    paths: DataPaths | None = None,
    include_non_knowledge: bool = False,
) -> dict[str, Any]:
    """Local cite-index search — library discovery before network (M07/M10)."""
    return cites_mod.search_cites(
        query,
        max_hits=max_hits,
        paths=paths,
        include_non_knowledge=include_non_knowledge,
    )
