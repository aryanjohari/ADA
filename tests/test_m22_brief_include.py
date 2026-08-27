"""M22 Slice 4 — prefs.brief_include (Today / brief section filter)."""

from __future__ import annotations

from pathlib import Path

from ada.dream.merge import apply_manage_result
from ada.harness.brief_spine import build_brief_include_args
from ada.harness.loop import run_turn
from ada.harness.pack_router import route_utterance
from ada.harness.session import ChatSession
from ada.hud.chat_service import ChatService
from ada.hud.today import build_today
from ada.io.paths import get_paths
from ada.memory.facts import (
    BRIEF_INCLUDE_DEFAULT,
    BRIEF_INCLUDE_SECTIONS,
    WHITELIST_KEYS,
    _coerce_pref_value,
    ensure_prefs,
    load_prefs,
    propose_edit,
)
from ada.tools.gateway import Gateway


class _ShouldNotRunAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        raise AssertionError("pack fast-path should finish before model generate")


def test_brief_include_not_whitelisted() -> None:
    assert "brief_include" not in WHITELIST_KEYS


def test_coerce_brief_include(data_root: Path) -> None:
    assert _coerce_pref_value("brief_include", None) == list(BRIEF_INCLUDE_DEFAULT)
    assert _coerce_pref_value(
        "brief_include", ["dues", "open_gym", "bogus", "dues"]
    ) == ["dues", "open_gym"]
    assert _coerce_pref_value("brief_include", "dues, overnight, meal_gap") == [
        "dues",
        "overnight",
        "meal_gap",
    ]
    assert set(BRIEF_INCLUDE_SECTIONS) == {
        "dues",
        "overnight",
        "meal_gap",
        "open_gym",
        "habits_due",
        "nutrition_headline",
        "continuity",
    }


def test_utterance_maps_dont_put_gym(data_root: Path) -> None:
    parsed = build_brief_include_args("Don't put gym in my morning brief")
    assert parsed.get("ok") is True
    assert "open_gym" not in (parsed.get("proposed") or [])
    assert "open_gym" in (parsed.get("removed") or [])
    assert parsed["args"]["key"] == "prefs.brief_include"


def test_route_dont_put_gym_brief() -> None:
    r = route_utterance("Don't put gym in my morning brief")
    assert r is not None
    assert r["verb"] == "brief_include"
    assert r["tool"] == "memory_facts_propose_edit"


def test_teach_in_flow_brief_include_confirm(data_root: Path) -> None:
    """Utterance → propose brief_include → Confirm → build_today omits open_gym."""
    ensure_prefs(get_paths())
    Gateway(mode="agent").execute("life_gym_start", {})
    before = build_today(paths=get_paths())
    assert before.get("open_gym") is not None

    session = ChatSession(mode="agent")
    result = run_turn(
        session,
        "Don't put gym in my morning brief",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason == "pack_fast_path"
    assert "Confirm brief" in (result.text or "")
    propose_receipts = [
        r
        for r in result.tool_receipts
        if str(r.get("tool") or "") == "memory_facts_propose_edit"
    ]
    assert propose_receipts
    assert propose_receipts[0].get("needs_confirm") or (
        propose_receipts[0].get("data") or {}
    ).get("needs_confirm")
    assert "brief_include" not in load_prefs(get_paths())

    probe = propose_receipts[0]
    rid = probe.get("receipt_id")
    data = probe.get("data") if isinstance(probe.get("data"), dict) else {}
    stash = dict(probe.get("args") or {})
    for key in ("key", "proposed", "value", "existing"):
        if data.get(key) is not None and key not in stash:
            stash[key] = data[key]
    if "value" not in stash and data.get("proposed") is not None:
        stash["value"] = data["proposed"]
    stash.setdefault("key", "prefs.brief_include")

    svc = ChatService()
    svc._ensure_session("agent")
    svc.pending_confirms[str(rid)] = {
        "tool": "memory_facts_propose_edit",
        "args": stash,
    }
    out = svc.confirm_tool(
        "memory_facts_propose_edit",
        {},
        pending_id=str(rid),
    )
    assert out.get("ok")
    prefs = load_prefs(get_paths())
    assert "open_gym" not in (prefs.get("brief_include") or [])

    after = build_today(paths=get_paths())
    assert after.get("open_gym") is None
    assert "due_todos" in after


def test_build_today_absent_brief_include_keeps_all(data_root: Path) -> None:
    ensure_prefs(get_paths())
    prefs = load_prefs(get_paths())
    assert "brief_include" not in prefs
    Gateway(mode="agent").execute("life_gym_start", {})
    payload = build_today(paths=get_paths())
    assert payload.get("brief_include") is None
    assert payload.get("open_gym") is not None
    assert "due_todos" in payload
    assert "habits_due" in payload


def test_build_today_filters_open_gym(data_root: Path) -> None:
    """Don't put gym in brief → Confirm propose_edit → Today omits open_gym."""
    ensure_prefs(get_paths())
    Gateway(mode="agent").execute("life_gym_start", {})
    before = build_today(paths=get_paths())
    assert before.get("open_gym") is not None

    include = [s for s in BRIEF_INCLUDE_DEFAULT if s != "open_gym"]
    probe = propose_edit("prefs.brief_include", include, confirmed=False)
    assert probe.get("needs_confirm") is True
    # No silent write
    assert "brief_include" not in load_prefs(get_paths())

    written = propose_edit("prefs.brief_include", include, confirmed=True)
    assert written.get("ok") is True
    prefs = load_prefs(get_paths())
    assert prefs.get("brief_include") == include

    after = build_today(paths=get_paths())
    assert after.get("brief_include") == include
    assert after.get("open_gym") is None
    # Other sections still present (keys exist; content may be empty lists)
    assert "due_todos" in after
    assert "habits_due" in after


def test_dream_stages_brief_include(data_root: Path) -> None:
    ensure_prefs(get_paths())
    staged = apply_manage_result(
        {
            "fact_candidates": [
                {
                    "key": "prefs.brief_include",
                    "value": ["dues", "habits_due"],
                    "field": "brief_include",
                }
            ],
            "open_loop_candidates": [],
            "campaign_candidates": [],
        },
        paths=get_paths(),
        dream_id="test-brief-include",
    )
    reasons = [
        (s.get("reason") if isinstance(s, dict) else None)
        for s in (staged.get("staged") or [])
    ]
    assert "brief_include_always_stage" in reasons
    # Must not auto-merge into prefs
    assert "brief_include" not in load_prefs(get_paths())
