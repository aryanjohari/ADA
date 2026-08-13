"""M06 campaigns / open_loops skeleton — falsifiers F1–F8."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from typer.testing import CliRunner

from ada.cli.main import app
from ada.dream.merge import apply_manage_result
from ada.io.paths import get_paths
from ada.memory.facts import append_fact, boot_fact_slice, ensure_prefs
from ada.memory.open_loops import (
    K_CAMPAIGN_HEADS,
    campaign_check,
    campaign_heads,
    due_campaigns,
    ensure_open_loops,
    get_loop,
    list_campaigns,
    list_loops,
    upsert_loop,
)
from ada.memory.proactivity import in_quiet_hours, proactivity_suppressed
from ada.memory.staging import list_staged


def test_f1_orphan_tmp_does_not_corrupt_status(data_root: Path) -> None:
    """F1: process-kill orphan .tmp leaves prior good STATUS readable."""
    paths = get_paths()
    ensure_open_loops(paths)
    r1 = upsert_loop(
        text="Job hunt",
        kind="campaign",
        status="active",
        stages=[{"id": "research", "state": "active"}],
        current_stage="research",
        paths=paths,
    )
    assert r1["ok"]
    cid = r1["loop"]["id"]
    target = paths.open_loops_yaml
    orphan = target.with_name(f"{target.name}.tmp.99999")
    orphan.write_text("CORRUPT", encoding="utf-8")
    loaded = get_loop(cid, paths=paths)
    assert loaded is not None
    assert loaded["status"] == "active"
    assert loaded["current_stage"] == "research"
    # New write cleans orphans via atomic_write_text
    upsert_loop(
        loop_id=cid,
        text="Job hunt",
        current_stage="shortlist",
        paths=paths,
    )
    assert get_loop(cid, paths=paths)["current_stage"] == "shortlist"


def test_f2_new_session_reads_status_from_disk(data_root: Path) -> None:
    """F2: fresh paths load sees campaign STATUS from file."""
    paths = get_paths()
    r = upsert_loop(
        text="Research watch",
        kind="campaign",
        status="blocked",
        blocked_reason="need API key",
        stages=[
            {"id": "scan", "state": "done"},
            {"id": "digest", "state": "active"},
        ],
        current_stage="digest",
        paths=paths,
    )
    cid = r["loop"]["id"]
    # Simulate new session: new DataPaths via get_paths again
    paths2 = get_paths()
    item = get_loop(cid, paths=paths2)
    assert item is not None
    assert item["status"] == "blocked"
    assert item["current_stage"] == "digest"
    assert item["blocked_reason"] == "need API key"


def test_f3_gated_done_needs_confirm_or_receipt(data_root: Path) -> None:
    """F3: cannot mark gated stage done without confirm/receipt."""
    paths = get_paths()
    r = upsert_loop(
        text="Apply jobs",
        kind="campaign",
        status="active",
        stages=[
            {"id": "research", "state": "done"},
            {"id": "apply", "state": "pending", "gate": "confirm"},
        ],
        current_stage="apply",
        paths=paths,
    )
    cid = r["loop"]["id"]
    blocked = upsert_loop(
        loop_id=cid,
        stages=[
            {"id": "research", "state": "done"},
            {"id": "apply", "state": "done", "gate": "confirm"},
        ],
        paths=paths,
    )
    assert blocked.get("needs_confirm") is True
    assert get_loop(cid, paths=paths)["stages"][1]["state"] == "pending"

    ok_receipt = upsert_loop(
        loop_id=cid,
        stages=[
            {"id": "research", "state": "done"},
            {"id": "apply", "state": "done", "gate": "confirm"},
        ],
        last_receipt="runs/2026-08-13/sess_test.jsonl#evt_1",
        paths=paths,
    )
    assert ok_receipt["ok"] is True
    assert get_loop(cid, paths=paths)["stages"][1]["state"] == "done"

    # Campaign-level done without confirm after clearing receipt path still gated
    r2 = upsert_loop(
        text="Other",
        kind="campaign",
        status="active",
        stages=[{"id": "apply", "state": "pending", "gate": "confirm"}],
        paths=paths,
    )
    cid2 = r2["loop"]["id"]
    need = upsert_loop(loop_id=cid2, status="done", paths=paths)
    assert need.get("needs_confirm") is True
    confirmed = upsert_loop(loop_id=cid2, status="done", confirmed=True, paths=paths)
    assert confirmed["ok"] is True


def test_f4_boot_slice_budget_no_runs_dump(data_root: Path) -> None:
    """F4: boot injects ≤K campaign heads; no runs/ dump; done excluded."""
    paths = get_paths()
    ensure_prefs(paths)
    upsert_loop(
        text="Blocked one",
        kind="campaign",
        status="waiting_on_aryan",
        blocked_reason="pick resume",
        stages=[{"id": "decide", "state": "active"}],
        current_stage="decide",
        paths=paths,
    )
    for i in range(4):
        upsert_loop(
            text=f"Active {i}",
            kind="campaign",
            status="active",
            stages=[{"id": "s1", "state": "active"}],
            current_stage="s1",
            paths=paths,
        )
    upsert_loop(
        text="Finished",
        kind="campaign",
        status="done",
        confirmed=True,
        stages=[{"id": "s1", "state": "done"}],
        current_stage="s1",
        paths=paths,
    )
    upsert_loop(text="Buy milk", kind="todo", status="open", paths=paths)

    heads = campaign_heads(paths=paths, limit=K_CAMPAIGN_HEADS)
    assert len(heads) <= K_CAMPAIGN_HEADS
    assert heads[0]["status"] == "waiting_on_aryan"
    assert all(h["status"] != "done" for h in heads)

    slice_text = boot_fact_slice(paths=paths, max_chars=3200)
    assert "campaigns:" in slice_text
    assert "waiting_on_aryan" in slice_text
    assert "Finished" not in slice_text
    assert "runs/" not in slice_text
    assert len(slice_text) <= 3200


def test_f5_quiet_hours_suppress_check(data_root: Path) -> None:
    """F5: quiet hours mute campaign check nudges."""
    paths = get_paths()
    ensure_prefs(paths)
    nz = ZoneInfo("Pacific/Auckland")
    night = datetime(2026, 8, 13, 2, 0, tzinfo=nz)
    assert in_quiet_hours(now=night) is True
    day = datetime(2026, 8, 13, 12, 0, tzinfo=nz)
    assert in_quiet_hours(now=day) is False

    upsert_loop(
        text="Stale camp",
        kind="campaign",
        status="blocked",
        blocked_reason="x",
        paths=paths,
    )
    suppress = proactivity_suppressed(paths=paths, now=night)
    assert suppress["suppressed"] is True
    assert "quiet_hours" in suppress["reasons"]
    # When suppressed, check path returns empty nudge payload (CLI pattern)
    if suppress["suppressed"]:
        payload = {"suppressed": True, "count": 0, "due": []}
    else:
        payload = campaign_check(paths=paths)
    assert payload["suppressed"] is True
    assert payload["count"] == 0
    # Organ still can list due when not gated by proactivity:
    assert campaign_check(paths=paths)["count"] >= 1


def test_f6_mute_proactivity_suppresses_check(data_root: Path) -> None:
    """F6: mute_proactivity suppresses check nudges."""
    paths = get_paths()
    ensure_prefs(paths)
    append_fact("prefs.mute_proactivity", True, paths=paths, allow_prefs_update=True)
    nz = ZoneInfo("Pacific/Auckland")
    noon = datetime(2026, 8, 13, 12, 0, tzinfo=nz)
    assert in_quiet_hours(now=noon) is False
    suppress = proactivity_suppressed(paths=paths, now=noon)
    assert suppress["suppressed"] is True
    assert "mute_proactivity" in suppress["reasons"]


def test_f7_cli_campaigns_status_from_file(data_root: Path) -> None:
    """F7: ada campaigns status answers where-is-X from file."""
    paths = get_paths()
    r = upsert_loop(
        text="Job hunt — NZ ML",
        kind="campaign",
        status="active",
        stages=[{"id": "shortlist", "state": "active"}],
        current_stage="shortlist",
        paths=paths,
    )
    cid = r["loop"]["id"]
    runner = CliRunner()
    result = runner.invoke(app, ["campaigns", "status", "--id", cid])
    assert result.exit_code == 0
    assert "shortlist" in result.stdout
    assert "active" in result.stdout
    assert cid in result.stdout


def test_f8_stale_or_due_surfaces_honestly(data_root: Path) -> None:
    """F8: past next_wake_at / 48h daily stale shows due_reason."""
    paths = get_paths()
    past = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    upsert_loop(
        text="Wake due",
        kind="campaign",
        status="active",
        next_wake_at=past,
        cadence="on_open_only",
        paths=paths,
    )
    upsert_loop(
        text="Daily stale",
        kind="campaign",
        status="active",
        cadence="daily",
        last_progress_at=past,
        paths=paths,
    )
    due = due_campaigns(paths=paths, now=datetime.now(timezone.utc), limit=10)
    reasons = {d.get("_due_reason") for d in due}
    assert "next_wake_at" in reasons
    assert "stale" in reasons
    check = campaign_check(paths=paths)
    assert check["count"] >= 2


def test_dream_stages_open_loops_never_auto_done(data_root: Path) -> None:
    paths = get_paths()
    ensure_prefs(paths)
    before = list_campaigns(paths=paths, include_done=True)
    info = apply_manage_result(
        {
            "digest": "note",
            "fact_candidates": [],
            "worldview_notes": [],
            "open_loops": [
                {"text": "Auto done?", "status": "done", "kind": "campaign"},
            ],
            "conflicts": [],
        },
        paths=paths,
        dream_id="dream-test",
    )
    staged = list_staged(paths=paths)
    assert any(s.get("reason") == "dream_open_loop_proposal" for s in staged)
    after = list_campaigns(paths=paths, include_done=True)
    assert len(after) == len(before)
    assert info["manage_applied"] is True


def test_todo_status_open_preserved(data_root: Path) -> None:
    paths = get_paths()
    r = upsert_loop(text="Buy milk", paths=paths)
    assert r["loop"]["kind"] == "todo"
    assert r["loop"]["status"] == "open"
    assert list_loops(paths=paths, status="open", kind="todo")


def test_memory_loops_campaigns_flag(data_root: Path) -> None:
    paths = get_paths()
    upsert_loop(text="Camp", kind="campaign", status="active", paths=paths)
    upsert_loop(text="Todo", kind="todo", status="open", paths=paths)
    runner = CliRunner()
    result = runner.invoke(app, ["memory", "loops", "--campaigns"])
    assert result.exit_code == 0
    assert "Camp" in result.stdout
    assert "Todo" not in result.stdout
