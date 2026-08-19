"""Gemini register-pass mouth — receipt JSON only, numeric fail-closed."""

from __future__ import annotations

import json
import re
from typing import Any

from ada.cortex.adapter import CortexAdapter
from ada.cortex.charter import load_register_contract
from ada.cortex.gemini import user_content

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
_CONFIRM_LINE = "Confirm candidates — no silent bind."

MOUTH_RULES = """
REGISTER PASS (mouth only — not a tool turn):
- Input is receipt JSON only. Rephrase fields that are present. 1–3 short sentences.
- Voice-brief (task ack). No HTML, CSS, markup, or code fences.
- Numbers never from the model: every numeric token you emit must already appear
  in the JSON (string-equal, or a whole number for a .0 value, or N% for a 0–1 rate).
- Do not invent kcal, protein, or success. Do not choose tools or panel_kind.
"""


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
    if _CONFIRM_LINE in (template or ""):
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
