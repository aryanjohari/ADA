"""M19b v1.6.1 thin skeleton — provenance, faces, Mac desk slot."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from ada.cortex.adapter import CortexTurn
from ada.harness.loop import run_turn
from ada.harness.session import ChatSession
from ada.hud.app import create_app
from ada.hud.devices import FACE_ALIASES, normalize_face
from ada.memory.facts import WHITELIST_KEYS


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


def _client(data_root: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ADA_HUD_COOKIE_SECURE", "0")
    monkeypatch.setenv("ADA_HUD_SESSION_SECRET", "test-secret-please-change")
    monkeypatch.setenv("ADA_HUD_PASSWORD", "test-password")
    app = create_app()
    app.state.chat.adapter_factory = lambda: _QuietCortex()
    return TestClient(app)


def _set_cookie_lines(resp) -> list[str]:
    h = resp.headers
    if hasattr(h, "getlist"):
        return list(h.getlist("set-cookie"))
    if hasattr(h, "get_list"):
        return list(h.get_list("set-cookie"))
    raw = h.get("set-cookie")
    return [raw] if raw else []


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


def test_normalize_face_aliases():
    assert normalize_face("phone") == "phone"
    assert normalize_face("mac") == "mac"
    assert normalize_face("display") == "display"
    assert normalize_face("mac-chat") == "mac"
    assert normalize_face("mac-companion") == "mac"
    assert normalize_face("nope") is None
    assert set(FACE_ALIASES.values()) == {"mac"}


def test_hud_devices_not_dream_whitelist():
    assert "hud_devices" not in WHITELIST_KEYS


def test_index_sets_non_httponly_device_cookie(data_root, monkeypatch):
    client = _client(data_root, monkeypatch)
    resp = client.get("/")
    assert resp.status_code == 200
    lines = _set_cookie_lines(resp)
    device_line = [ln for ln in lines if "ada_hud_device=" in ln]
    assert device_line, lines
    assert "httponly" not in device_line[0].lower()
    assert "ada_hud_session=" not in device_line[0]
    cookie_id = client.cookies.get("ada_hud_device")
    assert cookie_id
    uuid.UUID(cookie_id)


def test_device_skip_still_stamps_uuid(data_root, monkeypatch):
    client = _client(data_root, monkeypatch)
    resp = client.post("/api/device", json={})
    assert resp.status_code == 200
    body = resp.json()
    did = body["device_id"]
    uuid.UUID(did)
    assert body.get("name") in (None, "")
    yaml_path = data_root / "memory" / "facts" / "hud_devices.yaml"
    assert yaml_path.is_file()
    text = yaml_path.read_text(encoding="utf-8")
    assert did in text
    assert "schema_version: 1" in text


def test_face_query_sets_data_face(data_root, monkeypatch):
    client = _client(data_root, monkeypatch)
    phone = client.get("/?face=phone")
    assert phone.status_code == 200
    assert 'data-face="phone"' in phone.text
    mac = client.get("/?face=mac")
    assert 'data-face="mac"' in mac.text
    display = client.get("/?face=display")
    assert 'data-face="display"' in display.text
    alias = client.get("/?face=mac-companion")
    assert 'data-face="mac"' in alias.text
    alias2 = client.get("/?face=mac-chat")
    assert 'data-face="mac"' in alias2.text
    assert 'value="mac-companion"' not in alias.text
    assert 'id="ada-orb"' in mac.text
    assert 'id="view-slot"' in mac.text
    assert 'id="face-select"' in mac.text
    assert "no view open" in mac.text


def test_hud_user_event_has_input_and_face(data_root, monkeypatch):
    client = _client(data_root, monkeypatch)
    client.get("/")
    cookie_id = client.cookies.get("ada_hud_device")
    spoof = str(uuid.uuid4())
    resp = client.post(
        "/api/chat",
        json={
            "message": "hello from hud",
            "mode": "observe",
            "input": "typed",
            "face": "phone",
            "device_id": spoof,
        },
        headers={"Tailscale-User-Login": "aryan@github"},
    )
    assert resp.status_code == 200
    users = _user_events(data_root)
    assert users
    payload = users[-1]["payload"]
    assert payload["text"] == "hello from hud"
    assert payload["input"] == "typed"
    assert payload["face"] == "phone"
    assert payload["device_id"] == cookie_id
    assert payload["device_id"] != spoof
    assert payload.get("tailscale_user") == "aryan@github"


def test_cli_run_turn_omits_device_fields(data_root, monkeypatch):
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    session = ChatSession(mode="observe", model="fake")
    run_turn(session, "hi from cli", _QuietCortex(), end_session=True)
    users = _user_events(data_root)
    assert users
    payload = users[-1]["payload"]
    assert payload["text"] == "hi from cli"
    assert payload["input"] == "typed"
    assert "face" not in payload
    assert "device_id" not in payload
    assert "device_name" not in payload


def test_named_device_stamps_name_on_chat(data_root, monkeypatch):
    client = _client(data_root, monkeypatch)
    named = client.post("/api/device", json={"name": "macbook"})
    assert named.json()["name"] == "macbook"
    did = named.json()["device_id"]
    resp = client.post(
        "/api/chat",
        json={"message": "named window", "mode": "observe", "face": "mac"},
    )
    assert resp.status_code == 200
    payload = _user_events(data_root)[-1]["payload"]
    assert payload["device_id"] == did
    assert payload["device_name"] == "macbook"
    assert payload["face"] == "mac"
    assert payload["input"] == "typed"
