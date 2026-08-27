"""M23 friend mouth — speech denylist, Confirm copy, life-ack register smokes."""

from __future__ import annotations

import json

from ada.cortex.charter import SPEECH_DENYLIST, build_system_charter
from ada.harness.loop import LIFE_SAVE_FAIL_ACK, _speak_gym_status, _speak_lift_log
from ada.harness.mouth import (
    CONFIRM_FOOD,
    CONFIRM_HABIT,
    CONFIRM_LINE,
    CONFIRM_SPLIT,
    MOUTH_RULES,
    apply_register_pass,
    mouth_passes_guard,
    receipt_bundle,
    should_skip_register_pass,
    speech_has_denylist,
)
from ada.cortex.adapter import CortexTurn


class _CaptureMouth:
    model = "fake"
    last_system = None

    def generate(self, *, system, contents, tools=None):
        self.last_system = system
        return CortexTurn(text="Logged lunch — 520 kcal.", tool_calls=[])


def test_m23_confirm_templates_friend_shaped_not_tool_voice() -> None:
    for line in (CONFIRM_LINE, CONFIRM_FOOD, CONFIRM_SPLIT, CONFIRM_HABIT):
        assert "no silent bind" not in line.lower()
        assert "silent write" not in line.lower()
        assert "confirm yes" not in line.lower()
    assert "Confirm" in CONFIRM_SPLIT
    assert "Confirm" in CONFIRM_HABIT
    assert "tap confirm" in CONFIRM_LINE.lower()


def test_m23_confirm_skip_still_returns_template() -> None:
    adapter = _CaptureMouth()
    text = apply_register_pass(
        adapter,
        receipts=[{"ok": True, "tool": "life_meal_log", "data": {"ok": True}}],
        template=CONFIRM_LINE,
    )
    assert text == CONFIRM_LINE
    assert adapter.last_system is None


def test_m23_speech_denylist_on_templates_and_guard() -> None:
    assert not speech_has_denylist("Logged the coffee — about 5 kcal.")
    assert speech_has_denylist("Done (receipt_id: abc)")
    assert speech_has_denylist("FOREIGN KEY constraint failed")
    assert speech_has_denylist("Run ada life habit status")
    assert LIFE_SAVE_FAIL_ACK == "That didn't save — try once more."
    assert not speech_has_denylist(LIFE_SAVE_FAIL_ACK)

    receipt = json.dumps(receipt_bundle([{
        "ok": True,
        "tool": "life_nutrition_day",
        "data": {"totals": {"energy_kcal": 520}},
    }]), default=str)
    assert mouth_passes_guard("520 kcal today.", receipt) is True
    assert mouth_passes_guard("520 kcal (receipt_id=deadbeef)", receipt) is False


def test_m23_mouth_rules_friend_result_first_no_forced_roast() -> None:
    low = MOUTH_RULES.lower()
    assert "friend" in low
    assert "roast off" in low
    assert "receipt_id" in low
    assert "slacker" not in low


def test_m23_empty_gym_status_not_roast_voice() -> None:
    spoken = _speak_gym_status({"sets_today": [], "active_session": {"session_id": "s1"}})
    low = spoken.lower()
    assert "slacker" not in low
    assert "receipt" not in low
    assert "open" in low or "no sets" in low


def test_m23_lift_speak_no_volume_invent_without_receipt_field() -> None:
    spoken = _speak_lift_log({"ok": True, "volume_kg": 300})
    assert "Logged" in spoken
    assert "300" not in spoken
    assert "receipt" not in spoken.lower()


def test_m23_charter_no_spoken_receipt_id_instruction() -> None:
    text = build_system_charter(mode="observe", include_worldview=False).lower()
    assert "do not speak receipt_id" in text or "never speak receipt_id" in text
    assert SPEECH_DENYLIST
    assert "foreign key" in text or "sql" in text


def test_m23_mouth_numeric_and_html_guards_unchanged() -> None:
    nutrition = [{
        "ok": True,
        "tool": "life_nutrition_day",
        "data": {"totals": {"energy_kcal": 520, "protein_g": 42}},
    }]
    receipt = json.dumps(receipt_bundle(nutrition), default=str)
    assert mouth_passes_guard("99999 kcal", receipt) is False
    assert mouth_passes_guard("<b>520</b>", receipt) is False
    assert mouth_passes_guard("520 kcal and 42g protein.", receipt) is True
    assert should_skip_register_pass(CONFIRM_LINE, nutrition) is True
