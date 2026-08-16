"""M15 intent→work loop — plan artifact, Accept→todos, history, eval falsifiers."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from ada.cortex.adapter import CortexTurn, ProposedToolCall
from ada.cortex.charter import mode_addendum
from ada.harness.eval import (
    exceeds_clarify_budget,
    task_done_without_receipt,
)
from ada.harness.plan_artifact import parse_plan_from_assistant
from ada.hud.app import create_app
from ada.memory import open_loops as ol
from ada.tools.gateway import Gateway


class _PlanCortex:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        return CortexTurn(
            text=(
                "```json\n"
                '{"steps":["List open campaigns","Draft next stage"]}\n'
                "```"
            ),
            tool_calls=[],
            usage={
                "prompt_token_count": 1,
                "candidates_token_count": 1,
                "total_token_count": 2,
            },
        )


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


class _WriteAttemptCortex:
    """Plan-mode model that tries a write tool (must be denied)."""

    model = "fake"
    n = 0

    def generate(self, *, system, contents, tools=None):
        self.n += 1
        if self.n == 1:
            return CortexTurn(
                text=None,
                tool_calls=[
                    ProposedToolCall(
                        name="memory_facts_append",
                        args={"key": "prefs.brief_time", "value": "06:00"},
                    )
                ],
                usage={
                    "prompt_token_count": 1,
                    "candidates_token_count": 1,
                    "total_token_count": 2,
                },
            )
        return CortexTurn(
            text="1. Stay read-only\n2. Propose only",
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


def _sse_events(body: str) -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    for block in body.split("\n\n"):
        if not block.strip() or block.startswith(":"):
            continue
        event = "message"
        data_lines: list[str] = []
        for line in block.split("\n"):
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())
        if not data_lines:
            continue
        try:
            out.append((event, json.loads("\n".join(data_lines))))
        except json.JSONDecodeError:
            continue
    return out


def test_parse_plan_json_fence():
    plan = parse_plan_from_assistant(
        'Here:\n```json\n{"steps":["A","B"]}\n```\n'
    )
    assert plan is not None
    assert len(plan["steps"]) == 2
    assert plan["steps"][0]["text"] == "A"
    assert plan["status"] == "proposed"


def test_parse_plan_numbered_list():
    plan = parse_plan_from_assistant("1. First step\n2. Second step\n")
    assert plan is not None
    assert [s["text"] for s in plan["steps"]] == ["First step", "Second step"]


def test_parse_plan_single_prose():
    plan = parse_plan_from_assistant("Just one idea.")
    assert plan is not None
    assert len(plan["steps"]) == 1
    assert "Just one idea" in plan["steps"][0]["text"]


def test_charter_plan_not_stub():
    text = mode_addendum("plan")
    assert "stub" not in text.lower()
    assert "steps" in text.lower() or "JSON" in text


def test_f3_plan_artifact_in_sse(data_root, monkeypatch):
    client, _ = _client(data_root, monkeypatch, lambda: _PlanCortex())
    _login(client)
    resp = client.post("/api/chat", json={"message": "plan this", "mode": "plan"})
    assert resp.status_code == 200
    events = _sse_events(resp.text)
    kinds = [e for e, _ in events]
    assert "plan_artifact" in kinds
    art = next(p for e, p in events if e == "plan_artifact")
    assert len(art["steps"]) == 2
    turn = next(p for e, p in events if e == "turn_done")
    assert turn.get("plan") and len(turn["plan"]["steps"]) == 2


def test_f1_plan_denies_write_tool(data_root, monkeypatch):
    client, _ = _client(data_root, monkeypatch, lambda: _WriteAttemptCortex())
    _login(client)
    resp = client.post("/api/chat", json={"message": "remember x", "mode": "plan"})
    assert resp.status_code == 200
    events = _sse_events(resp.text)
    finished = [p for e, p in events if e == "tool_call_finished"]
    assert finished
    assert finished[0].get("outcome") == "denied"


def test_f1_accept_does_not_write_facts(data_root, monkeypatch):
    client, app = _client(data_root, monkeypatch, lambda: _QuietCortex())
    _login(client)
    before = ol.list_loops(paths=None, kind="todo", status="open", limit=50)
    # Accept only todos — no facts route
    resp = client.post(
        "/api/plan/accept",
        json={
            "plan_id": "plan_test",
            "steps": [{"text": "Do alpha"}, {"text": "Do beta"}],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["count"] == 2
    after = ol.list_loops(paths=None, kind="todo", status="open", limit=50)
    assert len(after) >= len(before) + 2
    # Gateway still denies writes in plan (Accept never called facts)
    g = Gateway(mode="plan")
    denied = g.execute(
        "memory_facts_append", {"key": "prefs.brief_time", "value": "07:00"}
    )
    assert denied.outcome == "denied"


def test_f4_accept_creates_todos(data_root, monkeypatch):
    client, _ = _client(data_root, monkeypatch, lambda: _QuietCortex())
    _login(client)
    resp = client.post(
        "/api/plan/accept",
        json={"steps": [{"text": "M15 todo one"}, {"text": "M15 todo two"}]},
    )
    assert resp.status_code == 200
    ids = {t["id"] for t in resp.json()["todos"]}
    assert len(ids) == 2
    loops = ol.list_loops(paths=None, kind="todo", status="open", limit=50)
    texts = {x.get("text") for x in loops}
    assert "M15 todo one" in texts
    assert "M15 todo two" in texts


def test_f5_plan_agent_preserves_history(data_root, monkeypatch):
    client, app = _client(data_root, monkeypatch, lambda: _PlanCortex())
    _login(client)
    chat = app.state.chat
    resp = client.post("/api/chat", json={"message": "plan work", "mode": "plan"})
    assert resp.status_code == 200
    hist_len = len(chat.history)
    assert hist_len > 0
    # Switch to agent without wiping history
    chat._ensure_session("agent")
    assert len(chat.history) == hist_len
    assert chat.session is not None
    assert chat.session.mode == "agent"


def test_f8_eval_task_done_without_receipt():
    assert task_done_without_receipt("All done!") is True
    assert task_done_without_receipt("Done — receipt_id=rcpt_abc") is False
    assert task_done_without_receipt("Finished; todo marked done") is False


def test_f7_clarify_budget():
    assert exceeds_clarify_budget("One? Two?") is False
    assert exceeds_clarify_budget("One? Two? Three?") is True


def test_plan_accept_requires_session(data_root, monkeypatch):
    client, _ = _client(data_root, monkeypatch, lambda: _QuietCortex())
    resp = client.post(
        "/api/plan/accept",
        json={"steps": [{"text": "no session"}]},
    )
    assert resp.status_code == 401


def test_pending_id_confirm_bind(data_root, monkeypatch):
    client, app = _client(data_root, monkeypatch, lambda: _QuietCortex())
    _login(client)
    chat = app.state.chat
    chat.pending_confirms["rcpt_test"] = {
        "tool": "memory_open_loops_upsert",
        "args": {"text": "confirm bind todo", "kind": "todo", "status": "open"},
    }
    # Client sends wrong args — stash wins when pending_id set
    resp = client.post(
        "/api/confirm",
        json={
            "tool": "memory_open_loops_upsert",
            "args": {"text": "FORGED", "kind": "todo"},
            "pending_id": "rcpt_test",
        },
    )
    assert resp.status_code == 200
    obs = resp.json()["observation"]
    assert obs.get("ok") is True or obs.get("outcome") in ("ok", "needs_confirm")
    # Stash cleared
    assert "rcpt_test" not in chat.pending_confirms
    loops = ol.list_loops(paths=None, kind="todo", status="open", limit=50)
    texts = {x.get("text") for x in loops}
    assert "confirm bind todo" in texts
    assert "FORGED" not in texts
