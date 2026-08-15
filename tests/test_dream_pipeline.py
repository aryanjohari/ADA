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


def test_extract_json_tolerates_preamble_and_fence() -> None:
    from ada.dream.manage import _extract_json

    raw = _extract_json('{"digest":"ok","fact_candidates":[],"worldview_notes":[]}')
    assert raw["digest"] == "ok"
    fenced = _extract_json('Here:\n```json\n{"digest":"n","fact_candidates":[]}\n```\n')
    assert fenced["digest"] == "n"
    nested = _extract_json('note {"digest":"x","open_loops":[{"text":"a{b}"}]} tail')
    assert nested["digest"] == "x"
    assert nested["open_loops"][0]["text"] == "a{b}"
    trailing = _extract_json('{"digest":"t","fact_candidates":[],}')
    assert trailing["digest"] == "t"


def test_extract_json_empty_and_invalid() -> None:
    import pytest

    from ada.dream.manage import _extract_json

    with pytest.raises(ValueError, match="empty"):
        _extract_json("")
    with pytest.raises(ValueError, match="no JSON object"):
        _extract_json("sorry, no object here")
    with pytest.raises(ValueError, match="invalid JSON"):
        _extract_json('{"digest": "broken "quote", "fact_candidates": []}')


def test_normalize_campaign_digests_object_and_list() -> None:
    from ada.dream.manage import _normalize_manage_result

    as_list = _normalize_manage_result(
        {
            "digest": "d",
            "campaign_digests": [
                {"campaign_id": "a", "digest": "note a", "cites": ["c_1"]}
            ],
        }
    )
    assert as_list["campaign_digests"][0]["campaign_id"] == "a"

    as_obj = _normalize_manage_result(
        {
            "digest": "d",
            "campaign_digests": {
                "bf6e4dadcd50": {"digest": "papers", "cites": ["c_9"]},
                "543a7a6c0d35": "short string digest",
            },
        }
    )
    by_id = {e["campaign_id"]: e for e in as_obj["campaign_digests"]}
    assert by_id["bf6e4dadcd50"]["digest"] == "papers"
    assert by_id["bf6e4dadcd50"]["cites"] == ["c_9"]
    assert by_id["543a7a6c0d35"]["digest"] == "short string digest"


def test_manage_delta_mocked_success() -> None:
    from ada.dream.manage import manage_delta

    payload = {
        "digest": "Thin prefs night.",
        "fact_candidates": [{"key": "brief_time", "value": "05:30"}],
        "worldview_notes": ["USB bit continues."],
        "campaign_digests": [
            {
                "campaign_id": "bf6e4dadcd50",
                "digest": "Abstract noted cite:c_abc",
                "cites": ["c_abc"],
            }
        ],
        "open_loops": [],
        "conflicts": [],
    }

    class OkClient:
        class models:
            @staticmethod
            def generate_content(**kwargs):
                config = kwargs.get("config")
                assert config is not None
                assert getattr(config, "response_mime_type", None) == "application/json"
                assert getattr(config, "response_schema", None) is not None
                thinking = getattr(config, "thinking_config", None)
                assert thinking is not None
                assert getattr(thinking, "thinking_budget", None) == 0

                class Resp:
                    text = json.dumps(payload)

                return Resp()

    out = manage_delta(
        {"summary_text": "DELTA: prefs touched; cite heads present."},
        api_key="fake",
        client=OkClient(),
    )
    assert out["ok"] is True
    assert out["skipped"] is False
    assert out["result"]["digest"] == "Thin prefs night."
    assert out["result"]["campaign_digests"][0]["campaign_id"] == "bf6e4dadcd50"


def test_manage_fail_includes_raw_snippet() -> None:
    from ada.dream.manage import manage_delta

    class EmptyClient:
        class models:
            @staticmethod
            def generate_content(**_kwargs):
                class Resp:
                    text = ""
                    candidates = []

                return Resp()

    out = manage_delta(
        {"summary_text": "DELTA: something"},
        api_key="fake",
        client=EmptyClient(),
    )
    assert out["ok"] is False
    assert "manage_fail" in (out.get("reason") or "")
    assert "empty manage response" in (out.get("reason") or "")


def test_delta_groups_cite_heads_by_campaign(data_root: Path) -> None:
    from ada.web import cites as cites_mod

    paths = get_paths()
    create_identity(paths=paths)
    ensure_prefs(paths)
    cites_mod.write_cite(
        url="https://example.com/a",
        final_url="https://example.com/a",
        status=200,
        etag=None,
        last_modified=None,
        content_hash="sha256:a1",
        title="A",
        excerpts=["alpha"],
        truncated=False,
        robots="honored",
        allowlist_host="example.com",
        receipt_id="r1",
        extract_ok=True,
        extract_status="ok",
        full_extract="alpha body",
        campaign_id="bf6e4dadcd50",
        watch_id="arxiv_cs_ai",
        paths=paths,
    )
    cites_mod.write_cite(
        url="https://example.com/b",
        final_url="https://example.com/b",
        status=200,
        etag=None,
        last_modified=None,
        content_hash="sha256:b1",
        title="B",
        excerpts=["beta"],
        truncated=False,
        robots="honored",
        allowlist_host="example.com",
        receipt_id="r2",
        extract_ok=True,
        extract_status="feed_item_fallback",
        full_extract="beta body",
        campaign_id="543a7a6c0d35",
        watch_id="beehive_rss",
        paths=paths,
    )
    delta = build_delta(paths=paths, since_ts=None)
    assert delta["cite_head_count"] >= 2
    groups = delta["cite_heads_by_campaign"]
    assert "bf6e4dadcd50" in groups
    assert "543a7a6c0d35" in groups
    assert "bf6e4dadcd50" in delta["summary_text"]
    assert len(delta["summary_text"]) <= 12_000


def test_merge_writes_per_campaign_worldview(data_root: Path) -> None:
    from ada.web import cites as cites_mod

    paths = get_paths()
    create_identity(paths=paths)
    ensure_prefs(paths)
    cite = cites_mod.write_cite(
        url="https://example.com/paper",
        final_url="https://example.com/paper",
        status=200,
        etag=None,
        last_modified=None,
        content_hash="sha256:p1",
        title="Paper",
        excerpts=["Abstract text"],
        truncated=False,
        robots="honored",
        allowlist_host="example.com",
        receipt_id="r",
        extract_ok=True,
        extract_status="abs_html",
        full_extract="Abstract text for paper",
        campaign_id="bf6e4dadcd50",
        watch_id="arxiv_cs_ai",
        paths=paths,
    )
    info = apply_manage_result(
        {
            "digest": "Quiet prefs night.",
            "fact_candidates": [],
            "worldview_notes": [f"Saw abstract cite:{cite['id']}"],
            "campaign_digests": [
                {
                    "campaign_id": "bf6e4dadcd50",
                    "digest": f"Field paper abstract noted cite:{cite['id']}",
                    "cites": [cite["id"]],
                }
            ],
            "open_loops": [],
            "conflicts": [],
        },
        paths=paths,
        dream_id="dream-m11",
        delta={
            "cite_heads": [
                {
                    "id": cite["id"],
                    "campaign_id": "bf6e4dadcd50",
                    "watch_id": "arxiv_cs_ai",
                    "extract_ok": True,
                    "extract_status": "abs_html",
                }
            ],
            "cite_heads_by_campaign": {
                "bf6e4dadcd50": [
                    {
                        "id": cite["id"],
                        "campaign_id": "bf6e4dadcd50",
                        "extract_ok": True,
                        "extract_status": "abs_html",
                    }
                ]
            },
        },
    )
    assert info["digest_path"]
    global_text = Path(info["digest_path"]).read_text(encoding="utf-8")
    assert f"cite:{cite['id']}" in global_text
    assert info["campaign_digest_paths"]
    camp_path = Path(info["campaign_digest_paths"][0])
    assert "campaigns/bf6e4dadcd50" in str(camp_path)
    camp_text = camp_path.read_text(encoding="utf-8")
    assert f"cite:{cite['id']}" in camp_text
    assert "campaign_id: bf6e4dadcd50" in camp_text
    # Shell honesty: feed_blob should not be attached as cite.
    shell_info = apply_manage_result(
        {
            "digest": "shell night",
            "fact_candidates": [],
            "worldview_notes": [],
            "open_loops": [],
            "conflicts": [],
        },
        paths=paths,
        dream_id="dream-shell",
        delta={
            "cite_heads": [
                {
                    "id": "c_shellfake",
                    "extract_ok": False,
                    "extract_status": "feed_blob",
                }
            ],
            "cite_heads_by_campaign": {},
        },
    )
    # May fail worldview if fake cite id — expect no crash; shell ref not required
    assert shell_info["manage_applied"] is True


def test_merge_writes_js_shell_only_campaign_worldview(data_root: Path) -> None:
    """Regression: stamped js_shell heads still get per-campaign WORLDVIEW.

    Metal smoke 2026-08-15: nz-civic (543a…) was in cite_heads_by_campaign but
    merge skipped when manage omitted campaign_digests and cite_refs were empty
    (extract_ok false / js_shell). field-papers survived via extract_ok cites.
    """
    paths = get_paths()
    create_identity(paths=paths)
    ensure_prefs(paths)
    civic = "543a7a6c0d35"
    info = apply_manage_result(
        {
            "digest": (
                "Two Beehive pages not readable. Two arXiv abstracts processed."
            ),
            "fact_candidates": [],
            "worldview_notes": [
                "Beehive pages not readable (cite:c_fd102be9189f41f39a0be42b1df25e2c)."
            ],
            # Manage mentioned Beehive only globally — no campaign_digests entry.
            "campaign_digests": [],
            "open_loops": [],
            "conflicts": [],
        },
        paths=paths,
        dream_id="dream-shell-camp",
        delta={
            "cite_heads": [
                {
                    "id": "c_fd102be9189f41f39a0be42b1df25e2c",
                    "campaign_id": civic,
                    "watch_id": "beehive_rss",
                    "extract_ok": False,
                    "extract_status": "js_shell",
                },
                {
                    "id": "c_ff41db70edfe4aa98f0f1ddfeeda1761",
                    "campaign_id": civic,
                    "watch_id": "beehive_rss",
                    "extract_ok": False,
                    "extract_status": "js_shell",
                },
            ],
            "cite_heads_by_campaign": {
                civic: [
                    {
                        "id": "c_fd102be9189f41f39a0be42b1df25e2c",
                        "campaign_id": civic,
                        "extract_ok": False,
                        "extract_status": "js_shell",
                    },
                    {
                        "id": "c_ff41db70edfe4aa98f0f1ddfeeda1761",
                        "campaign_id": civic,
                        "extract_ok": False,
                        "extract_status": "js_shell",
                    },
                ],
            },
        },
    )
    assert info["manage_applied"] is True
    assert info["campaign_digest_paths"], "js_shell-only campaign must get WORLDVIEW"
    camp_path = Path(info["campaign_digest_paths"][0])
    assert f"campaigns/{civic}" in str(camp_path)
    civic_text = camp_path.read_text(encoding="utf-8")
    assert f"campaign_id: {civic}" in civic_text
    assert "js_shell" in civic_text
    assert "not readable" in civic_text.lower()
    # Frontmatter cites must not attach shell cite:c_… (honesty).
    header = civic_text.split("\n\n", 1)[0]
    assert "cite:c_fd102be9189f41f39a0be42b1df25e2c" not in header
    assert "cite:c_ff41db70edfe4aa98f0f1ddfeeda1761" not in header
    # Ungrouped heads still must not invent a campaign folder.
    ungrouped = apply_manage_result(
        {
            "digest": "ungrouped shell",
            "fact_candidates": [],
            "worldview_notes": [],
            "campaign_digests": [],
            "open_loops": [],
            "conflicts": [],
        },
        paths=paths,
        dream_id="dream-ungrouped",
        delta={
            "cite_heads": [
                {
                    "id": "c_nogroup",
                    "campaign_id": None,
                    "extract_ok": False,
                    "extract_status": "js_shell",
                }
            ],
            "cite_heads_by_campaign": {
                "ungrouped": [
                    {
                        "id": "c_nogroup",
                        "extract_ok": False,
                        "extract_status": "js_shell",
                    }
                ]
            },
        },
    )
    assert all(
        "/campaigns/ungrouped/" not in p for p in ungrouped["campaign_digest_paths"]
    )


def test_staging_confirm_open_loop_cli(data_root: Path) -> None:
    from typer.testing import CliRunner

    from ada.cli.main import app
    from ada.memory.open_loops import list_loops
    from ada.memory.staging import list_staged, stage_candidate

    paths = get_paths()
    ensure_prefs(paths)
    staged = stage_candidate(
        {"text": "Buy more USB bits", "status": "open", "kind": "todo"},
        reason="dream_open_loop_proposal",
        paths=paths,
    )
    before = len(list_loops(paths=paths, kind="todo", status="open"))
    runner = CliRunner()
    result = runner.invoke(app, ["staging", "confirm", staged["id"]])
    assert result.exit_code == 0, result.stdout + result.stderr
    after = list_loops(paths=paths, kind="todo", status="open")
    assert len(after) == before + 1
    assert any(s.get("status") == "confirmed" for s in list_staged(paths=paths))
    rej = stage_candidate(
        {"text": "Nope", "kind": "todo"},
        reason="dream_open_loop_proposal",
        paths=paths,
    )
    r2 = runner.invoke(app, ["staging", "reject", rej["id"], "--reason", "noise"])
    assert r2.exit_code == 0


def test_update_cite_stamps_campaign_id(data_root: Path) -> None:
    from ada.web import cites as cites_mod

    paths = get_paths()
    cite = cites_mod.write_cite(
        url="https://example.com/stamp",
        final_url="https://example.com/stamp",
        status=200,
        etag=None,
        last_modified=None,
        content_hash="sha256:stamp",
        title="Stamp me",
        excerpts=["x"],
        truncated=False,
        robots="honored",
        allowlist_host="example.com",
        receipt_id="r",
        extract_ok=True,
        extract_status="ok",
        full_extract="x",
        paths=paths,
    )
    assert cite.get("campaign_id") is None
    updated = cites_mod.update_cite_fetched_at(
        cite["id"],
        campaign_id="543a7a6c0d35",
        watch_id="beehive_rss",
        paths=paths,
    )
    assert updated["cite"]["campaign_id"] == "543a7a6c0d35"
    assert updated["cite"]["watch_id"] == "beehive_rss"
    got = cites_mod.get_cite(cite["id"], paths=paths)
    assert got["cite"]["campaign_id"] == "543a7a6c0d35"
