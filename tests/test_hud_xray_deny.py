"""X-ray allowlist + deny falsifiers (M13 F5)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ada.hud.app import create_app
from ada.io.paths import get_paths


def _seed_layout(root: Path) -> None:
    paths = get_paths(root)
    paths.ensure_memory_dirs()
    paths.ensure_cite_dirs()
    paths.ensure_dream_dirs()
    paths.runs.mkdir(parents=True, exist_ok=True)
    (paths.dreams / "2026-08-15.md").write_text(
        "# Dream digest\n\n- hello\n", encoding="utf-8"
    )
    (paths.cites / "c_test.md").write_text(
        "---\ncid: c_test\n---\n\nExcerpt body.\n", encoding="utf-8"
    )
    day = paths.runs / "2026-08-15"
    day.mkdir(parents=True, exist_ok=True)
    (day / "run.jsonl").write_text(
        '{"type":"token_delta","text":"hi"}\n', encoding="utf-8"
    )
    secrets = root / "secrets"
    secrets.mkdir(mode=0o700, exist_ok=True)
    (secrets / "gemini.env").write_text("KEY=secret\n", encoding="utf-8")
    (secrets / "hud.env").write_text("ADA_HUD_PASSWORD=x\n", encoding="utf-8")


def test_xray_list_and_read_happy(data_root, monkeypatch):
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    _seed_layout(data_root)
    client = TestClient(create_app())

    mem = client.get("/api/xray/list", params={"root": "memory", "path": ""})
    assert mem.status_code == 200
    names = {e["name"] for e in mem.json()["entries"]}
    assert "dreams" in names
    assert "cites" in names

    dreams = client.get("/api/xray/list", params={"root": "memory", "path": "dreams"})
    assert dreams.status_code == 200
    assert any(e["name"] == "2026-08-15.md" for e in dreams.json()["entries"])

    read = client.get(
        "/api/xray/read",
        params={"root": "memory", "path": "dreams/2026-08-15.md"},
    )
    assert read.status_code == 200
    body = read.json()
    assert body["binary"] is False
    assert "Dream digest" in body["text"]
    assert body["content_type"] == "text/markdown"

    runs = client.get("/api/xray/list", params={"root": "runs", "path": ""})
    assert runs.status_code == 200
    assert any(e["name"] == "2026-08-15" for e in runs.json()["entries"])

    outbox = client.get("/api/xray/list", params={"root": "outbox", "path": ""})
    assert outbox.status_code == 200
    assert "entries" in outbox.json()


def test_xray_refuses_secrets_tree(data_root, monkeypatch):
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    _seed_layout(data_root)
    client = TestClient(create_app())

    # Escape via .. from memory into secrets
    resp = client.get(
        "/api/xray/read",
        params={"root": "memory", "path": "../secrets/gemini.env"},
    )
    assert resp.status_code in (403, 404)
    assert "KEY=secret" not in resp.text
    assert "secret" not in (resp.json().get("text") or "")

    resp2 = client.get(
        "/api/xray/list",
        params={"root": "memory", "path": "../secrets"},
    )
    assert resp2.status_code in (403, 404)


def test_xray_refuses_unknown_root_and_env_names(data_root, monkeypatch):
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    _seed_layout(data_root)
    # Plant a decoy env-named file under memory — still deny by name.
    decoy = get_paths(data_root).memory / "gemini.env"
    decoy.write_text("KEY=nope\n", encoding="utf-8")

    client = TestClient(create_app())
    bad_root = client.get("/api/xray/list", params={"root": "secrets", "path": ""})
    assert bad_root.status_code == 404

    denied = client.get(
        "/api/xray/read",
        params={"root": "memory", "path": "gemini.env"},
    )
    assert denied.status_code == 403
    assert "nope" not in denied.text


def test_xray_refuses_symlink_escape(data_root, monkeypatch):
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    _seed_layout(data_root)
    paths = get_paths(data_root)
    link = paths.memory / "leak"
    try:
        link.symlink_to(data_root / "secrets" / "gemini.env")
    except OSError:
        # Some FS may block symlinks; skip soft.
        return
    client = TestClient(create_app())
    resp = client.get("/api/xray/read", params={"root": "memory", "path": "leak"})
    assert resp.status_code in (403, 404)
    assert "KEY=secret" not in resp.text
