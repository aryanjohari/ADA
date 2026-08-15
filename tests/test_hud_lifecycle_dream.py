"""Lifecycle API reflects dream_status (not hardcoded n/a)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ada.body.lifecycle import append_event
from ada.hud.app import create_app
from ada.io.paths import get_paths


def test_lifecycle_empty_sandbox_is_honest(data_root, monkeypatch):
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    client = TestClient(create_app())
    resp = client.get("/api/lifecycle")
    assert resp.status_code == 200
    body = resp.json()
    assert body["last_dream_at"] is None
    assert body["last_dream_status"] == "n/a"
    assert body["push"] == "skipped"


def test_lifecycle_reflects_synthetic_dream_ok(data_root, monkeypatch):
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    paths = get_paths(data_root)
    paths.ensure_memory_dirs()
    paths.ensure_dream_dirs()
    ev = append_event(
        "dream_ok",
        summary="synthetic seal",
        receipts={
            "dream_id": "dream-test",
            "push": "skipped",
            "push_reason": "dream.push stub — remote not configured in v1; local seal retained",
        },
        paths=paths,
        ts="2026-08-15T10:00:00+00:00",
    )
    client = TestClient(create_app())
    resp = client.get("/api/lifecycle")
    assert resp.status_code == 200
    body = resp.json()
    assert body["last_dream_status"] == "dream_ok"
    assert body["last_dream_at"] == ev.ts
    assert body["push"] == "skipped"
    assert body.get("push_reason")


def test_lifecycle_prefers_newer_dream_fail(data_root, monkeypatch):
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    paths = get_paths(data_root)
    paths.ensure_memory_dirs()
    append_event(
        "dream_ok",
        summary="older ok",
        paths=paths,
        ts="2026-08-15T09:00:00+00:00",
    )
    fail = append_event(
        "dream_fail",
        summary="newer fail",
        paths=paths,
        ts="2026-08-15T11:00:00+00:00",
    )
    client = TestClient(create_app())
    body = client.get("/api/lifecycle").json()
    assert body["last_dream_status"] == "dream_fail"
    assert body["last_dream_at"] == fail.ts
    assert body["push"] == "skipped"
