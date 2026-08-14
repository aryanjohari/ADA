"""Local main-content extract — trafilatura with plain-text fallback (M07).

Never return raw HTML to the model. Deterministic; no local LLM.
"""

from __future__ import annotations

from html.parser import HTMLParser
from typing import Any


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = 0
        self.title: str | None = None
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        if t in ("script", "style", "noscript"):
            self._skip += 1
        if t == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in ("script", "style", "noscript") and self._skip:
            self._skip -= 1
        if t == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        text = data.strip()
        if not text:
            return
        if self._in_title and self.title is None:
            self.title = text
        else:
            self._chunks.append(text)

    def text(self) -> str:
        return "\n".join(self._chunks)


def _fallback_extract(html: str) -> dict[str, Any]:
    parser = _VisibleTextParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # noqa: BLE001
        # Last resort: strip tags poorly
        import re

        bare = re.sub(r"<[^>]+>", " ", html)
        return {"title": None, "text": " ".join(bare.split()), "method": "strip"}
    return {
        "title": parser.title,
        "text": parser.text(),
        "method": "visible_text",
    }


def extract_main(html: str, *, url: str | None = None) -> dict[str, Any]:
    """Extract title + main text from HTML.

    Prefers trafilatura; falls back to visible-text strip.
    """
    if not html:
        return {"title": None, "text": "", "method": "empty"}

    try:
        import trafilatura

        downloaded = html
        text = trafilatura.extract(
            downloaded,
            url=url,
            include_comments=False,
            include_tables=False,
            favor_recall=False,
        )
        meta = trafilatura.extract_metadata(downloaded, default_url=url)
        title = None
        if meta is not None:
            title = getattr(meta, "title", None)
        if text and text.strip():
            return {
                "title": title,
                "text": text.strip(),
                "method": "trafilatura",
            }
    except Exception:  # noqa: BLE001 — fall through
        pass

    return _fallback_extract(html)
