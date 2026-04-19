"""FTS5 query shaping and LIKE fallback for knowledge_items search."""

from __future__ import annotations

import re

# Minimal English stopwords — tokens dropped from FTS OR-queries (not from LIKE fallback).
_KNOWLEDGE_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "if",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "as",
        "is",
        "was",
        "are",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "can",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "they",
        "them",
        "their",
        "what",
        "which",
        "who",
        "whom",
        "whose",
        "where",
        "when",
        "why",
        "how",
        "all",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "nor",
        "not",
        "only",
        "own",
        "same",
        "so",
        "than",
        "too",
        "very",
        "just",
        "about",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "from",
        "up",
        "down",
        "out",
        "off",
        "over",
        "under",
        "again",
        "once",
        "here",
        "there",
        "any",
        "me",
        "my",
        "we",
        "our",
        "you",
        "your",
        "he",
        "she",
        "him",
        "her",
        "use",
        "using",
        "tell",
        "give",
        "get",
        "make",
        "like",
        "with",
        "without",
    }
)

_TOKEN_SPLIT = re.compile(r"[^\w\-]+", re.UNICODE)


def normalize_knowledge_query_tokens(
    raw: str, *, max_tokens: int = 12
) -> list[str]:
    """
    Split user text into candidate FTS tokens: strip noise, drop stopwords.
    Preserves hyphenated alphanumerics as single tokens (e.g. co-op).
    """
    s = raw.replace('"', " ").strip()
    if not s:
        return []
    parts: list[str] = []
    for chunk in _TOKEN_SPLIT.split(s):
        t = chunk.strip().lower()
        if len(t) < 2:
            continue
        if t in _KNOWLEDGE_STOPWORDS:
            continue
        parts.append(t)
        if len(parts) >= max_tokens:
            break
    return parts


def _fts_token_expr(token: str) -> str:
    """Single-token FTS5 expression; bare alphanumerics keep porter stemming."""
    if not token:
        return ""
    safe = all(c.isalnum() or c in "-_" for c in token)
    if safe:
        return token
    return '"' + token.replace('"', " ") + '"'


def build_fts_match_query(raw: str, *, max_tokens: int = 12) -> str:
    """
    Turn free text into an FTS5 MATCH string (OR of tokens).

    Uses **unquoted** bare tokens when safe so ``porter`` stemming applies
    (quoted phrases in FTS5 disable stemming and often miss indexed text).

    Stopwords are removed so phrases like "Hastings or Salvation" become
    ``hastings OR salvation`` instead of requiring the token ``or``.

    Returns "" if there is nothing to search (caller should use LIKE fallback).
    """
    parts = normalize_knowledge_query_tokens(raw, max_tokens=max_tokens)
    if not parts:
        return ""
    return " OR ".join(_fts_token_expr(p) for p in parts)


def reciprocal_rank_fusion(
    rank_lists: list[list[int]], *, k: int = 60
) -> list[int]:
    """
    Merge ordered id lists (e.g. lexical + semantic top-k) by RRF score.
    Higher score = better; output is ids sorted by descending score.
    """
    scores: dict[int, float] = {}
    for ranks in rank_lists:
        for rank, iid in enumerate(ranks):
            scores[iid] = scores.get(iid, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
