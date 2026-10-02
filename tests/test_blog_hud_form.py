"""HUD blog form: one step at a time, and the rail says which step is current."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ada.hud.app import create_app
from ada.io.paths import get_paths
from ada.memory.campaign_page import SITE

pytestmark = pytest.mark.tier_a

SOURCE = "docs/research/01_how_discovery_works.md"
QUESTION = "What do SEO, AEO, and GEO consume on one page?"
AUDIENCE = "A reader who wants one page for those three names."


def _client(monkeypatch: pytest.MonkeyPatch, data_root: Path) -> TestClient:
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    monkeypatch.delenv("ADA_PORTFOLIO_CHECKOUT", raising=False)
    monkeypatch.setenv("ADA_HUD_SESSION_SECRET", "test-secret-please-change")
    monkeypatch.setenv("ADA_HUD_PASSWORD", "test-password")
    monkeypatch.setenv("ADA_HUD_COOKIE_SECURE", "0")
    client = TestClient(create_app())
    login = client.post("/api/login", json={"password": "test-password"})
    assert login.status_code == 200
    return client


def _store(client: TestClient) -> dict:
    response = client.post(
        "/api/blog/step",
        json={
            "step": "store",
            "site": SITE,
            "audience": AUDIENCE,
            "source": SOURCE,
            "question": QUESTION,
            "fill": "researched",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_blog_form_shows_the_current_step(
    data_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(monkeypatch, data_root)
    empty = client.get("/api/blog")
    assert empty.status_code == 200
    assert empty.json()["current"] == "store"
    assert [step["state"] for step in empty.json()["steps"]] == [
        "current",
        "later",
        "later",
        "later",
        "later",
    ]

    anon = TestClient(create_app())
    refused = anon.post(
        "/api/blog/step",
        json={"step": "store", "site": SITE, "question": QUESTION},
    )
    assert refused.status_code == 401

    stored = _store(client)
    assert stored["ok"] is True
    assert stored["result_line"] == "Stored the row."
    assert stored["status"]["current"] == "gather"
    raw = get_paths().open_loops_yaml.read_text(encoding="utf-8")
    assert QUESTION not in raw

    skipped = client.post(
        "/api/blog/step",
        json={"step": "draft", "campaign_id": stored["status"]["campaign_id"]},
    )
    assert skipped.status_code == 400
    assert "Gather" in skipped.json()["result_line"]

    gathered = client.post(
        "/api/blog/step",
        json={"step": "gather", "campaign_id": stored["status"]["campaign_id"]},
    )
    assert gathered.status_code == 200, gathered.text
    body = gathered.json()
    assert body["status"]["current"] == "draft"
    assert body["status"]["packet_count"] > 0
    assert "Gathered" in body["result_line"]

    drafted = client.post(
        "/api/blog/step",
        json={"step": "draft", "campaign_id": stored["status"]["campaign_id"]},
    )
    assert drafted.status_code == 200, drafted.text
    assert drafted.json()["status"]["current"] == "copy"
    assert drafted.json()["status"]["loop_status"] == "waiting_on_aryan"

    copied = client.post(
        "/api/blog/step",
        json={
            "step": "copy",
            "campaign_id": stored["status"]["campaign_id"],
            "confirmed": True,
        },
    )
    assert copied.status_code == 400
    assert "ADA_PORTFOLIO_CHECKOUT" in copied.json()["result_line"]
    assert copied.json()["status"]["current"] == "copy"
