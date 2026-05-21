"""When to inject ProgrammeDigest (WORK) or ProfileDigest (Entity) into chat turns."""

from __future__ import annotations

import os
import re
import sqlite3

from ada.chat_ingress import ChatSurfaceMode

_INTENT_RE = re.compile(
    r"\b(?:schedule|mission|missions|job|jobs|tick|brief|status|flags|"
    r"programme|cron|daily_brief|overdue|never\s*ran)\b",
    re.IGNORECASE,
)

_PROFILE_INTENT_RE = re.compile(
    r"\b(?:setup|flag|flags|weather|mission|missions|schedule|programme|"
    r"rss|source|sources|profile|status|jobs)\b",
    re.IGNORECASE,
)


def programme_digest_injection_enabled() -> bool:
    raw = os.environ.get("ADA_INJECT_PROGRAMME_DIGEST", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def user_message_matches_programme_intent(user_text: str) -> bool:
    return bool(_INTENT_RE.search(user_text or ""))


def should_inject_programme_digest(
    *,
    work_mode: bool = False,
    mission_id: int | None = None,
    agent_default_mission_id: int | None = None,
    user_turn_count_before: int = 0,
    user_text: str = "",
) -> bool:
    scope_id = mission_id if work_mode else agent_default_mission_id
    if scope_id is None:
        return False
    if not programme_digest_injection_enabled():
        return False
    if user_turn_count_before == 0:
        return True
    return user_message_matches_programme_intent(user_text)


def profile_digest_injection_enabled() -> bool:
    raw = os.environ.get("ADA_INJECT_PROFILE_DIGEST", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def user_message_matches_profile_intent(user_text: str) -> bool:
    return bool(_PROFILE_INTENT_RE.search(user_text or ""))


def should_inject_profile_digest(
    *,
    entity_mode: bool,
    mission_id: int | None,
    user_turn_count_before: int,
    user_text: str,
) -> bool:
    if not entity_mode or mission_id is not None:
        return False
    if not profile_digest_injection_enabled():
        return False
    if user_turn_count_before == 0:
        return True
    return user_message_matches_profile_intent(user_text)


def known_mission_slugs(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute(
        "SELECT slug FROM missions WHERE slug IS NOT NULL AND TRIM(slug) != '' ORDER BY slug"
    )
    return [str(r["slug"]).strip() for r in cur.fetchall() if str(r["slug"] or "").strip()]


def slug_mentioned_in_user_text(user_text: str, slugs: list[str]) -> str | None:
    text = user_text or ""
    if not text.strip() or not slugs:
        return None
    for slug in sorted(slugs, key=len, reverse=True):
        if not slug:
            continue
        pattern = re.compile(rf"(?<!\w){re.escape(slug)}(?!\w)", re.IGNORECASE)
        if pattern.search(text):
            return slug
    return None


def should_inject_programme_digest_for_chat(
    *,
    surface: ChatSurfaceMode,
    mission_id: int | None,
    user_turn_count_before: int,
    user_text: str,
    conn: sqlite3.Connection,
) -> tuple[bool, str | None]:
    if surface not in (ChatSurfaceMode.CHAT, ChatSurfaceMode.PLAN):
        return False, None
    if mission_id is not None:
        return False, None
    if user_turn_count_before == 0:
        return False, None
    if not programme_digest_injection_enabled():
        return False, None
    slugs = known_mission_slugs(conn)
    matched = slug_mentioned_in_user_text(user_text, slugs)
    if matched is None:
        return False, None
    return True, matched
