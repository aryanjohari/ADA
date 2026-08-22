"""M20c 3c — Mac desk + display panel-forward (chips +, TTS glyph, steel)."""

from __future__ import annotations

from pathlib import Path


def _hud():
    root = Path(__file__).resolve().parents[1]
    return root / "src/ada/hud"


def test_mac_chips_collapsed_behind_plus():
    html = (_hud() / "templates/index.html").read_text(encoding="utf-8")
    chips_js = (_hud() / "static/js/composer_chips.js").read_text(encoding="utf-8")
    css = (_hud() / "static/css/faces.css").read_text(encoding="utf-8")
    assert 'id="composer-chips-toggle"' in html
    assert 'aria-controls="composer-chips"' in html
    assert 'id="composer-chips"' in html
    assert "setComposerChipsOpen" in chips_js
    assert 'currentFace() === "mac"' in chips_js
    assert 'ev.key === "Escape"' in chips_js
    assert "syncComposerChipsChrome" in chips_js
    assert 'html[data-face="mac"] .composer-chips {' in css
    assert "display: none !important" in css
    assert 'html[data-face="mac"] .composer-chips.is-open' in css


def test_mac_css_tts_body_plan_hairline():
    html = (_hud() / "templates/index.html").read_text(encoding="utf-8")
    css = (_hud() / "static/css/faces.css").read_text(encoding="utf-8")
    mac = css[css.index('html[data-face="mac"]') :]
    mac = mac[: mac.index('html[data-face="phone"]')]
    assert 'id="tts-toggle"' in html
    assert 'class="tts-glyph"' in html
    assert 'id="body-open"' in html
    assert 'value="plan"' in html
    assert "composer-chips-toggle" in mac
    assert ".tts-toggle" in mac
    assert "#body-open" in mac
    assert "var(--deny)" in mac
    assert 'html[data-face="mac"] .send-btn' in mac
    assert "background: transparent" in mac


def test_display_composer_hidden_panel_shown():
    css = (_hud() / "static/css/faces.css").read_text(encoding="utf-8")
    display = css[css.index('html[data-face="display"]') :]
    assert ".chat-form" in display
    assert ".view-slot" in display
    assert "display: flex" in display.split(".view-slot")[1][:120]
    hide_chunk = display.split("display: none !important")[0]
    assert ".chat-form" in hide_chunk or 'html[data-face="display"] .chat-form' in display
    for needle in ("#body-open", "#today-strip", ".ada-orb", "#tts-toggle"):
        assert needle in display, needle


def test_tokens_still_steel_no_moss_accent():
    tokens = (_hud() / "static/css/tokens.css").read_text(encoding="utf-8")
    assert "--accent: #6d8f9c" in tokens
    assert "#7fad63" not in tokens


def test_phone_chips_still_fully_hidden():
    css = (_hud() / "static/css/faces.css").read_text(encoding="utf-8")
    phone = css[css.index('html[data-face="phone"]') :]
    phone = phone[: phone.index('html[data-face="display"]')]
    assert "#composer-chips" in phone
    assert "#composer-chips-wrap" in phone
    assert "#composer-chips-toggle" in phone
