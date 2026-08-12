"""Dream seal / manage fail-open / whitelist merge / push stub (M04 §10.3)."""

from __future__ import annotations

import json
from pathlib import Path

from ada.body.identity import create_identity
from ada.body.lifecycle import read_events
from ada.dream.delta import build_delta
from ada.dream.merge import apply_manage_result
from ada.dream.push import push_outbox
from ada.dream.run import dream_run, dream_status
from ada.io.paths import get_paths
from ada.memory.facts import ensure_prefs, get_fact, load_prefs
from ada.memory.staging import list_staged


def test_dream_run_seals_with_skip_manage(data_root: Path) -> None:
    paths = get_paths()
    create_identity(paths=paths)
    ensure_prefs(paths)
    result = dream_run(paths=paths, skip_manage=True)
    assert result["ok"] is True
    assert result["status"] == "dream_ok"
    assert result["push"]["push"] == "skipped"
    outbox = Path(result["seal"]["outbox_path"])
    assert outbox.is_dir()
    assert (outbox / "MANIFEST.json").is_file()
    manifest = json.loads((outbox / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["package_sha256"]
    assert manifest["dream_id"] == result["dream_id"]
    types = [ev.type for ev in read_events(paths)]
    assert "dream_ok" in types
    status = dream_status(paths=paths)
    assert status["outbox_count"] >= 1
    assert status["push"] == "skipped"


def test_manage_fail_still_seals(data_root: Path) -> None:
    paths = get_paths()
    create_identity(paths=paths)
    ensure_prefs(paths)

    class BoomClient:
        class models:
            @staticmethod
            def generate_content(**_kwargs):
                raise RuntimeError("forced manage fail")

    result = dream_run(paths=paths, manage_client=BoomClient(), api_key="fake")
    assert result["ok"] is True
    assert result["status"] == "dream_ok"
    assert result["manage"]["skipped"] is True
    assert "manage_fail" in (result["manage"].get("reason") or "")
    assert Path(result["seal"]["outbox_path"]).is_dir()


def test_whitelist_merge_and_stage_non_whitelist(data_root: Path) -> None:
    paths = get_paths()
    create_identity(paths=paths)
    ensure_prefs(paths)
    manage_result = {
        "digest": "Nightly note: briefs stay early.",
        "fact_candidates": [
            {"key": "brief_time", "value": "05:30"},
            {"key": "people.friend", "value": "should stage"},
            {"key": "born_at", "value": "NOPE"},
            {"key": "favorite_color", "value": "blue"},
        ],
        "worldview_notes": ["USB bit continues."],
        "open_loops": [],
        "conflicts": [],
    }
    info = apply_manage_result(manage_result, paths=paths, dream_id="test-dream")
    assert any(m.get("key") == "prefs.brief_time" for m in info["merged"])
    assert get_fact("prefs.brief_time", paths=paths)["value"] == "05:30"
    staged = list_staged(paths=paths)
    reasons = {s.get("reason") for s in staged}
    assert "people_always_stage" in reasons or any(
        "people" in str(s.get("candidate")) for s in staged
    )
    assert "sacred_identity_denied" in reasons or "non_whitelist" in reasons
    # born_at untouched
    ident = paths.identity_yaml.read_text(encoding="utf-8")
    assert "NOPE" not in ident
    assert info["digest_path"]
    assert Path(info["digest_path"]).is_file()


def test_delta_is_capped_not_full_history(data_root: Path) -> None:
    paths = get_paths()
    create_identity(paths=paths)
    ensure_prefs(paths)
    # Create many fake run files
    runs = paths.runs / "2099-01-01"
    runs.mkdir(parents=True)
    for i in range(30):
        (runs / f"sess-{i}.jsonl").write_text('{"type":"user"}\n', encoding="utf-8")
    delta = build_delta(paths=paths)
    assert len(delta["run_files"]) <= 20
    assert "summary_text" in delta
    assert "BEGINNING" in delta["summary_text"] or delta["since"] is None


def test_push_stub_always_skipped() -> None:
    result = push_outbox(dream_id="x", outbox_path="/tmp/nope")
    assert result["push"] == "skipped"


def test_conflict_pref_stages(data_root: Path) -> None:
    paths = get_paths()
    ensure_prefs(paths)
    # Force existing different value
    from ada.memory.facts import propose_edit

    propose_edit("prefs.tease_ok", True, paths=paths, confirmed=True)
    info = apply_manage_result(
        {
            "digest": "",
            "fact_candidates": [{"key": "tease_ok", "value": False}],
            "worldview_notes": [],
            "open_loops": [],
            "conflicts": [],
        },
        paths=paths,
        dream_id="c1",
    )
    assert load_prefs(paths)["tease_ok"] is True
    assert info["staged"]
    assert any("tease_ok" in c for c in info["conflicts"]) or info["staged"]
