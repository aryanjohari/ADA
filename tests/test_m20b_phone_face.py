"""M20b 3b — phone ingest face (CSS hide, Ask label, TTS default off, restore)."""

from __future__ import annotations

from pathlib import Path


def _hud():
    root = Path(__file__).resolve().parents[1]
    return root / "src/ada/hud"


def test_phone_html_tts_nav_not_session_menu():
    html = (_hud() / "templates/index.html").read_text(encoding="utf-8")
    tts_at = html.index('id="tts-toggle"')
    menu_at = html.index('id="session-menu"')
    assert tts_at < menu_at
    assert "session-menu-panel" not in html[tts_at : tts_at + 80]
    assert 'aria-pressed="false"' in html
    assert "TTS off" in html
    assert 'value="observe"' in html
    assert 'value="plan"' in html
    assert 'value="agent"' in html


def test_phone_css_hides_clutter_keeps_confirm():
    css = (_hud() / "static/css/faces.css").read_text(encoding="utf-8")
    block = css[css.index('html[data-face="phone"]') :]
    for needle in (
        "#body-open",
        ".tool-card",
        ".plan-card",
        ".turn-footer",
        ".ada-orb",
        ".view-slot",
        "#welcome-line",
        "#today-strip",
        "#composer-chips",
        "#mode-segment",
        "data-field-state",
    ):
        assert needle in block, needle
    assert "var(--deny)" in block
    hide_rule = block.split("display: none !important")[0]
    assert ".confirm-card" not in hide_rule


def test_phone_taste_steel_tokens():
    tokens = (_hud() / "static/css/tokens.css").read_text(encoding="utf-8")
    assert "--accent: #6d8f9c" in tokens
    assert "--deny: #c45c5c" in tokens
    assert "#7fad63" not in tokens


def test_phone_composer_glyph_and_conditional_send():
    html = (_hud() / "templates/index.html").read_text(encoding="utf-8")
    voice = (_hud() / "static/js/voice.js").read_text(encoding="utf-8")
    assert 'class="mic-glyph"' in html
    assert 'class="tts-glyph"' in html
    assert "syncComposerChrome" in voice
    assert 'id="mode-segment"' in html


def test_phone_composer_row_nowrap_min_width():
    """Phone .chat-form must stay one line; textarea shrinks (min-width: 0)."""
    css = (_hud() / "static/css/faces.css").read_text(encoding="utf-8")
    phone = css[css.index('html[data-face="phone"]') :]
    form_at = phone.index('html[data-face="phone"] .chat-form {')
    form_block = phone[form_at : form_at + 200]
    assert "flex-wrap: nowrap" in form_block
    ta_at = phone.index('html[data-face="phone"] .chat-form textarea {')
    ta_block = phone[ta_at : ta_at + 280]
    assert "min-width: 0" in ta_block
    assert "flex: 1 1 0" in ta_block


def test_phone_mode_ask_label_observe_value():
    mode_js = (_hud() / "static/js/mode.js").read_text(encoding="utf-8")
    assert 'option[value="observe"]' in mode_js
    assert 'textContent = phone ? "Ask" : "Observe"' in mode_js
    assert 'el.value === "plan"' in mode_js
    assert 'el.value = "observe"' in mode_js
    assert 'suggested === "plan"' in mode_js


def test_tts_default_off_speak_gated():
    voice = (_hud() / "static/js/voice.js").read_text(encoding="utf-8")
    stream = (_hud() / "static/js/stream.js").read_text(encoding="utf-8")
    assert 'TTS_STORAGE = "ada_hud_tts"' in voice
    assert '=== "on"' in voice
    assert "function ttsEnabled" in voice or "export function ttsEnabled" in voice
    assert "if (!_ttsOn)" in voice
    assert "ttsEnabled()" in stream
    assert "speakFinal" in stream
    assert "/api/chat" not in voice


def test_phone_mic_is_tap_toggle_not_hold_race():
    """Stop-before-recorder-ready must queue, not no-op; second tap must not start a new recorder."""
    voice = (_hud() / "static/js/voice.js").read_text(encoding="utf-8")
    api = (_hud() / "static/js/api.js").read_text(encoding="utf-8")
    assert "function phoneFace" in voice
    assert 'currentFace() === "phone"' in voice
    assert "function onMicClick" in voice
    assert 'addEventListener("click", onMicClick)' in voice
    assert "function onMicPointerDown" in voice
    assert "_arming || _recorder || _state === \"listening\"" in voice
    assert "_stopWhenReady" in voice
    assert "_arming && !_recorder" in voice
    assert 'dispatchEvent(new Event("input"' in voice
    assert 'dataset.inputKind = "stt"' in voice
    assert "!blob.size" in voice
    assert "/api/chat" not in voice
    assert "utterance.m4a" in api
    assert "audio/mp4" in voice


def test_face_restore_from_registry_and_localstorage():
    face = (_hud() / "static/js/face.js").read_text(encoding="utf-8")
    device = (_hud() / "static/js/device.js").read_text(encoding="utf-8")
    assert "localStorage.setItem(STORAGE_KEY" in face
    assert "localStorage.getItem(STORAGE_KEY)" in face
    assert "ada-face" in face
    assert "info.face_hint" in device
    assert "urlFace()" in device
    assert "applyFace(info.face_hint)" in device
