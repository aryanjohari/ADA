"""Gemini text embeddings for semantic knowledge search (optional, env-gated)."""

from __future__ import annotations

import asyncio
import logging
import struct

from google import genai
from google.genai import types

log = logging.getLogger("ada.embeddings")


def float32_list_to_blob(values: list[float]) -> bytes:
    return struct.pack(f"<{len(values)}f", *values)


def blob_to_float32_list(blob: bytes) -> list[float]:
    if not blob or len(blob) % 4:
        return []
    n = len(blob) // 4
    return list(struct.unpack(f"<{n}f", blob))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _embed_blocking(
    api_key: str,
    text: str,
    *,
    model: str,
    output_dimensionality: int,
    task_type: str | None,
) -> list[float]:
    client = genai.Client(api_key=api_key)
    cfg_kw: dict[str, object] = {"output_dimensionality": output_dimensionality}
    if task_type is not None:
        cfg_kw["task_type"] = task_type
    resp = client.models.embed_content(
        model=model,
        contents=text,
        config=types.EmbedContentConfig(**cfg_kw),
    )
    return list(resp.embeddings[0].values)


async def embed_query_text(
    api_key: str,
    text: str,
    *,
    model: str,
    output_dimensionality: int,
) -> list[float]:
    return await asyncio.to_thread(
        _embed_blocking,
        api_key,
        text,
        model=model,
        output_dimensionality=output_dimensionality,
        task_type="RETRIEVAL_QUERY",
    )


async def embed_document_text(
    api_key: str,
    text: str,
    *,
    model: str,
    output_dimensionality: int,
) -> list[float]:
    return await asyncio.to_thread(
        _embed_blocking,
        api_key,
        text,
        model=model,
        output_dimensionality=output_dimensionality,
        task_type="RETRIEVAL_DOCUMENT",
    )
