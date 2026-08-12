"""Default interactive model is gemini-2.5-flash."""

from ada.cortex.models import MODEL_CHAT_INTERACTIVE, resolve_model


def test_model_map_default_flash(monkeypatch):
    monkeypatch.delenv("ADA_GEMINI_MODEL", raising=False)
    assert MODEL_CHAT_INTERACTIVE == "gemini-2.5-flash"
    assert resolve_model("chat_interactive") == "gemini-2.5-flash"


def test_model_env_override(monkeypatch):
    monkeypatch.setenv("ADA_GEMINI_MODEL", "gemini-2.5-pro")
    assert resolve_model("chat_interactive") == "gemini-2.5-pro"
