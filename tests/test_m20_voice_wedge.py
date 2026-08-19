"""M20 phase 2 — PTT organs, preview-Send provenance, register-pass guard."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from ada.cortex.adapter import CortexTurn
from ada.harness.loop import EMPTY_CORTEX_ACK, run_turn
from ada.harness.mouth import apply_register_pass, mouth_passes_guard, receipt_bundle
from ada.harness.session import ChatSession
from ada.hud.app import create_app
from ada.hud.xray import ALLOWED_ROOTS
from ada.io.paths import get_paths
from ada.memory.facts import WHITELIST_KEYS
from ada.voice.organs import transcribe_audio
from ada.voice.paths import voice_paths
from ada.voice.stt import MAX_AUDIO_BYTES


class _QuietCortex:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        return CortexTurn(
            text="ok",
            tool_calls=[],
            usage={
                "prompt_token_count": 1,
                "candidates_token_count": 1,
                "total_token_count": 2,
            },
        )


class _CaptureMouth:
    model = "fake"
    last_system = None
    last_contents = None
    last_tools = None
    reply = "520 kcal and 42g protein."

    def generate(self, *, system, contents, tools=None):
        self.last_system = system
        self.last_contents = contents
        self.last_tools = tools
        return CortexTurn(text=self.reply, tool_calls=[])


class _EmptyCortex:
    """Gemini-shaped blank: no text, no tools, prompt tokens == total."""

    model = "fake"
    n = 0

    def generate(self, *, system, contents, tools=None):
        self.n += 1
        return CortexTurn(
            text=None,
            tool_calls=[],
            usage={
                "prompt_token_count": 12,
                "candidates_token_count": 0,
                "total_token_count": 12,
            },
        )


class _CapturingSink:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def emit(self, event: str, payload: dict) -> None:
        self.events.append((event, payload))


class _InventKcal:
    model = "fake"
    last_contents = None
    last_tools = None

    def generate(self, *, system, contents, tools=None):
        self.last_contents = contents
        self.last_tools = tools
        return CortexTurn(text="Logged lunch — 99999 kcal.", tool_calls=[])


def _client(data_root: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ADA_HUD_COOKIE_SECURE", "0")
    monkeypatch.setenv("ADA_HUD_SESSION_SECRET", "test-secret-please-change")
    monkeypatch.setenv("ADA_HUD_PASSWORD", "test-password")
    monkeypatch.setenv("ADA_VOICE_WARMUP", "0")
    app = create_app()
    app.state.chat.adapter_factory = lambda: _QuietCortex()
    return TestClient(app)


def _user_events(data_root: Path) -> list[dict]:
    runs = data_root / "runs"
    files = list(runs.rglob("*.jsonl"))
    assert files, "expected a run receipt file"
    out: list[dict] = []
    for path in files:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("type") == "user":
                out.append(rec)
    return out


def _nutrition_receipts() -> list[dict]:
    return [
        {
            "ok": True,
            "tool": "life_nutrition_day",
            "data": {
                "date": "today",
                "totals": {"energy_kcal": 520, "protein_g": 42},
            },
        }
    ]


TEMPLATE = "today: 520 kcal 42g protein"


def test_models_tree_isolated_from_memory_and_xray(data_root):
    paths = get_paths(data_root)
    paths.ensure_voice_model_dirs()
    assert paths.models_voice == data_root / "models" / "voice"
    assert paths.memory not in paths.models_voice.parents
    assert paths.models_voice.relative_to(data_root) == Path("models/voice")
    assert "models" not in ALLOWED_ROOTS
    assert "models" not in WHITELIST_KEYS
    assert "hud_devices" not in WHITELIST_KEYS
    vp = voice_paths()
    assert vp.models_voice_whisper == paths.models_voice_whisper
    assert vp.models_voice_piper == paths.models_voice_piper


def test_empty_audio_empty_transcript(data_root, monkeypatch):
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    result = transcribe_audio(b"")
    assert result.transcript == ""
    assert not result.refused
    assert result.reason == "empty"


def test_stt_endpoint_empty_audio_does_not_run_turn(data_root, monkeypatch):
    calls = {"n": 0}

    def boom(*args, **kwargs):
        calls["n"] += 1
        raise AssertionError("STT must not call run_turn")

    monkeypatch.setattr("ada.hud.chat_service.run_turn", boom)
    monkeypatch.setattr("ada.harness.loop.run_turn", boom)
    client = _client(data_root, monkeypatch)
    resp = client.post(
        "/api/voice/stt",
        files={"audio": ("empty.webm", b"", "audio/webm")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["transcript"] == ""
    assert calls["n"] == 0


def test_stt_too_large_refused(data_root, monkeypatch):
    client = _client(data_root, monkeypatch)
    blob = b"x" * (MAX_AUDIO_BYTES + 1)
    resp = client.post(
        "/api/voice/stt",
        files={"audio": ("big.webm", blob, "audio/webm")},
    )
    assert resp.status_code == 200
    assert resp.json()["refused"] is True
    assert resp.json()["transcript"] == ""


def test_numeric_guard_fail_uses_template():
    receipt = json.dumps(receipt_bundle(_nutrition_receipts()), default=str)
    assert mouth_passes_guard("Logged lunch — 99999 kcal.", receipt) is False
    assert mouth_passes_guard("ok", receipt) is False
    assert mouth_passes_guard("<b>520</b>", receipt) is False
    adapter = _InventKcal()
    text = apply_register_pass(
        adapter, receipts=_nutrition_receipts(), template=TEMPLATE
    )
    assert text == TEMPLATE
    assert adapter.last_tools == []


def test_numeric_guard_pass_keeps_receipt_numbers():
    receipt = json.dumps(receipt_bundle(_nutrition_receipts()), default=str)
    assert mouth_passes_guard("520 kcal and 42g protein.", receipt) is True
    adapter = _CaptureMouth()
    text = apply_register_pass(
        adapter, receipts=_nutrition_receipts(), template=TEMPLATE
    )
    assert text == adapter.reply
    assert adapter.last_tools == []
    blob = str(adapter.last_contents)
    assert "RIFF" not in blob
    assert ".wav" not in blob.lower()
    assert "audio/" not in blob.lower()
    assert adapter.last_system
    assert "REGISTER" in adapter.last_system or "register" in adapter.last_system.lower()


def test_empty_receipt_skips_model():
    adapter = _CaptureMouth()
    text = apply_register_pass(adapter, receipts=[], template=TEMPLATE)
    assert text == TEMPLATE
    assert adapter.last_contents is None


def test_confirm_line_skips_model():
    adapter = _CaptureMouth()
    text = apply_register_pass(
        adapter,
        receipts=_nutrition_receipts(),
        template="Confirm candidates — no silent bind.",
    )
    assert "Confirm" in text
    assert adapter.last_contents is None


def test_hud_chat_input_stt_stamps_composer_text(data_root, monkeypatch):
    client = _client(data_root, monkeypatch)
    client.get("/")
    msg = "log meal: one banana"
    resp = client.post(
        "/api/chat",
        json={
            "message": msg,
            "mode": "observe",
            "input": "stt",
            "face": "mac",
        },
    )
    assert resp.status_code == 200
    payload = _user_events(data_root)[-1]["payload"]
    assert payload["text"] == msg
    assert payload["input"] == "stt"
    assert payload["face"] == "mac"


def test_cli_run_turn_still_typed(data_root, monkeypatch):
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    session = ChatSession(mode="observe", model="fake")
    run_turn(session, "hi from cli", _QuietCortex(), end_session=True)
    payload = _user_events(data_root)[-1]["payload"]
    assert payload["text"] == "hi from cli"
    assert payload["input"] == "typed"
    assert "face" not in payload


def test_voice_js_never_auto_posts_chat():
    root = Path(__file__).resolve().parents[1]
    voice_js = (root / "src/ada/hud/static/js/voice.js").read_text(encoding="utf-8")
    index_html = (root / "src/ada/hud/templates/index.html").read_text(encoding="utf-8")
    stream_js = (root / "src/ada/hud/static/js/stream.js").read_text(encoding="utf-8")
    assert "/api/chat" not in voice_js
    assert "openChatStream" not in voice_js
    assert "postVoiceStt" in voice_js
    assert 'id="chat-mic"' in index_html
    assert "composerInputKind" in stream_js
    assert 'input === "stt"' in stream_js or 'pendingInput === "stt"' in stream_js
    assert "SKIP_TTS_STOPS" in stream_js
    assert '"error"' in stream_js
    assert '"no_key"' in stream_js
    skip_decl = stream_js[
        stream_js.index("SKIP_TTS_STOPS") : stream_js.index(
            ";", stream_js.index("SKIP_TTS_STOPS")
        )
    ]
    assert "empty_cortex" not in skip_decl
    skip_at = stream_js.index("SKIP_TTS_STOPS.has")
    speak_at = stream_js.index("speakFinal", skip_at)
    assert speak_at > skip_at


def test_empty_cortex_is_not_completed(data_root, monkeypatch):
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    session = ChatSession(mode="observe", model="fake")
    adapter = _EmptyCortex()
    sink = _CapturingSink()
    result = run_turn(
        session,
        "Can you tell me what do you know about Ravi?",
        adapter,
        sink=sink,
        input_kind="stt",
        end_session=True,
    )
    assert adapter.n == 1
    assert result.stop_reason == "empty_cortex"
    assert result.stop_reason != "completed"
    assert result.text == EMPTY_CORTEX_ACK
    assert result.text == "No reply that turn. Try once more."
    deltas = [p["text"] for ev, p in sink.events if ev == "token_delta"]
    assert deltas == [EMPTY_CORTEX_ACK]
    events = [
        json.loads(line)
        for line in session.run_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    faults = [e for e in events if e.get("type") == "fault"]
    assert faults
    assert faults[0]["payload"]["where"] == "cortex.empty"
    ends = [e for e in events if e.get("type") == "session_end"]
    assert ends
    assert ends[0]["payload"]["stop_reason"] == "empty_cortex"


def test_tts_skip_is_503_not_cloud(data_root, monkeypatch):
    client = _client(data_root, monkeypatch)
    resp = client.post("/api/voice/tts", json={"text": "hello"})
    # No piper weights in tmp ADA_DATA_ROOT → skip, not a vendor.
    assert resp.status_code == 503
    assert resp.content == b""
