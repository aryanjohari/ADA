"""M28 Layer A — shared work-loop metal (plan_id pin, handshake, operator-ship)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ada.cortex.adapter import CortexTurn
from ada.cortex.charter import mode_addendum
from ada.hud.app import create_app
from ada.io.paths import get_paths
from ada.memory.artifacts import write_artifact
from ada.memory.open_loops import (
    campaign_heads,
    format_campaign_head,
    get_loop,
    upsert_loop,
)
from ada.tools.artifact_tools import run_artifact_write
from ada.tools.memory_tools import run_memory_open_loops_upsert
from ada.tools.toolspec import SPECS_BY_NAME

pytestmark = pytest.mark.tier_a


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


def _client(data_root, monkeypatch, factory):
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ADA_HUD_SESSION_SECRET", "test-secret-please-change")
    monkeypatch.setenv("ADA_HUD_PASSWORD", "test-password")
    monkeypatch.setenv("ADA_HUD_COOKIE_SECURE", "0")
    app = create_app()
    app.state.chat.adapter_factory = factory
    return TestClient(app), app


def _login(client: TestClient) -> None:
    login = client.post("/api/login", json={"password": "test-password"})
    assert login.status_code == 200


def _campaign(paths, **kwargs):
    payload = {
        "text": "Shared work container",
        "kind": "campaign",
        "status": "active",
        "stages": [
            {"id": "draft", "state": "active"},
            {"id": "ship", "state": "pending", "gate": "confirm"},
        ],
        "current_stage": "draft",
        "paths": paths,
    }
    payload.update(kwargs)
    r = upsert_loop(**payload)
    assert r["ok"], r
    return r["loop"]


def test_f_m28_8_plan_id_survives_reload(data_root: Path) -> None:
    """F-M28-8: campaign plan_id + STATUS survive get_paths() reload."""
    paths = get_paths()
    r = upsert_loop(
        text="Resume me",
        kind="campaign",
        status="waiting_on_aryan",
        plan_id="plan_ab12cd34ef56",
        blocked_reason="paste the draft",
        stages=[{"id": "ship", "state": "active", "gate": "confirm"}],
        current_stage="ship",
        paths=paths,
    )
    assert r["ok"]
    cid = r["loop"]["id"]
    assert r["loop"]["plan_id"] == "plan_ab12cd34ef56"

    via_tool = run_memory_open_loops_upsert(
        {
            "id": cid,
            "plan_id": "plan_ab12cd34ef56",
            "blocked_reason": "paste the draft",
        }
    )
    assert via_tool["ok"]

    paths2 = get_paths()
    item = get_loop(cid, paths=paths2)
    assert item is not None
    assert item["status"] == "waiting_on_aryan"
    assert item["plan_id"] == "plan_ab12cd34ef56"
    head = format_campaign_head(item)
    assert "plan=plan_ab12cd34ef56" in head
    assert "STATUS=waiting_on_aryan" in head
    heads = campaign_heads(paths=paths2)
    assert any(h.get("id") == cid and h.get("plan_id") == "plan_ab12cd34ef56" for h in heads)


def test_handshake_artifact_write_waiting_on_aryan(data_root: Path) -> None:
    paths = get_paths()
    camp = _campaign(paths)
    cid = camp["id"]
    rel = f"work/{cid}/draft.md"
    out = run_artifact_write(
        {
            "title": "draft",
            "body": "# Draft\nhello\n",
            "path": rel,
            "campaign_id": cid,
            "next_stage": "ship",
            "waiting_reason": f"paste artifacts/work/{cid}/draft.md",
        }
    )
    assert out["ok"]
    assert out["path"] == f"artifacts/{rel}"
    hs = out.get("handshake") or {}
    assert hs.get("ok") is True
    item = get_loop(cid, paths=get_paths())
    assert item is not None
    assert item["status"] == "waiting_on_aryan"
    assert item["current_stage"] == "ship"
    assert item["last_receipt"] == f"artifacts/{rel}"
    assert "paste artifacts/work/" in str(item.get("blocked_reason"))
    stages = {s["id"]: s["state"] for s in item["stages"]}
    assert stages["draft"] == "done"
    assert stages["ship"] == "active"


def test_f_m28_7_done_needs_operator_ship_receipt(data_root: Path) -> None:
    paths = get_paths()
    camp = _campaign(paths, status="waiting_on_aryan", current_stage="ship")
    cid = camp["id"]
    upsert_loop(
        loop_id=cid,
        last_receipt=f"artifacts/work/{cid}/draft.md",
        paths=paths,
    )

    need = upsert_loop(loop_id=cid, status="done", paths=paths)
    assert need.get("needs_confirm") is True
    assert get_loop(cid, paths=paths)["status"] == "waiting_on_aryan"

    denied = upsert_loop(loop_id=cid, status="done", confirmed=True, paths=paths)
    assert denied.get("ok") is not True
    assert denied.get("outcome") == "denied"
    assert get_loop(cid, paths=paths)["status"] == "waiting_on_aryan"

    unconfirmed_url = upsert_loop(
        loop_id=cid,
        status="done",
        last_receipt="https://example.test/blog/one",
        paths=paths,
    )
    assert unconfirmed_url.get("needs_confirm") is True
    assert get_loop(cid, paths=paths)["status"] == "waiting_on_aryan"

    invented = upsert_loop(
        loop_id=cid,
        status="done",
        last_receipt="https://...",
        confirmed=True,
        paths=paths,
    )
    assert invented.get("ok") is not True
    assert invented.get("outcome") in {"denied", "needs_confirm"}

    ok = upsert_loop(
        loop_id=cid,
        status="done",
        last_receipt="https://example.test/blog/one",
        confirmed=True,
        paths=paths,
    )
    assert ok["ok"] is True
    done = get_loop(cid, paths=paths)
    assert done["status"] == "done"
    assert done["last_receipt"] == "https://example.test/blog/one"


def test_false_completion_draft_path_not_ship(data_root: Path) -> None:
    paths = get_paths()
    camp = _campaign(paths)
    cid = camp["id"]
    draft = f"artifacts/work/{cid}/draft.md"
    write_artifact(
        title="draft",
        body="# Draft\n",
        relative_path=f"work/{cid}/draft.md",
        campaign_id=cid,
        next_stage="ship",
        waiting_reason="operator ships next",
        paths=paths,
    )
    item = get_loop(cid, paths=paths)
    assert item["status"] == "waiting_on_aryan"
    assert item["last_receipt"] == draft

    blocked = upsert_loop(
        loop_id=cid,
        status="done",
        last_receipt=draft,
        confirmed=True,
        paths=paths,
    )
    assert blocked.get("ok") is not True
    assert blocked.get("outcome") == "denied"
    assert get_loop(cid, paths=paths)["status"] == "waiting_on_aryan"

    sent = upsert_loop(
        loop_id=cid,
        status="done",
        last_receipt="sent to Acme via email on 2026-09-20",
        confirmed=True,
        paths=paths,
    )
    assert sent["ok"] is True
    assert get_loop(cid, paths=paths)["status"] == "done"


def test_accept_todo_pin_campaign_and_plan(data_root: Path, monkeypatch) -> None:
    paths = get_paths()
    camp = _campaign(paths)
    cid = camp["id"]
    client, _ = _client(data_root, monkeypatch, lambda: _QuietCortex())
    _login(client)
    resp = client.post(
        "/api/plan/accept",
        json={
            "plan_id": "plan_pinloop01",
            "campaign_id": cid,
            "steps": [{"text": "Write the draft"}, {"text": "Wait for ship"}],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["plan_id"] == "plan_pinloop01"
    assert body["campaign_id"] == cid
    assert body["count"] == 2

    todos = [get_loop(t["id"], paths=get_paths()) for t in body["todos"]]
    assert all(t and t.get("campaign_id") == cid for t in todos)
    assert all(t and t.get("plan_id") == "plan_pinloop01" for t in todos)

    camp2 = get_loop(cid, paths=get_paths())
    assert camp2 is not None
    assert camp2["plan_id"] == "plan_pinloop01"

    direct = upsert_loop(
        text="Pinned via upsert",
        kind="todo",
        campaign_id=cid,
        plan_id="plan_pinloop01",
        paths=get_paths(),
    )
    assert direct["ok"]
    assert direct["loop"]["campaign_id"] == cid
    assert direct["loop"]["plan_id"] == "plan_pinloop01"


def test_toolspec_and_charter_shared_loop_recipe() -> None:
    upsert = SPECS_BY_NAME["memory_open_loops_upsert"]
    write = SPECS_BY_NAME["artifact_write"]
    assert "plan_id" in upsert.schema["parameters"]["properties"]
    assert "campaign_id" in upsert.schema["parameters"]["properties"]
    assert "campaign_id" in write.schema["parameters"]["properties"]
    assert "waiting_on_aryan" in write.schema["description"]
    agent = mode_addendum("agent")
    assert "waiting_on_aryan" in agent
    assert "Accept ≠ Confirm ≠ operator-ship" in agent or "Accept" in agent
    plan = mode_addendum("plan")
    assert "stub" not in plan.lower()
