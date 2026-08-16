"""M16 Phase 0+1 — birth pack, dues, artifacts, notify, Today (F3–F12 smokes)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from ada.body.identity import create_identity
from ada.cortex.charter import build_system_charter
from ada.hud.today import build_today
from ada.io.paths import get_paths
from ada.memory.artifacts import list_artifacts, write_artifact
from ada.memory.birth_pack import apply_birth_pack, load_syllabus_heads
from ada.memory.facts import append_fact, boot_fact_slice, ensure_prefs, load_prefs
from ada.memory.notify import notify_send
from ada.memory.open_loops import campaign_check, due_todos, upsert_loop
from ada.tools.gateway import Gateway
from ada.tools.toolspec import SPECS_BY_NAME


def test_f3_birth_pack_idempotent_and_syllabus(data_root: Path) -> None:
    paths = get_paths()
    card, created = create_identity(paths=paths, append_birth_event=False)
    assert created
    assert paths.syllabus_self.is_file()
    assert "ADA" in paths.syllabus_self.read_text(encoding="utf-8")
    assert paths.syllabus_operator.is_file()

    # Second apply does not overwrite operator edits.
    paths.syllabus_self.write_text("# CUSTOM SELF\n", encoding="utf-8")
    pack = apply_birth_pack(paths)
    assert "syllabus/SELF.md" in pack["skipped"]
    assert paths.syllabus_self.read_text(encoding="utf-8").startswith("# CUSTOM SELF")

    heads = load_syllabus_heads(paths=paths, max_chars=800)
    assert "Syllabus" in heads
    charter = build_system_charter(mode="observe")
    assert "Syllabus (SELF" in charter
    assert "not conscious" in charter.lower() or "Never claim consciousness" in charter


def test_f5_due_todos_boot_and_check(data_root: Path) -> None:
    paths = get_paths()
    ensure_prefs(paths)
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    future = (datetime.now(timezone.utc) + timedelta(days=2)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    r1 = upsert_loop(text="Pay rent", kind="todo", due_at=past, paths=paths)
    assert r1["ok"]
    upsert_loop(text="Later thing", kind="todo", due_at=future, paths=paths)

    due = due_todos(paths=paths)
    assert len(due) == 1
    assert due[0]["text"] == "Pay rent"

    boot = boot_fact_slice(paths=paths)
    assert "due_todos:" in boot
    assert "Pay rent" in boot

    check = campaign_check(paths=paths)
    assert check["due_todo_count"] == 1
    assert check["due_todos"][0]["text"] == "Pay rent"

    today = build_today(paths=paths)
    assert today["due_todos"][0]["text"] == "Pay rent"


def test_f6_artifact_write_and_jail(data_root: Path) -> None:
    paths = get_paths()
    ok = write_artifact(
        title="Link note",
        body="# Summary\nHello from Pi.\n",
        format="md",
        source_cites=["cite:c_test"],
        paths=paths,
    )
    assert ok["ok"]
    assert ok["receipt_id"]
    assert ok["path"].startswith("artifacts/")
    abs_path = Path(ok["abspath"])
    assert abs_path.is_file()
    assert "cite:c_test" in abs_path.read_text(encoding="utf-8")

    denied = write_artifact(
        title="escape",
        body="nope",
        relative_path="../../etc/passwd.md",
        paths=paths,
    )
    assert denied["ok"] is False
    assert denied["outcome"] == "denied"

    gw = Gateway(mode="agent")
    obs = gw.execute(
        "artifact_write",
        {"title": "via gateway", "body": "body text", "format": "md"},
    )
    assert obs.ok
    assert obs.data["receipt_id"]

    denied_obs = Gateway(mode="observe").execute(
        "artifact_write", {"body": "should deny"}
    )
    assert not denied_obs.ok
    assert denied_obs.outcome == "denied"


def test_f8_notify_quiet_mute_budget_cooldown(data_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = get_paths()
    ensure_prefs(paths)
    monkeypatch.setenv("NTFY_URL", "https://ntfy.example/ada-test")

    sent: list[tuple[str, dict[str, str], bytes]] = []

    def fake_post(url: str, headers: dict[str, str], body: bytes) -> tuple[int, str]:
        sent.append((url, headers, body))
        return 200, "ok"

    # Disabled → skip
    r0 = notify_send(message="hi", paths=paths, http_post=fake_post)
    assert r0["skipped"] and r0["reason"] == "notify_disabled"

    # Enable via confirmed append
    en = append_fact("prefs.notify_enabled", True, paths=paths, confirmed=True)
    assert en["ok"]

    # Mute wins
    append_fact("prefs.mute_proactivity", True, paths=paths)
    r1 = notify_send(message="muted", paths=paths, http_post=fake_post)
    assert r1["skipped"] and r1["reason"] == "proactivity_suppressed"
    append_fact("prefs.mute_proactivity", False, paths=paths)

    # First send OK
    r2 = notify_send(message="ping1", paths=paths, http_post=fake_post)
    assert r2["ok"] and not r2.get("skipped")
    assert len(sent) == 1

    # Cooldown
    r3 = notify_send(message="ping2", paths=paths, http_post=fake_post)
    assert r3["skipped"] and r3["reason"] == "cooldown"

    # Budget — force past cooldown by editing meta
    prefs = load_prefs(paths)
    prefs["notify_budget_per_day"] = 1
    prefs["_notify_meta"] = {
        "day": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "count": 1,
        "last_at": (datetime.now(timezone.utc) - timedelta(hours=2)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
    }
    from ada.memory.facts import save_prefs

    save_prefs(prefs, paths)
    r4 = notify_send(message="ping3", paths=paths, http_post=fake_post)
    assert r4["skipped"] and r4["reason"] == "budget_exhausted"


def test_f1_notify_enable_needs_confirm(data_root: Path) -> None:
    paths = get_paths()
    ensure_prefs(paths)
    r = append_fact("prefs.notify_enabled", True, paths=paths)
    assert r["needs_confirm"] is True
    assert load_prefs(paths)["notify_enabled"] is False


def test_f13_todo_next_wake_at_fails_closed(data_root: Path) -> None:
    """Remind/ping must bind remind_at — next_wake_at on todos is an error."""
    paths = get_paths()
    ensure_prefs(paths)
    wake = (datetime.now(timezone.utc) + timedelta(minutes=1)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    bad = upsert_loop(
        text="ping me to rest",
        kind="todo",
        next_wake_at=wake,
        paths=paths,
    )
    assert bad["ok"] is False
    assert bad["outcome"] == "error"
    assert "remind_at" in str(bad.get("error", "")).lower()
    assert "next_wake_at" in str(bad.get("error", "")).lower()

    # Update path also fails closed.
    ok_create = upsert_loop(text="existing todo", kind="todo", paths=paths)
    assert ok_create["ok"]
    lid = ok_create["loop"]["id"]
    bad_upd = upsert_loop(
        loop_id=lid, kind="todo", next_wake_at=wake, paths=paths
    )
    assert bad_upd["ok"] is False
    assert bad_upd["outcome"] == "error"

    gw = Gateway(mode="agent")
    obs = gw.execute(
        "memory_open_loops_upsert",
        {"text": "gateway ping", "kind": "todo", "next_wake_at": wake},
    )
    assert not obs.ok
    assert obs.outcome == "error"
    assert obs.error and "remind_at" in str(obs.error).lower()


def test_f13_todo_remind_at_still_works(data_root: Path) -> None:
    from ada.memory.open_loops import remind_soon_todos, notify_due_todos

    paths = get_paths()
    ensure_prefs(paths)
    soon = (datetime.now(timezone.utc) + timedelta(minutes=30)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    r = upsert_loop(
        text="rest ping",
        kind="todo",
        remind_at=soon,
        paths=paths,
    )
    assert r["ok"]
    assert r["loop"]["remind_at"] == soon
    assert "next_wake_at" not in r["loop"] or r["loop"].get("next_wake_at") is None

    soon_list = remind_soon_todos(paths=paths, within_hours=2.0)
    assert any(t["text"] == "rest ping" for t in soon_list)

    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    r2 = upsert_loop(
        text="notify-due ping",
        kind="todo",
        remind_at=past,
        notify=True,
        paths=paths,
    )
    assert r2["ok"]
    ready = notify_due_todos(paths=paths)
    assert any(t["text"] == "notify-due ping" for t in ready)


def test_ops_fields_and_artifact_list(data_root: Path) -> None:
    paths = get_paths()
    write_artifact(title="A", body="one", paths=paths)
    write_artifact(title="B", body="two", paths=paths)
    items = list_artifacts(paths=paths, limit=5)
    assert len(items) >= 2

    r = upsert_loop(
        text="Ping Sam",
        kind="todo",
        remind_at=(datetime.now(timezone.utc) + timedelta(hours=2)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        people_ids=["sam"],
        artifact_path="artifacts/note.md",
        starts_at=(datetime.now(timezone.utc) + timedelta(days=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        ends_at=(datetime.now(timezone.utc) + timedelta(days=1, hours=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        notify=True,
        paths=paths,
    )
    assert r["ok"]
    loop = r["loop"]
    assert loop["people_ids"] == ["sam"]
    assert loop["artifact_path"] == "artifacts/note.md"
    assert loop["notify"] is True


def test_toolspec_registers_m16_tools() -> None:
    assert "artifact_write" in SPECS_BY_NAME
    assert "notify_send" in SPECS_BY_NAME
    assert "artifact_list" in SPECS_BY_NAME
    assert SPECS_BY_NAME["artifact_write"].modes == frozenset({"agent"})
    assert SPECS_BY_NAME["notify_send"].egress == "web"


def test_f12_today_is_strip_shaped(data_root: Path) -> None:
    """Today payload is a compact strip model — not an ops dashboard schema."""
    paths = get_paths()
    ensure_prefs(paths)
    payload = build_today(paths=paths)
    # Strip keys only — no nested dashboard panels.
    allowed = {
        "ok",
        "ts",
        "due_todos",
        "remind_soon",
        "pending_confirms",
        "plan_sticky",
        "artifacts",
        "overnight",
        "continuity",
        "suppressed",
        "suppress_reasons",
    }
    assert set(payload.keys()) <= allowed
    assert isinstance(payload["due_todos"], list)
    assert "columns" not in payload
    assert "widgets" not in payload
