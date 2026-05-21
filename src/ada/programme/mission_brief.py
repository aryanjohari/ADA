"""Load bounded mission brief_md for workflow runner prompts."""

from __future__ import annotations

from ada.query_engine import QueryEngine

WORKFLOW_BRIEF_MAX_CHARS_DEFAULT = 8000


def truncate_brief_utf8(text: str, *, max_chars: int) -> str:
    """Trim to max_chars code points, then UTF-8-safe byte cap if needed."""
    cap = max(0, int(max_chars))
    if not text or cap == 0:
        return ""
    s = text.strip()
    if len(s) <= cap:
        out = s
    else:
        out = s[:cap]
        if out and out[-1] == "\ufffd":
            out = out[:-1]
    data = out.encode("utf-8")
    if len(data) <= cap:
        return out
    truncated = data[:cap]
    while truncated and (truncated[-1] & 0xC0) == 0x80:
        truncated = truncated[:-1]
    return truncated.decode("utf-8", errors="replace").strip()


def programme_brief_block(brief: str) -> str:
    """Prefix block for workflow step user messages."""
    b = brief.strip()
    if not b:
        return ""
    return f"[PROGRAMME_BRIEF]\n{b}\n\n"


async def load_mission_brief_for_workflow(
    qe: QueryEngine,
    mission_id: int | None,
    *,
    max_chars: int = WORKFLOW_BRIEF_MAX_CHARS_DEFAULT,
) -> str:
    """Return trimmed brief_md for mission_id or \"\"."""
    if mission_id is None:
        return ""
    row = await qe.get_mission_by_id(int(mission_id))
    if row is None:
        return ""
    raw = str(row.get("brief_md") or "")
    return truncate_brief_utf8(raw, max_chars=max_chars)
