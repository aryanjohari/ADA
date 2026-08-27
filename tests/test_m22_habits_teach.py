"""M22 Slice 3 — habit resolve Confirm (3a) + Confirm-create (3b)."""

from __future__ import annotations

from pathlib import Path

from ada.harness.habit_spine import build_habit_tick_args
from ada.harness.loop import run_turn
from ada.harness.pack_router import route_utterance
from ada.harness.session import ChatSession
from ada.hud.chat_service import ChatService
from ada.hud.routes_api import _CONFIRMABLE_TOOLS
from ada.io.paths import get_paths
from ada.logs import habits as habits_mod
from ada.logs.connection import open_life_db
from ada.tools.gateway import Gateway


class _ShouldNotRunAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        raise AssertionError("pack fast-path should finish before model generate")


def _habit_event_count(habit_id: str | None = None) -> int:
    with open_life_db(paths=get_paths()) as conn:
        if habit_id:
            return int(
                conn.execute(
                    "SELECT COUNT(*) FROM habit_events WHERE habit_id = ?",
                    (habit_id,),
                ).fetchone()[0]
            )
        return int(conn.execute("SELECT COUNT(*) FROM habit_events").fetchone()[0])


def _seed_ambiguous_skin(data_root: Path) -> tuple[str, str]:
    """Two habits that both match alias 'skin' → many."""
    habits_mod.upsert_habit_definition(
        habit_id="habit_skin_am",
        display_name="AM skincare",
        aliases=["skin"],
        source="seed",
    )
    habits_mod.upsert_habit_definition(
        habit_id="habit_skin_pm",
        display_name="PM skincare",
        aliases=["skin"],
        source="seed",
    )
    return "habit_skin_am", "habit_skin_pm"


# --- Slice 3a: habits resolve Confirm ---


def test_habit_tools_confirmable_allowlist() -> None:
    assert "life_habit_do" in _CONFIRMABLE_TOOLS
    assert "life_habit_miss" in _CONFIRMABLE_TOOLS


def test_route_habit_done_without_colon() -> None:
    """Phone NL 'Habit done skincare' must pack-route (not prose Confirm)."""
    r = route_utterance("Habit done skincare")
    assert r is not None
    assert r["verb"] == "habit_do"
    assert r["tool"] == "life_habit_do"
    assert "skincare" in (r["args"].get("name") or "").lower()


def test_f_m21_habit_ambiguous_needs_confirm(data_root: Path) -> None:
    """Many matches → needs_confirm; no silent tick (F-M21-7 class)."""
    a, b = _seed_ambiguous_skin(data_root)
    parsed = build_habit_tick_args("skin", verb="habit_do")
    assert parsed.get("needs_confirm") is True
    assert parsed.get("ok") is False
    cands = parsed.get("candidates") or []
    assert len(cands) >= 2
    ids = {c.get("ref_id") or c.get("habit_id") for c in cands}
    assert a in ids and b in ids

    session = ChatSession(mode="agent")
    result = run_turn(session, "habit done: skin", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    assert "Confirm habit" in (result.text or "")
    habit_receipts = [
        r for r in result.tool_receipts if str(r.get("tool") or "") == "life_habit_do"
    ]
    assert habit_receipts
    assert habit_receipts[0].get("needs_confirm") or (
        habit_receipts[0].get("data") or {}
    ).get("needs_confirm")
    assert _habit_event_count() == 0


def test_f_m21_habit_yes_binds_gateway_habit_id(data_root: Path) -> None:
    """Yes binds selected habit_id from gateway candidates — ticks that id only."""
    a, b = _seed_ambiguous_skin(data_root)
    probe = Gateway(mode="agent").execute(
        "life_habit_do",
        {"name": "skin", "confirmed": False},
    )
    assert probe.needs_confirm
    assert _habit_event_count() == 0

    svc = ChatService()
    svc._ensure_session("agent")
    data = probe.data if isinstance(probe.data, dict) else {}
    stash = dict(probe.args or {})
    for key in ("candidates", "resolve", "name", "habit_id"):
        if data.get(key) is not None and key not in stash:
            stash[key] = data[key]
    svc.pending_confirms[probe.receipt_id] = {
        "tool": "life_habit_do",
        "args": stash,
    }
    out = svc.confirm_tool(
        "life_habit_do",
        {"selected_ref_id": b, "habit_id": "HACK"},
        pending_id=probe.receipt_id,
    )
    assert out.get("ok")
    assert out.get("data", {}).get("habit_id") == b or (
        isinstance(out.get("data"), dict) and out["data"].get("habit_id") == b
    )
    # Observation shape may nest habit_id under data
    hid = (out.get("data") or {}).get("habit_id") if isinstance(out.get("data"), dict) else None
    if hid is None:
        hid = out.get("habit_id")
    assert hid == b
    assert _habit_event_count(b) == 1
    assert _habit_event_count(a) == 0


def test_f_m21_habit_deny_no_tick(data_root: Path) -> None:
    """Deny / no Confirm → fail-closed, zero habit_events."""
    _seed_ambiguous_skin(data_root)
    probe = Gateway(mode="agent").execute(
        "life_habit_do",
        {"name": "skin", "confirmed": False},
    )
    assert probe.needs_confirm
    assert _habit_event_count() == 0
    # Operator Deny does not call gateway — still no tick.
    assert _habit_event_count() == 0


def test_habit_unique_binds_without_confirm(data_root: Path) -> None:
    habits_mod.upsert_habit_definition(
        habit_id="habit_floss",
        display_name="floss",
        aliases=["flossing"],
        source="seed",
    )
    parsed = build_habit_tick_args("floss", verb="habit_do")
    assert parsed.get("ok") is True
    assert parsed.get("needs_confirm") is not True
    assert parsed["args"]["habit_id"] == "habit_floss"

    session = ChatSession(mode="agent")
    result = run_turn(session, "habit done: floss", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    assert "Habit logged" in (result.text or "")
    assert _habit_event_count("habit_floss") == 1


def test_chat_yes_alone_does_not_invent_bind(data_root: Path) -> None:
    """Consent Integrity: chat 'Yes' is not the Confirm path (no invented tick)."""
    _seed_ambiguous_skin(data_root)
    # Stale invented id + confirmed=true (model after chat Yes) must not FK / tick.
    fake = Gateway(mode="agent").execute(
        "life_habit_do",
        {
            "name": "skin",
            "habit_id": "habit_invented_skincare",
            "confirmed": True,
        },
    )
    assert not fake.ok
    assert fake.needs_confirm or (fake.data or {}).get("needs_confirm")
    assert _habit_event_count() == 0
    # Bare Yes utterance does not pack-route to habit tick.
    assert route_utterance("Yes") is None
    assert route_utterance("yes") is None


# --- Slice 3b: unknown habit Confirm-create ---


def test_life_habit_create_in_toolspec() -> None:
    from ada.tools.toolspec import SPECS_BY_NAME, WRITE_TOOL_NAMES

    assert "life_habit_create" in SPECS_BY_NAME
    assert "life_habit_create" in WRITE_TOOL_NAMES
    assert "life_habit_create" in _CONFIRMABLE_TOOLS


def test_f_m22_unknown_habit_confirm_create_no_silent(
    data_root: Path,
) -> None:
    """Empty catalog + habit done → Confirm-create; no silent SQL insert (F-M22-1/2)."""
    assert habits_mod.list_habit_definitions() == []
    parsed = build_habit_tick_args("meditation", verb="habit_do")
    assert parsed.get("needs_confirm") is True
    assert parsed.get("create") is True
    assert parsed.get("confirm_tool") == "life_habit_create"

    session = ChatSession(mode="agent")
    result = run_turn(session, "habit done: meditation", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    assert "Confirm save habit" in (result.text or "")
    create_receipts = [
        r
        for r in result.tool_receipts
        if str(r.get("tool") or "") == "life_habit_create"
    ]
    assert create_receipts
    assert create_receipts[0].get("needs_confirm") or (
        create_receipts[0].get("data") or {}
    ).get("needs_confirm")
    assert habits_mod.list_habit_definitions() == []
    assert _habit_event_count() == 0


def test_f_m22_phone_nl_unknown_habit_confirm_create(data_root: Path) -> None:
    """Habit done skincare (no colon) → Confirm-create card path, not prose/FK."""
    assert habits_mod.list_habit_definitions() == []
    session = ChatSession(mode="agent")
    result = run_turn(session, "Habit done skincare", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    create_receipts = [
        r
        for r in result.tool_receipts
        if str(r.get("tool") or "") == "life_habit_create"
    ]
    assert create_receipts
    assert habits_mod.list_habit_definitions() == []
    assert _habit_event_count() == 0


def test_f_m22_stale_habit_id_becomes_create_confirm(data_root: Path) -> None:
    """Cortex invents habit_id → needs_confirm create, never FK."""
    assert habits_mod.list_habit_definitions() == []
    probe = Gateway(mode="agent").execute(
        "life_habit_do",
        {
            "name": "skincare",
            "habit_id": "habit_skincare",
            "confirmed": False,
        },
    )
    assert probe.needs_confirm
    data = probe.data if isinstance(probe.data, dict) else {}
    assert data.get("reason") == "create_habit" or data.get("proposed_display_name")
    assert habits_mod.list_habit_definitions() == []
    assert _habit_event_count() == 0


def test_f_m22_confirm_create_then_tick(data_root: Path) -> None:
    """Yes → sticky def (source=teach_in_flow) + same-turn tick."""
    assert habits_mod.list_habit_definitions() == []
    probe = Gateway(mode="agent").execute(
        "life_habit_create",
        {
            "display_name": "meditation",
            "confirmed": False,
            "tick_after": True,
        },
    )
    assert probe.needs_confirm
    assert habits_mod.list_habit_definitions() == []

    svc = ChatService()
    svc._ensure_session("agent")
    data = probe.data if isinstance(probe.data, dict) else {}
    stash = dict(probe.args or {})
    for key in (
        "proposed_display_name",
        "display_name",
        "aliases",
        "schedule",
        "tick_after",
    ):
        if data.get(key) is not None and key not in stash:
            stash[key] = data[key]
    stash.setdefault("display_name", "meditation")
    stash.setdefault("tick_after", True)
    svc.pending_confirms[probe.receipt_id] = {
        "tool": "life_habit_create",
        "args": stash,
    }
    out = svc.confirm_tool(
        "life_habit_create",
        {},
        pending_id=probe.receipt_id,
    )
    assert out.get("ok")
    defs = habits_mod.list_habit_definitions()
    assert len(defs) == 1
    assert defs[0]["display_name"] == "meditation"
    assert defs[0]["source"] == "teach_in_flow"
    assert _habit_event_count(defs[0]["habit_id"]) == 1


def test_f_m22_hud_works_without_habit_seed(data_root: Path) -> None:
    """F-M22-1: no habit-seed required before Confirm-create path."""
    # Explicitly do not call seed_default_habits
    assert habits_mod.list_habit_definitions() == []
    session = ChatSession(mode="agent")
    result = run_turn(session, "habit done: breathwork", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    assert any(
        str(r.get("tool") or "") == "life_habit_create" for r in result.tool_receipts
    )
    assert habits_mod.list_habit_definitions() == []
