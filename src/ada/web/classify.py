"""Deterministic fetch-body classification (M10) — no LLM.

Labels empty / WAF-JS shells / feed XML vs real HTML (and abs-grade pages).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

# Challenge / bot-wall markers seen on metal (Beehive Incapsula) + common cousins.
_JS_SHELL_MARKERS = (
    "_Incapsula_Resource",
    "Incapsula",
    "cf-browser-verification",
    "cf-challenge",
    "challenge-platform",
    "Just a moment",
    "AkamaiGHost",
    "Attention Required! | Cloudflare",
    "enablejavascript",
    "Checking your browser",
)

_FEED_ROOT_RE = re.compile(
    r"<(?:rss|feed|rdf:RDF)\b",
    re.IGNORECASE,
)
_XML_DECL_RE = re.compile(r"^\s*<\?xml\b", re.IGNORECASE)

# Tiny body with challenge markers — typical Imperva shell (~212 B on metal).
_SHELL_BODY_MAX = 4096
_EMPTY_EXTRACT_MAX = 40


@dataclass(frozen=True)
class ExtractClass:
    kind: str
    extract_status: str
    extract_ok: bool
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "extract_status": self.extract_status,
            "extract_ok": self.extract_ok,
            "reason": self.reason,
        }


def _looks_like_feed_xml(raw: str) -> bool:
    head = (raw or "")[:8000]
    if _FEED_ROOT_RE.search(head):
        return True
    if _XML_DECL_RE.match(head) and (
        "<channel" in head.lower() or "<entry" in head.lower()
    ):
        return True
    return False


def _js_shell_hit(raw: str) -> str | None:
    for marker in _JS_SHELL_MARKERS:
        if marker.lower() in (raw or "").lower():
            return marker
    return None


def _is_arxiv_abs(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:  # noqa: BLE001
        return False
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in ("arxiv.org", "www.arxiv.org", "export.arxiv.org"):
        return False
    path = parsed.path or ""
    return "/abs/" in path


def classify_fetch(
    *,
    url: str,
    raw_body: str,
    extracted_text: str,
    truncated_download: bool = False,
) -> ExtractClass:
    """Classify a fetched body for library honesty (M10 §8 / §11)."""
    raw = raw_body or ""
    text = (extracted_text or "").strip()
    final = url or ""

    if _looks_like_feed_xml(raw):
        return ExtractClass(
            kind="feed_blob",
            extract_status="feed_blob",
            extract_ok=False,
            reason="rss_or_atom_xml",
        )

    shell_marker = _js_shell_hit(raw)
    if shell_marker and (len(raw) <= _SHELL_BODY_MAX or not text):
        return ExtractClass(
            kind="js_shell",
            extract_status="js_shell",
            extract_ok=False,
            reason=f"challenge:{shell_marker}",
        )

    if not text or len(text) <= _EMPTY_EXTRACT_MAX:
        # Empty extract + challenge chrome anywhere → shell; else empty.
        if shell_marker:
            return ExtractClass(
                kind="js_shell",
                extract_status="js_shell",
                extract_ok=False,
                reason=f"empty_with_challenge:{shell_marker}",
            )
        return ExtractClass(
            kind="empty",
            extract_status="empty",
            extract_ok=False,
            reason="empty_extract",
        )

    if _is_arxiv_abs(final):
        status = "truncated_download" if truncated_download else "abs_html"
        return ExtractClass(
            kind="abs_html",
            extract_status=status if truncated_download else "abs_html",
            extract_ok=True,
            reason="arxiv_abs_page",
        )

    if truncated_download:
        return ExtractClass(
            kind="page",
            extract_status="truncated_download",
            extract_ok=True,
            reason="download_capped",
        )

    return ExtractClass(
        kind="page",
        extract_status="ok",
        extract_ok=True,
        reason="html_extract",
    )


# Statuses that count as usable library knowledge for Dream / search defaults.
KNOWLEDGE_OK_STATUSES = frozenset(
    {"ok", "feed_item_fallback", "abs_html", "truncated_download"}
)
NON_KNOWLEDGE_KINDS = frozenset({"js_shell", "feed_blob", "empty"})
