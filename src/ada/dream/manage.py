"""Capped Gemini Dream manage-pass on delta summary only (fail-open)."""

from __future__ import annotations

import json
import re
from typing import Any

from ada.cortex.models import resolve_model

# Hard caps — Anatomy cost warnings; constitution dream_manage purpose.
MAX_OUTPUT_TOKENS = 1024
MAX_INPUT_CHARS = 12_000

_MANAGE_SYSTEM = """You are ADA's offline Dream manage-pass (not chat, not conscious).
Given a DELTA summary only, return ONE JSON object with keys:
  digest: string (short interpretive daily digest; must not claim consciousness)
  fact_candidates: list of {key, value} — ONLY prefer whitelist keys:
    brief_time, quiet_hours_start, quiet_hours_end, mute_proactivity,
    tease_ok, preferred_tz, brief_enabled,
    roast_energy, humor_density, chill_immediate, humor_banned_topics
  worldview_notes: list of strings
  open_loops: list of {text, status, kind?} — kind todo|campaign; optional stage notes only.
    Proposals are STAGED (never auto-done). Do not mark campaigns done without receipts.
  conflicts: list of strings
Never rewrite born_at. Never invent people. Never claim feelings.
Return JSON only."""


def _extract_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ValueError("empty manage response")
    # Fenced block.
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        return json.loads(fence.group(1))
    # Raw object.
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError("no JSON object in manage response")


def manage_delta(
    delta: dict[str, Any],
    *,
    api_key: str | None = None,
    client: Any | None = None,
    skip: bool = False,
) -> dict[str, Any]:
    """Run capped manage. On any failure return skipped/failed — caller still seals."""
    if skip:
        return {
            "ok": False,
            "skipped": True,
            "reason": "manage skipped by caller",
            "result": None,
        }

    summary = str(delta.get("summary_text") or "")[:MAX_INPUT_CHARS]
    if not summary.strip():
        return {
            "ok": False,
            "skipped": True,
            "reason": "empty delta summary",
            "result": None,
        }

    key = api_key
    if not key and client is None:
        try:
            from ada.secrets.load import MissingSecret, load_gemini_api_key

            key = load_gemini_api_key()
        except Exception as exc:  # noqa: BLE001 — fail-open
            return {
                "ok": False,
                "skipped": True,
                "reason": f"no_key: {exc}",
                "result": None,
            }

    try:
        from google import genai
        from google.genai import types

        model = resolve_model("dream_manage")
        gen_client = client or genai.Client(api_key=key)
        config = types.GenerateContentConfig(
            system_instruction=_MANAGE_SYSTEM,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            temperature=0.2,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        )
        response = gen_client.models.generate_content(
            model=model,
            contents=summary,
            config=config,
        )
        text = getattr(response, "text", None)
        if not text:
            # Fallback extract from candidates.
            parts: list[str] = []
            for cand in getattr(response, "candidates", None) or []:
                content = getattr(cand, "content", None)
                if content is None:
                    continue
                for part in getattr(content, "parts", None) or []:
                    t = getattr(part, "text", None)
                    if t:
                        parts.append(t)
            text = "\n".join(parts)
        parsed = _extract_json(text or "")
        return {
            "ok": True,
            "skipped": False,
            "model": model,
            "result": {
                "digest": parsed.get("digest") or "",
                "fact_candidates": list(parsed.get("fact_candidates") or []),
                "worldview_notes": list(parsed.get("worldview_notes") or []),
                "open_loops": list(parsed.get("open_loops") or []),
                "conflicts": list(parsed.get("conflicts") or []),
            },
        }
    except Exception as exc:  # noqa: BLE001 — fail-open for seal
        return {
            "ok": False,
            "skipped": True,
            "reason": f"manage_fail: {exc}",
            "result": None,
        }
