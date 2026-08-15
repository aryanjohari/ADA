"""Capped Gemini Dream manage-pass on delta summary only (fail-open)."""

from __future__ import annotations

import json
import re
from typing import Any

from ada.cortex.models import resolve_model

# Hard caps — Anatomy cost warnings; constitution dream_manage purpose.
MAX_OUTPUT_TOKENS = 1024
MAX_INPUT_CHARS = 12_000
_REASON_SNIPPET_CHARS = 180

_MANAGE_SYSTEM = """You are ADA's offline Dream manage-pass (not chat, not conscious).
Given a DELTA summary only, return ONE JSON object with keys:
  digest: string (short interpretive daily digest; must not claim consciousness;
    prefs-only nights stay thin — do not pretend watch consolidation)
  fact_candidates: list of {key, value} — ONLY prefer whitelist keys:
    brief_time, quiet_hours_start, quiet_hours_end, mute_proactivity,
    tease_ok, preferred_tz, brief_enabled,
    roast_energy, humor_density, chill_immediate, humor_banned_topics
  worldview_notes: list of strings (may include cite:c_… ids)
  campaign_digests: list of {campaign_id, digest, cites?} —
    one short note per campaign/watch group present in cite_heads_by_campaign
    (skip the key "ungrouped" or treat lightly). Each digest about web pages
    MUST include cite:c_… ids from that group's heads.
  open_loops: list of {text, status, kind?} — kind todo|campaign; optional stage notes only.
    Proposals are STAGED (never auto-done). Do not mark campaigns done without receipts.
  conflicts: list of strings
Never rewrite born_at. Never invent people. Never claim feelings.
When DELTA includes cite_heads about the web:
  - WORLDVIEW digest/notes/campaign_digests about those pages MUST include cite:c_… ids from the heads.
  - If extract_ok is false / extract_status is js_shell|empty|feed_blob: say the page was not readable — do not invent Beehive/stats/paper claims.
  - abs_html means abstract page only — never claim you read the PDF/paper body.
  - Keep digests short; never paste full page text into WORLDVIEW.
Return JSON only."""


def _snippet_for_reason(text: str, *, limit: int = _REASON_SNIPPET_CHARS) -> str:
    """Short ops hint; no secrets expected in manage text."""
    one = re.sub(r"\s+", " ", (text or "").strip())
    if not one:
        return ""
    if len(one) <= limit:
        return one
    return one[: limit - 1] + "…"


def _loads_object(blob: str) -> dict[str, Any]:
    """json.loads with one light trailing-comma repair (no quote surgery)."""
    try:
        obj = json.loads(blob)
    except json.JSONDecodeError:
        repaired = re.sub(r",\s*([}\]])", r"\1", blob)
        if repaired == blob:
            raise
        obj = json.loads(repaired)
    if not isinstance(obj, dict):
        raise ValueError("manage JSON root is not an object")
    return obj


def _extract_json(text: str) -> dict[str, Any]:
    """Parse manage JSON — tolerate fences, preamble, or raw objects."""
    text = (text or "").strip()
    if not text:
        raise ValueError("empty manage response")

    # Fenced ```json ... ``` (greedy inner object).
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        try:
            return _loads_object(fence.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

    # Whole text is JSON.
    try:
        return _loads_object(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # First "{" … last "}".
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return _loads_object(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON object in manage response: {exc}") from exc
        except ValueError as exc:
            raise ValueError(f"invalid JSON object in manage response: {exc}") from exc

    raise ValueError("no JSON object in manage response")


def _normalize_campaign_digests(raw_cd: Any) -> list[Any]:
    """List as-is; object keyed by campaign_id → list of entries."""
    if isinstance(raw_cd, list):
        return raw_cd
    if isinstance(raw_cd, dict):
        out: list[Any] = []
        for cid, val in raw_cd.items():
            if isinstance(val, dict):
                entry = dict(val)
                entry.setdefault("campaign_id", str(cid))
                out.append(entry)
            elif isinstance(val, str):
                out.append({"campaign_id": str(cid), "digest": val})
        return out
    return []


def _normalize_manage_result(parsed: dict[str, Any]) -> dict[str, Any]:
    return {
        "digest": parsed.get("digest") or "",
        "fact_candidates": list(parsed.get("fact_candidates") or []),
        "worldview_notes": list(parsed.get("worldview_notes") or []),
        "campaign_digests": _normalize_campaign_digests(parsed.get("campaign_digests")),
        "open_loops": list(parsed.get("open_loops") or []),
        "conflicts": list(parsed.get("conflicts") or []),
    }


def _manage_response_schema(types: Any) -> Any:
    """Gemini structured-output schema matching M11 manage JSON keys."""
    S = types.Schema
    T = types.Type
    string = S(type=T.STRING)
    value = S(
        any_of=[
            S(type=T.STRING),
            S(type=T.BOOLEAN),
            S(type=T.NUMBER),
            S(type=T.NULL),
            S(type=T.ARRAY, items=string),
        ]
    )
    fact_item = S(
        type=T.OBJECT,
        properties={"key": string, "value": value},
        required=["key", "value"],
    )
    campaign_item = S(
        type=T.OBJECT,
        properties={
            "campaign_id": string,
            "digest": string,
            "cites": S(type=T.ARRAY, items=string),
        },
        required=["campaign_id", "digest"],
    )
    loop_item = S(
        type=T.OBJECT,
        properties={
            "text": string,
            "status": string,
            "kind": string,
        },
        required=["text", "status"],
    )
    return S(
        type=T.OBJECT,
        properties={
            "digest": string,
            "fact_candidates": S(type=T.ARRAY, items=fact_item),
            "worldview_notes": S(type=T.ARRAY, items=string),
            "campaign_digests": S(type=T.ARRAY, items=campaign_item),
            "open_loops": S(type=T.ARRAY, items=loop_item),
            "conflicts": S(type=T.ARRAY, items=string),
        },
        required=[
            "digest",
            "fact_candidates",
            "worldview_notes",
            "campaign_digests",
            "open_loops",
            "conflicts",
        ],
    )


def _response_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if text:
        return str(text)
    parts: list[str] = []
    for cand in getattr(response, "candidates", None) or []:
        content = getattr(cand, "content", None)
        if content is None:
            continue
        for part in getattr(content, "parts", None) or []:
            t = getattr(part, "text", None)
            if t:
                parts.append(str(t))
    return "\n".join(parts)


def _manage_fail(reason: str, *, raw: str | None = None) -> dict[str, Any]:
    snip = _snippet_for_reason(raw or "")
    if snip:
        reason = f"{reason} | raw={snip!r}"
    return {
        "ok": False,
        "skipped": True,
        "reason": reason,
        "result": None,
    }


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
            from ada.secrets.load import load_gemini_api_key

            key = load_gemini_api_key()
        except Exception as exc:  # noqa: BLE001 — fail-open
            return {
                "ok": False,
                "skipped": True,
                "reason": f"no_key: {exc}",
                "result": None,
            }

    raw_text = ""
    try:
        from google import genai
        from google.genai import types

        model = resolve_model("dream_manage")
        gen_client = client or genai.Client(api_key=key)
        # 2.5 Flash thinking tokens count against max_output_tokens; budget=0
        # keeps the 1024-cap for the JSON body (budgets unchanged).
        config = types.GenerateContentConfig(
            system_instruction=_MANAGE_SYSTEM,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=_manage_response_schema(types),
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        )
        response = gen_client.models.generate_content(
            model=model,
            contents=summary,
            config=config,
        )
        raw_text = _response_text(response)
        parsed = _extract_json(raw_text)
        return {
            "ok": True,
            "skipped": False,
            "model": model,
            "result": _normalize_manage_result(parsed),
        }
    except Exception as exc:  # noqa: BLE001 — fail-open for seal
        return _manage_fail(f"manage_fail: {exc}", raw=raw_text)
