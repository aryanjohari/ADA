"""Missing API key fails closed — no Gemini call."""

from typer.testing import CliRunner

from ada.cli.main import app
from ada.secrets.load import MissingSecret, load_gemini_api_key


def test_load_gemini_missing_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("ADA_SECRETS_DIR", str(tmp_path))
    try:
        load_gemini_api_key()
        assert False, "expected MissingSecret"
    except MissingSecret as exc:
        assert "missing" in exc.message.lower() or "empty" in exc.message.lower()


def test_no_key_fails_closed(tmp_path, monkeypatch, data_root):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("ADA_SECRETS_DIR", str(tmp_path / "nosecrets"))
    (tmp_path / "nosecrets").mkdir()
    runner = CliRunner()
    result = runner.invoke(app, ["chat", "-q", "hi"])
    assert result.exit_code != 0
    assert "no_key" in (result.stdout + result.stderr).lower() or result.exit_code == 1
