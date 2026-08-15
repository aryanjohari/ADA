"""Deterministic paragraph/window chunking for cite library (M10).

No embeddings. ~800–1200 char windows with small overlap.
"""

from __future__ import annotations

from typing import Any

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100
# Disk may keep a long extract; Gemini still sees OBSERVATION_CHAR_CAP.
STORE_EXTRACT_CHAR_CAP = 500_000


def chunk_text(
    text: str,
    *,
    size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
    max_chars: int = STORE_EXTRACT_CHAR_CAP,
) -> list[dict[str, Any]]:
    """Split text into overlapping chunks with char_range metadata."""
    raw = (text or "").strip()
    if not raw:
        return []
    if len(raw) > max_chars:
        raw = raw[:max_chars]
    if size < 1:
        size = CHUNK_SIZE
    overlap = max(0, min(overlap, size - 1))

    chunks: list[dict[str, Any]] = []
    start = 0
    idx = 0
    n = len(raw)
    while start < n:
        end = min(start + size, n)
        # Prefer breaking on paragraph / newline near the window end.
        if end < n:
            window = raw[start:end]
            br = max(window.rfind("\n\n"), window.rfind("\n"), window.rfind(". "))
            if br >= size // 3:
                end = start + br + 1
        piece = raw[start:end].strip()
        if piece:
            chunks.append(
                {
                    "i": idx,
                    "text": piece,
                    "char_range": [start, end],
                }
            )
            idx += 1
        if end >= n:
            break
        nxt = end - overlap
        start = nxt if nxt > start else end
    return chunks
