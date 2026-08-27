"""M22 gym teach-in-flow — Slice 1 packs/split + Slice 2 last-session weights."""

from __future__ import annotations

from pathlib import Path

import pytest

from ada.harness.loop import run_turn
from ada.harness.pack_router import resolve_pack, route_utterance
from ada.harness.session import ChatSession
from ada.io.paths import get_paths
from ada.logs import gym_split as split_mod
from ada.logs.connection import open_life_db
from ada.memory.facts import get_fact
from ada.tools.gateway import Gateway
from ada.tools.toolspec import SPECS_BY_NAME, WRITE_TOOL_NAMES


class _ShouldNotRunAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        raise AssertionError("pack fast-path should finish before model generate")


def _open_session_count() -> int:
    with open_life_db(paths=get_paths()) as conn:
        return int(
            conn.execute(
                "SELECT COUNT(*) FROM gym_sessions WHERE status = 'open'"
            ).fetchone()[0]
        )


def test_pack_routes_gym_start_and_end() -> None:
    start = route_utterance("start gym")
    assert start is not None
    assert start["verb"] == "gym_start"
    assert start["tool"] == "life_gym_start"

    close = route_utterance("close gym")
    assert close is not None
    assert close["verb"] == "gym_end"
    assert close["tool"] == "life_gym_end"

    workout = route_utterance("end workout")
    assert workout is not None
    assert workout["verb"] == "gym_end"
    assert workout["tool"] == "life_gym_end"

    pack = resolve_pack("gym_start")
    assert pack is not None
    assert pack["tool"] == "life_gym_start"


def test_life_split_set_in_toolspec_and_write_set() -> None:
    assert "life_split_set" in SPECS_BY_NAME
    assert "life_split_set" in WRITE_TOOL_NAMES


def test_f_m22_split_needs_confirm_no_silent_write(data_root: Path) -> None:
    """Missing split → needs_confirm; Deny path = no FACT file (F-M22-2)."""
    assert not split_mod.has_gym_split()
    denied = split_mod.set_gym_split(
        days={"mon": {"label": "Push", "body_parts": ["chest"]}},
        confirmed=False,
    )
    assert denied.get("needs_confirm") is True
    assert not (get_paths().facts / "gym_split.yaml").is_file()
    assert get_fact("gym_split")["found"] is False


def test_f_m22_empty_split_labels_rejected(data_root: Path) -> None:
    """Empty day labels must not sticky a useless gym_split.yaml (phone H3)."""
    empty = split_mod.empty_day_slots()
    denied = Gateway(mode="agent").execute(
        "life_split_set",
        {"days": empty, "confirmed": True},
    )
    assert not denied.ok
    assert denied.needs_confirm or (denied.data or {}).get("needs_confirm")
    data = denied.data if isinstance(denied.data, dict) else {}
    assert data.get("reason") == "empty_split_labels"
    assert data.get("label_hint")
    assert not (get_paths().facts / "gym_split.yaml").is_file()
    assert get_fact("gym_split")["found"] is False


def test_f_m22_labeled_split_writes_and_status_reads(data_root: Path) -> None:
    """Labeled days write; gym_status reads FACT."""
    days = {
        "mon": {"label": "Push", "body_parts": ["chest"]},
        "tue": {"label": "Pull", "body_parts": ["back"]},
        "wed": {"label": "Legs", "body_parts": ["quads"]},
        "thu": {"label": "Rest", "body_parts": []},
    }
    written = Gateway(mode="agent").execute(
        "life_split_set",
        {"days": days, "confirmed": True},
    )
    assert written.ok
    assert (get_paths().facts / "gym_split.yaml").is_file()
    status = Gateway(mode="agent").execute("life_gym_status", {})
    assert status.ok
    assert status.data.get("gym_split") is not None
    assert status.data["gym_split"]["days"]["mon"]["label"] == "Push"


def test_f_m22_split_confirm_probe_includes_label_hint(data_root: Path) -> None:
    probe = Gateway(mode="agent").execute(
        "life_split_set",
        {"days": split_mod.empty_day_slots(), "confirmed": False},
    )
    assert probe.needs_confirm
    data = probe.data if isinstance(probe.data, dict) else {}
    assert "label_hint" in data
    assert "Push" in str(data.get("label_hint") or "")


def test_f_m22_split_confirm_write_and_gym_status_reads(data_root: Path) -> None:
    """Yes → sticky FACT; gym_status receipt includes it (F-M22-1/2)."""
    days = {
        "mon": {"label": "Upper", "body_parts": ["chest", "back"]},
        "wed": {"label": "Lower", "body_parts": ["quads"]},
    }
    probe = Gateway(mode="agent").execute(
        "life_split_set",
        {"days": days, "confirmed": False},
    )
    assert probe.needs_confirm
    assert not (get_paths().facts / "gym_split.yaml").is_file()

    written = Gateway(mode="agent").execute(
        "life_split_set",
        {"days": days, "confirmed": True},
    )
    assert written.ok
    assert (get_paths().facts / "gym_split.yaml").is_file()
    hit = get_fact("gym_split")
    assert hit["found"] is True
    assert hit["value"]["days"]["mon"]["label"] == "Upper"

    status = Gateway(mode="agent").execute("life_gym_status", {})
    assert status.ok
    assert status.data.get("gym_split") is not None
    assert status.data["gym_split"]["days"]["wed"]["body_parts"] == ["quads"]


def test_f_m22_start_gym_opens_without_yaml_and_asks_split(data_root: Path) -> None:
    """Empty root: start gym opens session + Confirm probe; no silent FACT."""
    assert not (get_paths().facts / "gym_split.yaml").is_file()
    session = ChatSession(mode="agent")
    result = run_turn(session, "start gym", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    assert _open_session_count() == 1
    assert not (get_paths().facts / "gym_split.yaml").is_file()

    split_receipts = [
        r for r in result.tool_receipts if str(r.get("tool") or "") == "life_split_set"
    ]
    assert split_receipts
    assert split_receipts[0].get("needs_confirm") or (
        split_receipts[0].get("data") or {}
    ).get("needs_confirm")
    start_receipts = [
        r for r in result.tool_receipts if str(r.get("tool") or "") == "life_gym_start"
    ]
    assert start_receipts and start_receipts[0].get("ok")
    assert "Confirm split" in (result.text or "")


def test_f_m22_deny_leaves_session_no_split_file(data_root: Path) -> None:
    """Deny = dismiss Confirm; session already open; still no gym_split.yaml."""
    session = ChatSession(mode="agent")
    result = run_turn(session, "start gym", _ShouldNotRunAdapter())
    assert _open_session_count() == 1
    assert not (get_paths().facts / "gym_split.yaml").is_file()
    # Operator Deny does not call gateway — sticky write never happens.
    assert any(
        r.get("needs_confirm") or (r.get("data") or {}).get("needs_confirm")
        for r in result.tool_receipts
    )


def test_f_m22_no_hardcoded_ppl_in_empty_slots() -> None:
    """Empty propose slots are weekday scaffolding, not baked Push/Pull/Legs."""
    slots = split_mod.empty_day_slots()
    blob = str(slots).lower()
    assert "push" not in blob
    assert "pull" not in blob
    assert "legs" not in blob
    assert set(slots.keys()) == {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}


def test_f_m22_gym_end_pack_speaks_from_receipt(data_root: Path) -> None:
    Gateway(mode="agent").execute("life_gym_start", {})
    session = ChatSession(mode="agent")
    result = run_turn(session, "close gym", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    end_receipts = [
        r for r in result.tool_receipts if str(r.get("tool") or "") == "life_gym_end"
    ]
    assert end_receipts and end_receipts[0].get("ok")
    assert _open_session_count() == 0


# --- Slice 2: last-session weights ---


@pytest.fixture
def seeded_gym(data_root: Path) -> None:
    from ada.logs.gym_import import import_exercise_seed

    import_exercise_seed(paths=get_paths())


def test_last_closed_sets_from_closed_session(
    seeded_gym: None, data_root: Path
) -> None:
    """Closed session A → same exercise_id in B shows prior load×reps on receipt."""
    from ada.harness.loop import _speak_gym_status, _speak_lift_log
    from ada.logs import gym as gym_mod

    gw = Gateway(mode="agent")

    a = gw.execute(
        "life_lift_log",
        {"sets": [{"exercise_name": "bench press", "load_kg": 60, "reps": 5}]},
    )
    assert a.ok
    eid = (a.data.get("resolved") or [{}])[0].get("exercise_id")
    assert eid
    assert a.data.get("last_session_id") is None
    ended = gw.execute("life_gym_end", {})
    assert ended.ok
    closed_sid = ended.data["session_id"]

    prior_rows = gym_mod.last_closed_sets(str(eid))
    assert len(prior_rows) >= 1
    assert prior_rows[-1]["load_kg"] == 60
    assert prior_rows[-1]["reps"] == 5
    assert prior_rows[-1]["session_id"] == closed_sid

    fields = gym_mod.last_closed_receipt_fields(str(eid))
    assert fields is not None
    assert fields["last_load_kg"] == 60
    assert fields["last_reps"] == 5
    assert fields["last_session_id"] == closed_sid
    assert fields["last_logged_at"]

    b = gw.execute(
        "life_lift_log",
        {"sets": [{"exercise_name": "bench press", "load_kg": 62.5, "reps": 5}]},
    )
    assert b.ok
    assert b.data.get("last_load_kg") == 60
    assert b.data.get("last_reps") == 5
    assert b.data.get("last_session_id") == closed_sid
    assert b.data.get("last_logged_at")
    assert (b.data.get("resolved") or [{}])[0].get("last_load_kg") == 60

    spoken = _speak_lift_log(b.data or {})
    assert "60" in spoken
    assert "5" in spoken
    assert "999" not in spoken
    assert "72" not in spoken  # invented kg fail-closed

    status = gw.execute("life_gym_status", {})
    assert status.ok
    exercises = (status.data or {}).get("exercises_today") or []
    with_prior = [e for e in exercises if e.get("last_session_id") == closed_sid]
    assert with_prior
    assert with_prior[0]["last_load_kg"] == 60
    assert with_prior[0]["last_reps"] == 5
    spoken_st = _speak_gym_status(status.data or {})
    assert "60" in spoken_st
    assert "5" in spoken_st


def test_last_closed_sets_ignores_open_only(
    seeded_gym: None, data_root: Path
) -> None:
    """Open session sets must not count as last closed (hygiene)."""
    from ada.logs import gym as gym_mod

    gw = Gateway(mode="agent")
    open_log = gw.execute(
        "life_lift_log",
        {"sets": [{"exercise_name": "bench press", "load_kg": 999, "reps": 1}]},
    )
    assert open_log.ok
    eid = (open_log.data.get("resolved") or [{}])[0].get("exercise_id")
    assert eid
    assert gym_mod.last_closed_sets(str(eid)) == []
    assert gym_mod.last_closed_receipt_fields(str(eid)) is None
    assert open_log.data.get("last_load_kg") is None


def test_speak_lift_no_invented_kg_without_prior(data_root: Path) -> None:
    from ada.harness.loop import _speak_lift_log

    spoken = _speak_lift_log({"ok": True, "volume_kg": 300})
    assert "Logged lift" in spoken
    assert "Last closed" not in spoken
    assert "300" not in spoken
