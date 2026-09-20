"""Gemini register-pass mouth — receipt JSON only, numeric fail-closed."""

from __future__ import annotations

import json
import re
from typing import Any

from ada.cortex.adapter import CortexAdapter
from ada.cortex.charter import load_register_contract
from ada.cortex.gemini import user_content

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")

# Friend-shaped Confirm stream lines — mouth skips rewrite when template contains these.
CONFIRM_LINE = "Tap the right food, then Confirm."
CONFIRM_FOOD = "Tap the right food, then Confirm."
CONFIRM_SPLIT = "Gym's open — Confirm split on the card if you want me to remember it."
CONFIRM_HABIT = "Which habit — tap Confirm on the card."
CONFIRM_HABIT_CREATE = "Confirm save habit — tap Confirm on the card."
CONFIRM_PERSON = "Which person — tap Confirm on the card."
CONFIRM_PERSON_CREATE = "Confirm save person — tap Confirm on the card."

# Back-compat aliases for substring skip checks.
_CONFIRM_LINE = CONFIRM_LINE
_CONFIRM_FOOD = CONFIRM_FOOD
_CONFIRM_SPLIT = CONFIRM_SPLIT

# Banned in spoken/TTS output (ok in runs/ + Confirm args).
SPEECH_DENYLIST_TOKENS = (
    "receipt_id",
    "FOREIGN KEY",
    "foreign key",
    "ada life ",
    "missing_life_receipt",
)

MOUTH_RULES = """
REGISTER PASS (mouth only — not a tool turn):
- Input is receipt JSON only. Rephrase fields that are present. 1–3 short sentences.
- Friend result-first: warm, short, plain — competent friend already in the room.
- Voice-brief (task ack). No HTML, CSS, markup, or code fences.
- Roast OFF on routine meal/gym/habit/dues/miss acks unless receipt marks challenge.
- Speech denylist: never say receipt_id, raw uuid crumbs, SQL/FK prose, ada life CLI,
  missing_life_receipt, or raw JSON fences in spoken copy.
- Numbers never from the model: every numeric token you emit must already appear
  in the JSON (string-equal, or a whole number for a .0 value, or N% for a 0–1 rate).
- Do not invent kcal, protein, or success. Do not choose tools or panel_kind.
"""


def speech_has_denylist(text: str) -> bool:
    """True if spoken copy includes M23-banned metal tokens."""
    blob = (text or "").lower()
    if not blob:
        return False
    if "receipt_id" in blob:
        return True
    if re.search(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        blob,
    ):
        return True
    for tok in SPEECH_DENYLIST_TOKENS:
        if tok.lower() in blob:
            return True
    return False


def _canon(token: str) -> str:
    try:
        val = float(token)
    except ValueError:
        return token
    if val == int(val) and abs(val) < 1e15:
        return str(int(val))
    return token


def numeric_tokens(text: str) -> list[str]:
    return _NUM_RE.findall(text or "")


def allowed_numeric_tokens(receipt_json: str) -> set[str]:
    """String-equal tokens plus documented rounding (strip .0; percent of 0–1)."""
    raw = numeric_tokens(receipt_json)
    allowed: set[str] = set()
    for tok in raw:
        allowed.add(tok)
        allowed.add(_canon(tok))
        try:
            val = float(tok)
        except ValueError:
            continue
        if 0 < abs(val) <= 1:
            allowed.add(str(int(round(abs(val) * 100))))
        if tok.endswith(".0"):
            allowed.add(tok[:-2])
    return allowed


def mouth_passes_guard(output: str, receipt_json: str) -> bool:
    """True iff rewrite is grounded. Vacuous / HTML / invented numbers fail."""
    text = (output or "").strip()
    if not text:
        return False
    lower = text.lower()
    if "<" in text or "</" in text or "style=" in lower or "```" in text:
        return False
    if speech_has_denylist(text):
        return False
    allowed = allowed_numeric_tokens(receipt_json)
    out_nums = numeric_tokens(text)
    for tok in out_nums:
        if tok not in allowed and _canon(tok) not in allowed:
            return False
    if numeric_tokens(receipt_json) and not out_nums:
        return False
    return True


def receipt_bundle(receipts: list[dict[str, Any]]) -> dict[str, Any] | None:
    items: list[dict[str, Any]] = []
    for row in receipts or []:
        if not row.get("ok"):
            continue
        data = row.get("data")
        if isinstance(data, dict) and data:
            items.append({"tool": row.get("tool"), "data": data})
    if not items:
        return None
    return {"receipts": items}


def should_skip_register_pass(template: str | None, receipts: list[dict[str, Any]]) -> bool:
    if not (template or "").strip():
        return True
    tmpl = template or ""
    for marker in (
        CONFIRM_LINE,
        CONFIRM_FOOD,
        CONFIRM_SPLIT,
        CONFIRM_HABIT,
        CONFIRM_HABIT_CREATE,
        CONFIRM_PERSON,
        CONFIRM_PERSON_CREATE,
    ):
        if marker in tmpl:
            return True
    stripped = tmpl.strip()
    if re.fullmatch(
        r"(?:due add|remind|due done) logged\.|\d+ open due\(s\)\.|"
        r"(?:person|note|birthday|alias set) saved\.|"
        r"matched .+\.|"
        r"no person match — offer to capture a stub\.|"
        r"no upcoming kin events in horizon\.|"
        r"upcoming: .+\.|"
        r"\d+ matches — tap confirm on the card\.",
        stripped,
        flags=re.IGNORECASE,
    ):
        return True
    for row in receipts or []:
        if row.get("needs_confirm") or (row.get("data") or {}).get("needs_confirm"):
            return True
    return receipt_bundle(receipts) is None


def apply_register_pass(
    adapter: CortexAdapter,
    *,
    receipts: list[dict[str, Any]],
    template: str,
) -> str:
    """Gemini rewrite of receipt JSON; template on any failure. No wav. No tools."""
    if should_skip_register_pass(template, receipts):
        return template
    bundle = receipt_bundle(receipts)
    if bundle is None:
        return template
    payload = json.dumps(bundle, default=str, ensure_ascii=False)
    system = load_register_contract() + "\n" + MOUTH_RULES.strip()
    try:
        turn = adapter.generate(
            system=system,
            contents=[user_content(payload)],
            tools=[],
        )
    except Exception:  # noqa: BLE001
        return template
    if turn.tool_calls:
        return template
    text = (turn.text or "").strip()
    if not mouth_passes_guard(text, payload):
        return template
    return text
