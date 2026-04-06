"""Manual dream job: model summarizes transcript + usage → master/soul append."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from google import genai
from google.genai import types

from ada.config import Settings
from ada.memory_io import append_markdown_block, format_master_section, format_soul_fragment
from ada.query_engine import QueryEngine

_DREAM_SYSTEM = """You compress local agent logs into durable memory updates.
Rules:
- Never copy API keys, tokens, or secrets into output.
- master_body: concise Markdown bullets of durable facts (hardware, preferences, recurring tasks).
- soul_fragment: at most 2 short sentences adjusting tone/persona ONLY if clearly justified; else "".
- Output MUST be valid JSON only with keys: master_heading (string), master_body (string), soul_fragment (string).
"""


async def run_dream_job(
    qe: QueryEngine,
    settings: Settings,
    *,
    session_id: int | None,
    dry_run: bool,
    max_messages: int,
) -> dict[str, Any]:
    """
    Summarize recent messages + usage ledger; append to master.md / optionally soul.md.
    Intended for manual `ada dream` (cron later). Logs to action_log.
    """
    transcript = await qe.load_messages_for_dream(
        session_id=session_id, limit=max_messages
    )
    usage_lines = await qe.load_usage_ledger_lines(40)
    user_block = (
        "Recent transcript lines (oldest→newest in window):\n"
        + ("\n".join(transcript) if transcript else "(empty)")
        + "\n\nRecent usage_ledger rows:\n"
        + ("\n".join(usage_lines) if usage_lines else "(empty)")
    )
    await qe.append_action_log(
        "dream_start",
        {
            "dry_run": dry_run,
            "session_id": session_id,
            "transcript_lines": len(transcript),
        },
        session_id=session_id,
    )

    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    client = genai.Client(api_key=settings.gemini_api_key)
    resp = await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=[
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_block)],
            )
        ],
        config=types.GenerateContentConfig(
            system_instruction=_DREAM_SYSTEM,
            response_mime_type="application/json",
        ),
    )
    raw = (getattr(resp, "text", None) or "").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        await qe.append_action_log(
            "dream_failed",
            {"error": "invalid_json", "preview": raw[:500]},
            session_id=session_id,
        )
        raise RuntimeError(f"dream model returned non-JSON: {e}") from e

    heading = str(data.get("master_heading") or "Dream compression").strip()
    master_body = str(data.get("master_body") or "").strip()
    soul_frag = str(data.get("soul_fragment") or "").strip()

    applied: dict[str, Any] = {"master": False, "soul": False, "dry_run": dry_run}
    if not dry_run:
        if master_body:
            block = format_master_section(heading, master_body)
            await append_markdown_block(
                settings.master_path,
                settings.memory_backups_dir,
                block,
                memory_dir=settings.memory_dir,
                max_block_bytes=settings.memory_max_append_bytes,
                max_file_bytes=settings.memory_max_file_bytes,
            )
            applied["master"] = True
        if soul_frag:
            if len(soul_frag.encode("utf-8")) > settings.dream_max_soul_bytes:
                raise ValueError("soul_fragment exceeds dream_max_soul_bytes")
            sblock = format_soul_fragment(soul_frag)
            await append_markdown_block(
                settings.soul_path,
                settings.memory_backups_dir,
                sblock,
                memory_dir=settings.memory_dir,
                max_block_bytes=settings.memory_max_append_bytes,
                max_file_bytes=settings.memory_max_file_bytes,
            )
            applied["soul"] = True
    else:
        applied["preview"] = {
            "master_heading": heading,
            "master_body": master_body,
            "soul_fragment": soul_frag,
        }

    await qe.append_action_log(
        "dream_complete",
        {
            "applied": applied,
            "master_heading": heading,
            "master_chars": len(master_body),
            "soul_chars": len(soul_frag),
            "model": settings.gemini_model,
        },
        session_id=session_id,
    )
    await qe.state_set("dream.last_run_at", datetime.now(timezone.utc).isoformat())
    return applied
